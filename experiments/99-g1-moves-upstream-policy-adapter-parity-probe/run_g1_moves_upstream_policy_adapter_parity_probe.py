#!/usr/bin/env python3
"""Probe G1 Moves upstream run_policy.py adapter choices in local MuJoCo.

exp98 used the public README layout but still produced OOD actions. The
upstream standalone runner reveals several concrete choices: pelvis anchor,
column-major 6D orientation flattening, zero default pose, and PD torque
targets. This experiment sweeps those choices against the local G1 model.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import tempfile
import urllib.request
from pathlib import Path
from typing import Any

import mujoco
import numpy as np
import onnxruntime as ort


EXP_DIR = Path(__file__).resolve().parent
ROOT = EXP_DIR.parents[1]
VERIFY = EXP_DIR / "verify" / "g1-moves-upstream-policy-adapter-parity-probe"
EXP98_PATH = ROOT / "experiments/98-g1-moves-standalone-onnx-native-adapter-probe/run_g1_moves_standalone_onnx_native_adapter_probe.py"
BASE = "https://huggingface.co/datasets/exptech/g1-moves/resolve/main/dance/J_Dance4_Broadway"
ONNX_URL = f"{BASE}/policy/J_Dance4_Broadway_policy.onnx"
NPZ_URL = f"{BASE}/training/J_Dance4_Broadway.npz"
RUN_POLICY_URL = "https://raw.githubusercontent.com/experientialtech/g1-moves/main/run_policy.py"
ACCESS_DATE = "2026-06-18"


KP = np.array(
    [
        40.2, 99.1, 40.2, 99.1, 28.6, 28.6,
        40.2, 99.1, 40.2, 99.1, 28.6, 28.6,
        40.2, 28.6, 28.6,
        14.3, 14.3, 14.3, 14.3, 14.3, 16.8, 16.8,
        14.3, 14.3, 14.3, 14.3, 14.3, 16.8, 16.8,
    ],
    dtype=np.float32,
)
KD = np.array(
    [
        2.6, 6.3, 2.6, 6.3, 1.8, 1.8,
        2.6, 6.3, 2.6, 6.3, 1.8, 1.8,
        2.6, 1.8, 1.8,
        0.9, 0.9, 0.9, 0.9, 0.9, 1.1, 1.1,
        0.9, 0.9, 0.9, 0.9, 0.9, 1.1, 1.1,
    ],
    dtype=np.float32,
)


def load_exp98():
    spec = importlib.util.spec_from_file_location("exp98_adapter", EXP98_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {EXP98_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EXP98 = load_exp98()
EXP28 = EXP98.EXP28
EXP37 = EXP98.EXP37
EXP67 = EXP98.EXP67


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "physical-ai-exp99/1.0"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def quat_to_rot_matrix(quat_wxyz: np.ndarray) -> np.ndarray:
    w, x, y, z = quat_wxyz
    return np.array(
        [
            [1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
            [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
            [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)],
        ],
        dtype=np.float64,
    )


def rotation_6d(rot_matrix: np.ndarray, order: str) -> np.ndarray:
    if order == "upstream":
        return rot_matrix[:, :2].T.flatten()
    if order == "row_major":
        return rot_matrix[:, :2].reshape(-1)
    raise ValueError(order)


def transform_anchor(
    robot_pos: np.ndarray,
    robot_quat_wxyz: np.ndarray,
    anchor_pos_world: np.ndarray,
    anchor_quat_world_wxyz: np.ndarray,
    ori_order: str,
) -> tuple[np.ndarray, np.ndarray]:
    r_robot = quat_to_rot_matrix(robot_quat_wxyz)
    anchor_pos_b = r_robot.T @ (anchor_pos_world - robot_pos)
    r_anchor = quat_to_rot_matrix(anchor_quat_world_wxyz)
    anchor_ori_b = rotation_6d(r_robot.T @ r_anchor, ori_order)
    return anchor_pos_b.astype(np.float32), anchor_ori_b.astype(np.float32)


def named_sensor(model: mujoco.MjModel, data: mujoco.MjData, name: str) -> np.ndarray:
    sensor = model.sensor(name)
    adr = int(sensor.adr[0])
    dim = int(sensor.dim[0])
    return np.asarray(data.sensordata[adr : adr + dim], dtype=np.float32)


def velocities(model: mujoco.MjModel, data: mujoco.MjData, source: str) -> tuple[np.ndarray, np.ndarray]:
    if source == "upstream_raw":
        ang = data.sensordata[:3].astype(np.float32) if data.sensordata.size >= 3 else np.zeros(3, dtype=np.float32)
        lin = data.sensordata[3:6].astype(np.float32) if data.sensordata.size >= 6 else np.zeros(3, dtype=np.float32)
        return ang, lin
    if source == "named":
        return named_sensor(model, data, "gyro_pelvis"), named_sensor(model, data, "local_linvel_pelvis")
    if source == "zero":
        return np.zeros(3, dtype=np.float32), np.zeros(3, dtype=np.float32)
    raise ValueError(source)


def make_obs(
    *,
    model: mujoco.MjModel,
    data: mujoco.MjData,
    motion: dict[str, np.ndarray],
    frame: int,
    last_action: np.ndarray,
    default_pose: np.ndarray,
    anchor_index: int,
    ori_order: str,
    vel_source: str,
) -> np.ndarray:
    ref_jp = motion["joint_pos"][frame].astype(np.float32)
    ref_jv = motion["joint_vel"][frame].astype(np.float32)
    anchor_pos_b, anchor_ori_b = transform_anchor(
        data.qpos[:3].copy(),
        data.qpos[3:7].copy(),
        motion["body_pos_w"][frame, anchor_index].astype(np.float64),
        motion["body_quat_w"][frame, anchor_index].astype(np.float64),
        ori_order,
    )
    base_ang_vel, base_lin_vel = velocities(model, data, vel_source)
    return np.concatenate(
        [
            ref_jp,
            ref_jv,
            anchor_pos_b,
            anchor_ori_b,
            base_ang_vel,
            base_lin_vel,
            data.qpos[7:36].astype(np.float32) - default_pose.astype(np.float32),
            data.qvel[6:35].astype(np.float32),
            last_action.astype(np.float32),
        ]
    ).astype(np.float32)


def init_from_motion(model: mujoco.MjModel, data: mujoco.MjData, motion: dict[str, np.ndarray], mode: str) -> np.ndarray:
    if mode == "upstream_motion":
        data.qpos[:3] = motion["body_pos_w"][0, 0]
        data.qpos[3:7] = motion["body_quat_w"][0, 0]
        data.qpos[7:36] = motion["joint_pos"][0]
    elif mode == "keyframe":
        data.qpos[:] = model.keyframe("knees_bent").qpos
    else:
        raise ValueError(mode)
    mujoco.mj_forward(model, data)
    if mode == "upstream_motion":
        return np.zeros(29, dtype=np.float32)
    return model.keyframe("knees_bent").qpos[7:].astype(np.float32).copy()


def visible_gate(run: dict[str, Any]) -> bool:
    return (
        run["fell_at"] is None
        and run["visible_drop"] >= 0.08
        and run["max_knee_delta_rad"] >= 0.60
        and run["max_hip_pitch_delta_rad"] >= 0.35
        and run["return_to_stand"]
        and run["foot_contact_ratio"] >= 0.90
        and run["foot_slip_distance"] <= 0.08
        and run["max_joint_limit_violation"] <= 0.05
    )


def annotate(run: dict[str, Any]) -> dict[str, Any]:
    run["visible_8cm_gate"] = visible_gate(run)
    if run["visible_8cm_gate"]:
        run["visible_verdict"] = "PASS_VISIBLE_8CM_GATE"
    elif run["fell_at"] is not None:
        run["visible_verdict"] = "FAIL_FALL"
    elif run["visible_drop"] < 0.08:
        run["visible_verdict"] = "DEPTH_PENDING_8CM"
    elif run["max_knee_delta_rad"] < 0.60 or run["max_hip_pitch_delta_rad"] < 0.35:
        run["visible_verdict"] = "POSE_GATE_PENDING"
    elif not run["return_to_stand"]:
        run["visible_verdict"] = "RETURN_PENDING"
    elif run["foot_contact_ratio"] < 0.90:
        run["visible_verdict"] = "CONTACT_PENDING"
    elif run["foot_slip_distance"] > 0.08:
        run["visible_verdict"] = "STANCE_SLIP_PENDING"
    else:
        run["visible_verdict"] = "GATE_PENDING"
    return run


def run_variant(
    *,
    variant: dict[str, Any],
    model: mujoco.MjModel,
    sess: ort.InferenceSession,
    motion: dict[str, np.ndarray],
    out_dir: Path,
) -> dict[str, Any]:
    data = mujoco.MjData(model)
    model.opt.timestep = 0.02 / 4
    default_pose = init_from_motion(model, data, motion, variant["init_mode"])
    input_name = sess.get_inputs()[0].name
    last_action = np.zeros(29, dtype=np.float32)
    ctrl_dt = 0.02
    n_substeps = 4
    total_steps = int(variant["seconds"] / ctrl_dt)
    start_height = float(data.qpos[2])
    start_qpos = data.qpos.copy()
    foot_site_ids = np.asarray(EXP28.ContactAwareSquat(config_overrides={"impl": "jax"})._feet_site_id)
    foot_geom_ids = np.asarray([model.geom("left_foot").id, model.geom("right_foot").id])
    initial_foot_xy = data.site_xpos[foot_site_ids, :2].copy()
    foot_sensor_ids = [model.sensor(name).id for name in ["left_foot_floor_found", "right_foot_floor_found"]]
    pose_indices = {name: EXP98.EXP96.EXP62.qpos_index(model, name) for name in EXP67.POSE_JOINTS}

    min_height = start_height
    final_height = start_height
    fell_at = None
    contact_count = 0
    max_slip = 0.0
    max_knee = 0.0
    max_hip = 0.0
    max_joint_violation = 0.0
    min_support_margin = float("inf")
    action_min = float("inf")
    action_max = -float("inf")
    obs_abs_max = 0.0
    first_obs: list[float] | None = None
    first_action: list[float] | None = None
    qpos_frames: list[list[float]] = []
    samples: list[dict[str, Any]] = []

    for step in range(total_steps):
        fps = float(np.asarray(motion["fps"]).reshape(-1)[0])
        frame = int((step * ctrl_dt * fps) % motion["joint_pos"].shape[0])
        obs = make_obs(
            model=model,
            data=data,
            motion=motion,
            frame=frame,
            last_action=last_action,
            default_pose=default_pose,
            anchor_index=variant["anchor_index"],
            ori_order=variant["ori_order"],
            vel_source=variant["vel_source"],
        )
        action = sess.run(["actions"], {input_name: obs[None, :]})[0][0].astype(np.float32)
        if first_obs is None:
            first_obs = [float(v) for v in obs[:80]]
            first_action = [float(v) for v in action[:29]]
        obs_abs_max = max(obs_abs_max, float(np.max(np.abs(obs))))
        action_min = min(action_min, float(np.min(action)))
        action_max = max(action_max, float(np.max(action)))
        if variant["control_mode"] == "position":
            target = action + default_pose
            if variant["action_step"] < 1.0:
                target = data.qpos[7:36] + variant["action_step"] * (target - data.qpos[7:36])
            np.clip(target, model.actuator_ctrlrange[:, 0], model.actuator_ctrlrange[:, 1], out=target)
            data.ctrl[:29] = target
        elif variant["control_mode"] == "torque_pd":
            target = action + default_pose
            torques = KP * (target - data.qpos[7:36].astype(np.float32)) - KD * data.qvel[6:35].astype(np.float32)
            np.clip(torques, model.actuator_ctrlrange[:, 0], model.actuator_ctrlrange[:, 1], out=torques)
            data.ctrl[:29] = torques
        else:
            raise ValueError(variant["control_mode"])
        for _ in range(n_substeps):
            mujoco.mj_step(model, data)
        last_action = action

        height = float(data.qpos[2])
        final_height = height
        min_height = min(min_height, height)
        contacts = [float(data.sensordata[model.sensor_adr[sid]]) > 0.0 for sid in foot_sensor_ids]
        contact_count += int(all(contacts))
        support = EXP37.support_metrics(model, data, foot_geom_ids)
        min_support_margin = min(min_support_margin, support["support_margin"])
        foot_slip = float(np.max(np.linalg.norm(data.site_xpos[foot_site_ids, :2] - initial_foot_xy, axis=1)))
        max_slip = max(max_slip, foot_slip)
        max_joint_violation = max(max_joint_violation, EXP28.joint_limit_violation(model, data))
        max_knee = max(
            max_knee,
            abs(float(data.qpos[pose_indices["left_knee_joint"]] - start_qpos[pose_indices["left_knee_joint"]])),
            abs(float(data.qpos[pose_indices["right_knee_joint"]] - start_qpos[pose_indices["right_knee_joint"]])),
        )
        max_hip = max(
            max_hip,
            abs(float(data.qpos[pose_indices["left_hip_pitch_joint"]] - start_qpos[pose_indices["left_hip_pitch_joint"]])),
            abs(float(data.qpos[pose_indices["right_hip_pitch_joint"]] - start_qpos[pose_indices["right_hip_pitch_joint"]])),
        )
        mat = np.empty(9)
        mujoco.mju_quat2Mat(mat, data.qpos[3:7])
        up_z = float(mat.reshape(3, 3)[2, 2])
        if (height < 0.45 or up_z < 0.30) and fell_at is None:
            fell_at = round(step * ctrl_dt, 3)
        if step % 10 == 0:
            samples.append(
                {
                    "t": round(step * ctrl_dt, 3),
                    "frame": frame,
                    "height": height,
                    "visible_drop": start_height - height,
                    "both_feet_contact": all(contacts),
                    "foot_slip_distance": foot_slip,
                    "support_margin": support["support_margin"],
                    "knee_delta": max_knee,
                    "hip_delta": max_hip,
                    "up_z": up_z,
                    "action_min": float(np.min(action)),
                    "action_max": float(np.max(action)),
                }
            )
        if variant["record_trajectory"]:
            qpos_frames.append([float(v) for v in data.qpos[: model.nq]])

    run = annotate(
        {
            "attempt": variant["attempt"],
            "variant": {k: v for k, v in variant.items() if k != "record_trajectory"},
            "start_height": start_height,
            "min_height": min_height,
            "visible_drop": start_height - min_height,
            "fell_at": fell_at,
            "final_height": final_height,
            "return_to_stand": final_height >= 0.74,
            "foot_contact_ratio": contact_count / max(1, total_steps),
            "foot_slip_distance": max_slip,
            "min_support_margin": min_support_margin,
            "max_joint_limit_violation": max_joint_violation,
            "max_knee_delta_rad": max_knee,
            "max_hip_pitch_delta_rad": max_hip,
            "action_min": action_min,
            "action_max": action_max,
            "obs_abs_max": obs_abs_max,
            "first_obs80": first_obs,
            "first_action29": first_action,
            "samples": samples,
        }
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    if qpos_frames:
        trajectory = {
            "schema": "physical-ai-web-trajectory-v1",
            "source": "g1-moves-upstream-policy-adapter-parity-probe",
            "scene": "g1/scene_g1_policy.xml",
            "robot": "unitree_g1",
            "fps": 50,
            "nq": model.nq,
            "frames": len(qpos_frames),
            "duration_s": len(qpos_frames) / 50.0,
            "qpos": qpos_frames,
        }
        (out_dir / "native_rollout_web_trajectory.json").write_text(json.dumps(trajectory), encoding="utf-8")
        run["trajectory_out"] = str((out_dir / "native_rollout_web_trajectory.json").relative_to(ROOT))
    (out_dir / "native-eval.json").write_text(json.dumps(run, indent=2), encoding="utf-8")
    return run


def variants(seconds: float) -> list[dict[str, Any]]:
    common = {"seconds": seconds, "record_trajectory": True}
    return [
        {**common, "attempt": "upstream-exact-position", "init_mode": "upstream_motion", "anchor_index": 0, "ori_order": "upstream", "vel_source": "upstream_raw", "control_mode": "position", "action_step": 1.0},
        {**common, "attempt": "upstream-exact-position-smooth0p25", "init_mode": "upstream_motion", "anchor_index": 0, "ori_order": "upstream", "vel_source": "upstream_raw", "control_mode": "position", "action_step": 0.25},
        {**common, "attempt": "upstream-exact-torque-pd", "init_mode": "upstream_motion", "anchor_index": 0, "ori_order": "upstream", "vel_source": "upstream_raw", "control_mode": "torque_pd", "action_step": 1.0},
        {**common, "attempt": "named-vel-position", "init_mode": "upstream_motion", "anchor_index": 0, "ori_order": "upstream", "vel_source": "named", "control_mode": "position", "action_step": 1.0},
        {**common, "attempt": "rowmajor-ablation", "init_mode": "upstream_motion", "anchor_index": 0, "ori_order": "row_major", "vel_source": "upstream_raw", "control_mode": "position", "action_step": 1.0},
        {**common, "attempt": "torso-anchor-ablation", "init_mode": "upstream_motion", "anchor_index": 7, "ori_order": "upstream", "vel_source": "upstream_raw", "control_mode": "position", "action_step": 1.0},
        {**common, "attempt": "keyframe-default-position", "init_mode": "keyframe", "anchor_index": 0, "ori_order": "upstream", "vel_source": "upstream_raw", "control_mode": "position", "action_step": 0.25},
    ]


def write_summary(result: dict[str, Any], out_dir: Path) -> None:
    lines = [
        "# G1 Moves Upstream Policy Adapter Parity Probe Summary",
        "",
        "| Attempt | Gate | Verdict | Drop | Knee | Hip | Contact | Slip | Fell | Action range | Obs max |",
        "|---|---|---|---:|---:|---:|---:|---:|---|---|---:|",
    ]
    for run in result["runs"]:
        fell = "never" if run["fell_at"] is None else f"{run['fell_at']:.2f}s"
        gate = "PASS" if run["visible_8cm_gate"] else "FAIL"
        lines.append(
            f"| {run['attempt']} | {gate} | {run['visible_verdict']} | {run['visible_drop']:.3f}m | "
            f"{run['max_knee_delta_rad']:.3f} | {run['max_hip_pitch_delta_rad']:.3f} | "
            f"{run['foot_contact_ratio']:.2f} | {run['foot_slip_distance']:.3f}m | {fell} | "
            f"{run['action_min']:.2f}..{run['action_max']:.2f} | {run['obs_abs_max']:.2f} |"
        )
    lines.extend(
        [
            "",
            f"Verdict: **{result['verdict']}**",
            "",
            "Browser replay is skipped unless a native visible gate passes.",
            "",
        ]
    )
    (out_dir / "g1-moves-upstream-policy-adapter-parity-summary.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=6.0)
    args = parser.parse_args()
    VERIFY.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="g1_moves_exp99_") as tmp_name:
        tmp = Path(tmp_name)
        onnx_blob = fetch(ONNX_URL)
        npz_blob = fetch(NPZ_URL)
        run_policy_blob = fetch(RUN_POLICY_URL)
        onnx_path = tmp / "policy.onnx"
        npz_path = tmp / "motion.npz"
        onnx_path.write_bytes(onnx_blob)
        npz_path.write_bytes(npz_blob)
        sess = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
        with np.load(npz_path) as motion_npz:
            motion = {key: motion_npz[key].copy() for key in motion_npz.files}
        env = EXP28.ContactAwareSquat(config_overrides={"impl": "jax"})
        model = env.mj_model
        runs = [
            run_variant(
                variant=variant,
                model=model,
                sess=sess,
                motion=motion,
                out_dir=VERIFY / variant["attempt"],
            )
            for variant in variants(args.seconds)
        ]
    visible = [run for run in runs if run["visible_8cm_gate"]]
    result = {
        "planning_gate": {
            "team_validation_mode": "manual-pass",
            "spec_delta": "M19 adapter route now tests upstream run_policy.py observation/control choices against the local model.",
            "perspectives": {
                "product": "checks whether the public standalone runner semantics can unlock native visible evidence",
                "architecture": "isolates pelvis anchor, orientation flattening, default pose, velocity source, and control mode",
                "security": "downloads public source and dataset artifacts only",
                "qa": "native rollout evaluated by exp29 visible gate; per-variant first obs/action saved",
                "skeptic": "local XML actuator semantics may differ from upstream g1_mode15_square.xml",
            },
            "dod": [
                "use upstream run_policy.py choices as a variant",
                "compare key ablations against exp98 choices",
                "skip browser replay unless native visible gate passes",
            ],
        },
        "sources": [
            {"url": RUN_POLICY_URL, "accessed": ACCESS_DATE},
            {"url": "https://github.com/experientialtech/g1-moves", "accessed": ACCESS_DATE},
            {"url": "https://huggingface.co/datasets/exptech/g1-moves", "accessed": ACCESS_DATE},
        ],
        "artifacts": {
            "onnx": {"url": ONNX_URL, "sha256": sha256(onnx_blob), "size_bytes": len(onnx_blob)},
            "npz": {"url": NPZ_URL, "sha256": sha256(npz_blob), "size_bytes": len(npz_blob)},
            "run_policy.py": {"url": RUN_POLICY_URL, "sha256": sha256(run_policy_blob), "size_bytes": len(run_policy_blob)},
        },
        "runs": runs,
        "best_visible": max(visible, key=lambda run: run["visible_drop"], default=None),
        "verdict": "PASS_VISIBLE_NATIVE__BROWSER_REPLAY_REQUIRED" if visible else "FAIL_VISIBLE_NATIVE",
        "next": "If FAIL, the remaining mismatch is likely local XML/actuator semantics; run upstream script against its expected g1_mode15_square.xml or port that XML.",
    }
    write_summary(result, VERIFY)
    (VERIFY / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"verdict": result["verdict"], "best_visible": None if result["best_visible"] is None else result["best_visible"]["attempt"]}, indent=2))
    return 0 if result["verdict"].startswith("PASS_VISIBLE_NATIVE") else 1


if __name__ == "__main__":
    raise SystemExit(main())
