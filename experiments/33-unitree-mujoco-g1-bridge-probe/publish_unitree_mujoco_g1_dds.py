#!/usr/bin/env python3
"""Run Unitree G1 MJCF headlessly and publish SDK2-style DDS state."""

from __future__ import annotations

import argparse
import json
import math
import sys
import threading
import time
from pathlib import Path
from typing import Any

import mujoco
import numpy as np
import onnxruntime as ort
import yaml


EXPECTED_NQ = 36
EXPECTED_NU = 29


class LowCmdState:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.msg: Any | None = None
        self.count = 0

    def update(self, msg: Any) -> None:
        with self.lock:
            self.msg = msg
            self.count += 1

    def snapshot(self) -> tuple[Any | None, int]:
        with self.lock:
            return self.msg, self.count


class HistoryTerm:
    def __init__(self, width: int, history_length: int, scale: list[float] | None = None) -> None:
        self.width = width
        self.history_length = history_length
        self.scale = np.asarray(scale if scale is not None else [1.0] * width, dtype=np.float32)
        if self.scale.shape != (width,):
            raise ValueError(f"scale width mismatch: expected {width}, got {self.scale.shape}")
        self.frames: list[np.ndarray] = []

    def reset(self, values: np.ndarray) -> None:
        scaled = self._scaled(values)
        self.frames = [scaled.copy() for _ in range(self.history_length)]

    def add(self, values: np.ndarray) -> None:
        self.frames.append(self._scaled(values))
        if len(self.frames) > self.history_length:
            self.frames.pop(0)

    def get(self) -> np.ndarray:
        return np.concatenate(self.frames).astype(np.float32)

    def _scaled(self, values: np.ndarray) -> np.ndarray:
        values = np.asarray(values, dtype=np.float32)
        if values.shape != (self.width,):
            raise ValueError(f"term width mismatch: expected {self.width}, got {values.shape}")
        return values * self.scale


class UnitreeRLLabPolicy:
    """Minimal Python port of Unitree RL Lab's G1-29DOF deploy observation/action path."""

    def __init__(self, policy_dir: Path, command: list[float]) -> None:
        deploy_path = policy_dir / "params" / "deploy.yaml"
        onnx_path = policy_dir / "exported" / "policy.onnx"
        cfg = yaml.safe_load(deploy_path.read_text(encoding="utf-8"))
        self.cfg = cfg
        self.session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
        self.step_dt = float(cfg["step_dt"])
        self.joint_ids_map = [int(x) for x in cfg["joint_ids_map"]]
        self.default_joint_pos = np.asarray(cfg["default_joint_pos"], dtype=np.float32)
        self.action_scale = np.asarray(cfg["actions"]["JointPositionAction"]["scale"], dtype=np.float32)
        self.action_offset = np.asarray(cfg["actions"]["JointPositionAction"]["offset"], dtype=np.float32)
        self.command = np.asarray(command, dtype=np.float32)
        if self.default_joint_pos.shape != (len(self.joint_ids_map),):
            raise ValueError("default_joint_pos must match joint_ids_map length")
        if self.action_scale.shape != self.default_joint_pos.shape:
            raise ValueError("action scale must match action width")
        if self.action_offset.shape != self.default_joint_pos.shape:
            raise ValueError("action offset must match action width")
        if self.command.shape != (3,):
            raise ValueError("--rl-command must contain exactly three floats")

        observations = cfg["observations"]
        self.terms = {
            "base_ang_vel": HistoryTerm(3, int(observations["base_ang_vel"]["history_length"]), observations["base_ang_vel"]["scale"]),
            "projected_gravity": HistoryTerm(
                3, int(observations["projected_gravity"]["history_length"]), observations["projected_gravity"]["scale"]
            ),
            "velocity_commands": HistoryTerm(
                3, int(observations["velocity_commands"]["history_length"]), observations["velocity_commands"]["scale"]
            ),
            "joint_pos_rel": HistoryTerm(
                len(self.joint_ids_map),
                int(observations["joint_pos_rel"]["history_length"]),
                observations["joint_pos_rel"]["scale"],
            ),
            "joint_vel_rel": HistoryTerm(
                len(self.joint_ids_map),
                int(observations["joint_vel_rel"]["history_length"]),
                observations["joint_vel_rel"]["scale"],
            ),
            "last_action": HistoryTerm(
                len(self.joint_ids_map),
                int(observations["last_action"]["history_length"]),
                observations["last_action"]["scale"],
            ),
        }
        self.last_action = np.zeros(len(self.joint_ids_map), dtype=np.float32)
        self.action_count = 0

    def reset(self, data: mujoco.MjData) -> None:
        values = self._values(data)
        for name, term in self.terms.items():
            term.reset(values[name])

    def target_by_motor_index(self, data: mujoco.MjData) -> list[float]:
        values = self._values(data)
        for name, term in self.terms.items():
            term.add(values[name])
        obs = np.concatenate([self.terms[name].get() for name in self.terms]).astype(np.float32)
        if obs.shape != (480,):
            raise ValueError(f"expected obs[480], got {obs.shape}")
        action = self.session.run(None, {"obs": obs.reshape(1, -1)})[0][0].astype(np.float32)
        self.last_action = action
        processed = action * self.action_scale + self.action_offset
        targets = [0.0] * len(self.joint_ids_map)
        for policy_idx, motor_idx in enumerate(self.joint_ids_map):
            targets[motor_idx] = float(processed[policy_idx])
        self.action_count += 1
        return targets

    def _values(self, data: mujoco.MjData) -> dict[str, np.ndarray]:
        joint_pos = np.asarray([float(data.qpos[7 + motor_idx]) for motor_idx in self.joint_ids_map], dtype=np.float32)
        joint_vel = np.asarray([float(data.qvel[6 + motor_idx]) for motor_idx in self.joint_ids_map], dtype=np.float32)
        return {
            "base_ang_vel": np.asarray([float(data.qvel[3]), float(data.qvel[4]), float(data.qvel[5])], dtype=np.float32),
            "projected_gravity": projected_gravity_body(data.qpos[3:7]),
            "velocity_commands": self.command,
            "joint_pos_rel": joint_pos - self.default_joint_pos,
            "joint_vel_rel": joint_vel,
            "last_action": self.last_action,
        }


def projected_gravity_body(qwxyz: Any) -> np.ndarray:
    w, x, y, z = [float(v) for v in qwxyz]
    # Rotation matrix first column convention is irrelevant here; this is q.conjugate() * [0, 0, -1].
    r20 = 2.0 * (x * z - w * y)
    r21 = 2.0 * (y * z + w * x)
    r22 = 1.0 - 2.0 * (x * x + y * y)
    return np.asarray([-r20, -r21, -r22], dtype=np.float32)


def apply_elastic_band(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    body_id: int,
    length: float,
    stiffness: float,
    damping: float,
) -> None:
    point = [0.0, 0.0, 3.0]
    delta = [point[i] - float(data.qpos[i]) for i in range(3)]
    distance = math.sqrt(sum(v * v for v in delta))
    if distance <= 1e-9:
        return
    direction = [v / distance for v in delta]
    velocity = sum(float(data.qvel[i]) * direction[i] for i in range(3))
    force_mag = stiffness * (distance - length) - damping * velocity
    for i in range(3):
        data.xfrc_applied[body_id, i] = force_mag * direction[i]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--unitree-root", required=True, type=Path)
    parser.add_argument("--sdk-path", type=Path)
    parser.add_argument("--frames", type=int, default=100)
    parser.add_argument("--fps", type=float, default=50.0)
    parser.add_argument("--domain-id", type=int, default=1)
    parser.add_argument("--interface", default=None)
    parser.add_argument("--topic", default="rt/lowstate")
    parser.add_argument("--sportmode-topic", default="rt/sportmodestate")
    parser.add_argument("--lowcmd-topic", default="rt/lowcmd")
    parser.add_argument("--control-source", choices=["internal-pd", "dds-lowcmd", "rl-lab-policy"], default="internal-pd")
    parser.add_argument("--rl-lab-policy-dir", type=Path)
    parser.add_argument("--rl-command", nargs=3, type=float, default=[0.0, 0.0, 0.0])
    parser.add_argument("--kp", type=float, default=80.0)
    parser.add_argument("--kd", type=float, default=3.0)
    parser.add_argument("--elastic-band", action="store_true")
    parser.add_argument("--band-length", type=float, default=0.5)
    parser.add_argument("--band-stiffness", type=float, default=200.0)
    parser.add_argument("--band-damping", type=float, default=100.0)
    parser.add_argument("--warmup-s", type=float, default=0.5)
    args = parser.parse_args()

    if args.sdk_path:
        sys.path.insert(0, str(args.sdk_path))

    from unitree_sdk2py.core.channel import ChannelFactoryInitialize, ChannelPublisher, ChannelSubscriber
    from unitree_sdk2py.idl.default import unitree_go_msg_dds__SportModeState_
    from unitree_sdk2py.idl.default import unitree_hg_msg_dds__LowState_
    from unitree_sdk2py.idl.unitree_go.msg.dds_ import SportModeState_
    from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowCmd_
    from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowState_

    xml_path = args.unitree_root / "unitree_robots" / "g1" / "scene.xml"
    model = mujoco.MjModel.from_xml_path(str(xml_path))
    data = mujoco.MjData(model)
    if model.nq != EXPECTED_NQ or model.nu != EXPECTED_NU:
        raise ValueError(f"expected nq={EXPECTED_NQ}, nu={EXPECTED_NU}; got nq={model.nq}, nu={model.nu}")

    mujoco.mj_resetData(model, data)
    data.qpos[:] = model.qpos0
    data.qvel[:] = 0.0
    mujoco.mj_forward(model, data)
    desired = [float(v) for v in data.qpos[7 : 7 + model.nu]]
    rl_policy = None
    if args.control_source == "rl-lab-policy":
        if args.rl_lab_policy_dir is None:
            raise ValueError("--rl-lab-policy-dir is required when --control-source=rl-lab-policy")
        rl_policy = UnitreeRLLabPolicy(args.rl_lab_policy_dir, args.rl_command)
        rl_policy.reset(data)

    band_body_id = -1
    if args.elastic_band:
        band_body_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "torso_link")
        if band_body_id < 0:
            raise ValueError("elastic band requested but body 'torso_link' was not found")

    ChannelFactoryInitialize(args.domain_id, args.interface)
    lowstate_publisher = ChannelPublisher(args.topic, LowState_)
    lowstate_publisher.Init()
    sportmode_publisher = ChannelPublisher(args.sportmode_topic, SportModeState_)
    sportmode_publisher.Init()
    lowcmd_state = LowCmdState()
    if args.control_source == "dds-lowcmd":
        lowcmd_subscriber = ChannelSubscriber(args.lowcmd_topic, LowCmd_)
        lowcmd_subscriber.Init(lowcmd_state.update, 10)
    time.sleep(args.warmup_s)

    dt = float(model.opt.timestep)
    substeps = max(1, round((1.0 / args.fps) / dt))
    heights: list[float] = []
    start = time.perf_counter()
    for tick in range(args.frames):
        low_state = unitree_hg_msg_dds__LowState_()
        sport_state = unitree_go_msg_dds__SportModeState_()
        low_state.tick = tick
        for i in range(4):
            low_state.imu_state.quaternion[i] = float(data.qpos[3 + i])
        for i in range(3):
            sport_state.position[i] = float(data.qpos[i])
        for i in range(model.nu):
            low_state.motor_state[i].q = float(data.qpos[7 + i])
            low_state.motor_state[i].dq = float(data.qvel[6 + i])
            low_state.motor_state[i].tau_est = float(data.ctrl[i])
        lowstate_publisher.Write(low_state)
        sportmode_publisher.Write(sport_state)
        heights.append(float(data.qpos[2]))

        rl_targets = rl_policy.target_by_motor_index(data) if rl_policy is not None else None
        for _ in range(substeps):
            data.xfrc_applied[:] = 0.0
            if args.elastic_band:
                apply_elastic_band(
                    model,
                    data,
                    band_body_id,
                    args.band_length,
                    args.band_stiffness,
                    args.band_damping,
                )
            lowcmd_msg, _ = lowcmd_state.snapshot()
            for i in range(model.nu):
                if args.control_source == "dds-lowcmd" and lowcmd_msg is not None:
                    motor_cmd = lowcmd_msg.motor_cmd[i]
                    q_target = float(motor_cmd.q)
                    dq_target = float(motor_cmd.dq)
                    kp = float(motor_cmd.kp)
                    kd = float(motor_cmd.kd)
                    tau = float(motor_cmd.tau)
                    q_err = q_target - float(data.qpos[7 + i])
                    dq_err = dq_target - float(data.qvel[6 + i])
                    data.ctrl[i] = tau + kp * q_err + kd * dq_err
                elif rl_targets is not None:
                    q_err = rl_targets[i] - float(data.qpos[7 + i])
                    dq = float(data.qvel[6 + i])
                    data.ctrl[i] = args.kp * q_err - args.kd * dq
                else:
                    q_err = desired[i] - float(data.qpos[7 + i])
                    dq = float(data.qvel[6 + i])
                    data.ctrl[i] = args.kp * q_err - args.kd * dq
            mujoco.mj_step(model, data)

        target = start + (tick + 1) * (1.0 / args.fps)
        sleep_s = target - time.perf_counter()
        if sleep_s > 0:
            time.sleep(sleep_s)

    summary = {
        "verdict": "PASS",
        "contract": "physical-ai-unitree-mujoco-g1-dds-publisher-v0",
        "source_xml": str(xml_path),
        "frames": args.frames,
        "fps_target": args.fps,
        "model_timestep_s": dt,
        "substeps_per_frame": substeps,
        "nq": int(model.nq),
        "nu": int(model.nu),
        "elastic_band": args.elastic_band,
        "control_source": args.control_source,
        "rl_lab_policy_dir": str(args.rl_lab_policy_dir) if args.rl_lab_policy_dir else None,
        "rl_command": args.rl_command,
        "rl_policy_action_count": rl_policy.action_count if rl_policy is not None else 0,
        "lowcmd_topic": args.lowcmd_topic,
        "lowcmd_received_count": lowcmd_state.snapshot()[1],
        "start_height_m": heights[0] if heights else None,
        "min_height_m": min(heights) if heights else None,
        "max_height_m": max(heights) if heights else None,
        "end_height_m": heights[-1] if heights else None,
        "root_height_drop_m": (heights[0] - min(heights)) if heights else None,
        "lowstate_topic": args.topic,
        "sportmode_topic": args.sportmode_topic,
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
