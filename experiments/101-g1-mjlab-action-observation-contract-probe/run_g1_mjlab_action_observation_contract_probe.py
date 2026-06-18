#!/usr/bin/env python3
"""Probe mjlab action/observation contract variants for G1 Moves ONNX."""

from __future__ import annotations

import argparse
import hashlib
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
VERIFY = EXP_DIR / "verify" / "g1-mjlab-action-observation-contract-probe"
SCENE = ROOT / "experiments/03-digital-twin/web/assets/scenes/g1/scene_g1_policy.xml"
BASE = "https://huggingface.co/datasets/exptech/g1-moves/resolve/main/dance/J_Dance4_Broadway"
ONNX_URL = f"{BASE}/policy/J_Dance4_Broadway_policy.onnx"
NPZ_URL = f"{BASE}/training/J_Dance4_Broadway.npz"
RUN_POLICY_URL = "https://raw.githubusercontent.com/experientialtech/g1-moves/main/run_policy.py"
MJLAB_G1_CFG_URL = "https://raw.githubusercontent.com/mujocolab/mjlab/main/src/mjlab/tasks/tracking/config/g1/env_cfgs.py"
MJLAB_TRACKING_CFG_URL = "https://raw.githubusercontent.com/mujocolab/mjlab/main/src/mjlab/tasks/tracking/tracking_env_cfg.py"
MJLAB_G1_CONSTANTS_URL = "https://raw.githubusercontent.com/mujocolab/mjlab/main/src/mjlab/asset_zoo/robots/unitree_g1/g1_constants.py"
ACCESS_DATE = "2026-06-18"

JOINT_NAMES = [
    "left_hip_pitch_joint", "left_hip_roll_joint", "left_hip_yaw_joint", "left_knee_joint", "left_ankle_pitch_joint", "left_ankle_roll_joint",
    "right_hip_pitch_joint", "right_hip_roll_joint", "right_hip_yaw_joint", "right_knee_joint", "right_ankle_pitch_joint", "right_ankle_roll_joint",
    "waist_yaw_joint", "waist_roll_joint", "waist_pitch_joint",
    "left_shoulder_pitch_joint", "left_shoulder_roll_joint", "left_shoulder_yaw_joint", "left_elbow_joint", "left_wrist_roll_joint", "left_wrist_pitch_joint", "left_wrist_yaw_joint",
    "right_shoulder_pitch_joint", "right_shoulder_roll_joint", "right_shoulder_yaw_joint", "right_elbow_joint", "right_wrist_roll_joint", "right_wrist_pitch_joint", "right_wrist_yaw_joint",
]


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "physical-ai-exp101/1.0"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def reflected_inertia(rotor_inertia: tuple[float, float, float], gear_ratio: tuple[float, float, float]) -> float:
    return rotor_inertia[0] * (gear_ratio[1] * gear_ratio[2]) ** 2 + rotor_inertia[1] * gear_ratio[2] ** 2 + rotor_inertia[2]


def mjlab_action_scale() -> np.ndarray:
    natural = 10 * 2.0 * np.pi
    vals = {
        "5020": (reflected_inertia((0.139e-4, 0.017e-4, 0.169e-4), (1, 1 + 46 / 18, 1 + 56 / 16)) * natural**2, 25.0),
        "7520_14": (reflected_inertia((0.489e-4, 0.098e-4, 0.533e-4), (1, 4.5, 1 + 48 / 22)) * natural**2, 88.0),
        "7520_22": (reflected_inertia((0.489e-4, 0.109e-4, 0.738e-4), (1, 4.5, 5)) * natural**2, 139.0),
        "4010": (reflected_inertia((0.068e-4, 0.0, 0.0), (1, 5, 5)) * natural**2, 5.0),
    }
    waist_ankle = vals["5020"][0] * 2, vals["5020"][1] * 2
    out = []
    for name in JOINT_NAMES:
        if "hip_pitch" in name or "hip_yaw" in name or name == "waist_yaw_joint":
            stiff, effort = vals["7520_14"]
        elif "hip_roll" in name or "knee" in name:
            stiff, effort = vals["7520_22"]
        elif "wrist_pitch" in name or "wrist_yaw" in name:
            stiff, effort = vals["4010"]
        elif "ankle" in name or name in ("waist_pitch_joint", "waist_roll_joint"):
            stiff, effort = waist_ankle
        else:
            stiff, effort = vals["5020"]
        out.append(0.25 * effort / stiff)
    return np.asarray(out, dtype=np.float32)


def knees_bent_default() -> np.ndarray:
    q = np.zeros(29, dtype=np.float32)
    for i, name in enumerate(JOINT_NAMES):
        if "hip_pitch" in name:
            q[i] = -0.312
        elif "knee" in name:
            q[i] = 0.669
        elif "ankle_pitch" in name:
            q[i] = -0.363
        elif "elbow" in name:
            q[i] = 0.6
        elif name == "left_shoulder_roll_joint":
            q[i] = 0.2
        elif name == "right_shoulder_roll_joint":
            q[i] = -0.2
        elif "shoulder_pitch" in name:
            q[i] = 0.2
    return q


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


def rot6(rot_matrix: np.ndarray) -> np.ndarray:
    return rot_matrix[:, :2].T.flatten()


def sensor_by_name(model: mujoco.MjModel, data: mujoco.MjData, names: tuple[str, ...]) -> np.ndarray | None:
    for name in names:
        sid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SENSOR, name)
        if sid >= 0:
            adr = int(model.sensor_adr[sid])
            dim = int(model.sensor_dim[sid])
            return np.asarray(data.sensordata[adr : adr + dim], dtype=np.float32)
    return None


def make_obs(model: mujoco.MjModel, data: mujoco.MjData, motion: dict[str, np.ndarray], frame: int, last_action: np.ndarray, variant: dict[str, Any]) -> np.ndarray:
    default = variant["default"]
    robot_pos = data.qpos[:3].copy()
    robot_quat = data.qpos[3:7].copy()
    r_robot = quat_to_rot_matrix(robot_quat)
    anchor_idx = int(variant["anchor_index"])
    anchor_pos_b = r_robot.T @ (motion["body_pos_w"][frame, anchor_idx].astype(np.float64) - robot_pos)
    anchor_ori_b = rot6(r_robot.T @ quat_to_rot_matrix(motion["body_quat_w"][frame, anchor_idx].astype(np.float64)))

    named_ang = sensor_by_name(model, data, ("robot/imu_ang_vel", "imu_ang_vel", "imu-pelvis-angular-velocity"))
    named_lin = sensor_by_name(model, data, ("robot/imu_lin_vel", "imu_lin_vel"))
    base_ang = named_ang if named_ang is not None else (data.sensordata[:3].astype(np.float32) if data.sensordata.size >= 3 else np.zeros(3, dtype=np.float32))
    base_lin = named_lin if named_lin is not None else data.qvel[:3].astype(np.float32)
    if variant["velocity_order"] == "ang_lin":
        velocity_terms = [base_ang, base_lin]
    else:
        velocity_terms = [base_lin, base_ang]

    return np.concatenate(
        [
            motion["joint_pos"][frame].astype(np.float32),
            motion["joint_vel"][frame].astype(np.float32),
            anchor_pos_b.astype(np.float32),
            anchor_ori_b.astype(np.float32),
            *velocity_terms,
            data.qpos[7:36].astype(np.float32) - default,
            data.qvel[6:35].astype(np.float32),
            last_action.astype(np.float32),
        ]
    ).astype(np.float32)


def qpos_index(model: mujoco.MjModel, name: str) -> int:
    jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, name)
    if jid < 0:
        raise KeyError(name)
    return int(model.jnt_qposadr[jid])


def run_variant(model: mujoco.MjModel, sess: ort.InferenceSession, motion: dict[str, np.ndarray], variant: dict[str, Any], seconds: float) -> dict[str, Any]:
    data = mujoco.MjData(model)
    model.opt.timestep = 0.005
    data.qpos[:3] = motion["body_pos_w"][0, 0]
    data.qpos[3:7] = motion["body_quat_w"][0, 0]
    data.qpos[7:36] = motion["joint_pos"][0]
    data.qvel[:] = 0.0
    mujoco.mj_forward(model, data)

    input_name = sess.get_inputs()[0].name
    scale = mjlab_action_scale()
    last_action = np.zeros(29, dtype=np.float32)
    fps = float(np.asarray(motion["fps"]).reshape(-1)[0])
    total_steps = int(seconds / 0.02)
    start_qpos = data.qpos.copy()
    start_height = float(data.qpos[2])
    knees = [qpos_index(model, "left_knee_joint"), qpos_index(model, "right_knee_joint")]
    hips = [qpos_index(model, "left_hip_pitch_joint"), qpos_index(model, "right_hip_pitch_joint")]
    foot_sites = [mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, n) for n in ("left_foot", "right_foot")]
    foot_sites = [i for i in foot_sites if i >= 0]
    initial_foot_xy = np.array([data.site_xpos[i, :2].copy() for i in foot_sites]) if foot_sites else np.zeros((0, 2))

    min_height = start_height
    final_height = start_height
    fell_at = None
    max_knee = 0.0
    max_hip = 0.0
    max_slip = 0.0
    action_min = float("inf")
    action_max = -float("inf")
    target_min = float("inf")
    target_max = -float("inf")
    obs_abs_max = 0.0
    first_action: list[float] | None = None
    first_target: list[float] | None = None
    samples = []

    for step in range(total_steps):
        frame = int((step * 0.02 * fps) % motion["joint_pos"].shape[0])
        obs = make_obs(model, data, motion, frame, last_action, variant)
        raw_action = sess.run(["actions"], {input_name: obs[None, :]})[0][0].astype(np.float32)
        if variant["target_mode"] == "direct":
            target = raw_action + variant["default"]
        elif variant["target_mode"] == "mjlab_scaled":
            target = raw_action * scale + variant["default"]
        else:
            raise ValueError(variant["target_mode"])
        if first_action is None:
            first_action = [float(v) for v in raw_action]
            first_target = [float(v) for v in target]
        obs_abs_max = max(obs_abs_max, float(np.max(np.abs(obs))))
        action_min = min(action_min, float(np.min(raw_action)))
        action_max = max(action_max, float(np.max(raw_action)))
        target_min = min(target_min, float(np.min(target)))
        target_max = max(target_max, float(np.max(target)))
        np.clip(target, model.actuator_ctrlrange[:29, 0], model.actuator_ctrlrange[:29, 1], out=target)
        data.ctrl[:29] = target
        for _ in range(4):
            mujoco.mj_step(model, data)
        last_action = raw_action

        height = float(data.qpos[2])
        final_height = height
        min_height = min(min_height, height)
        max_knee = max(max_knee, *(abs(float(data.qpos[i] - start_qpos[i])) for i in knees))
        max_hip = max(max_hip, *(abs(float(data.qpos[i] - start_qpos[i])) for i in hips))
        if foot_sites:
            foot_xy = np.array([data.site_xpos[i, :2].copy() for i in foot_sites])
            max_slip = max(max_slip, float(np.max(np.linalg.norm(foot_xy - initial_foot_xy, axis=1))))
        mat = np.empty(9)
        mujoco.mju_quat2Mat(mat, data.qpos[3:7])
        up_z = float(mat.reshape(3, 3)[2, 2])
        if fell_at is None and (height < 0.45 or up_z < 0.30):
            fell_at = round(step * 0.02, 3)
        if step % 10 == 0:
            samples.append({"t": round(step * 0.02, 3), "height": height, "drop": start_height - height, "knee": max_knee, "hip": max_hip, "slip": max_slip, "up_z": up_z})

    gate = fell_at is None and start_height - min_height >= 0.08 and max_knee >= 0.60 and max_hip >= 0.35 and final_height >= start_height - 0.03 and max_slip <= 0.08
    return {
        "attempt": variant["attempt"],
        "variant": {k: v for k, v in variant.items() if k != "default"},
        "default_name": variant["default_name"],
        "start_height": start_height,
        "min_height": min_height,
        "visible_drop": start_height - min_height,
        "fell_at": fell_at,
        "final_height": final_height,
        "return_to_stand": final_height >= start_height - 0.03,
        "max_knee_delta_rad": max_knee,
        "max_hip_pitch_delta_rad": max_hip,
        "foot_slip_distance": max_slip,
        "action_min": action_min,
        "action_max": action_max,
        "target_min": target_min,
        "target_max": target_max,
        "obs_abs_max": obs_abs_max,
        "first_action29": first_action,
        "first_target29": first_target,
        "samples": samples,
        "visible_8cm_gate": gate,
        "visible_verdict": "PASS_VISIBLE_NATIVE" if gate else ("FAIL_FALL" if fell_at is not None else "FAIL_VISIBLE_GATE"),
    }


def variants() -> list[dict[str, Any]]:
    zero = np.zeros(29, dtype=np.float32)
    knees = knees_bent_default()
    return [
        {"attempt": "run-policy-baseline", "anchor_index": 0, "velocity_order": "ang_lin", "target_mode": "direct", "default": zero, "default_name": "zero"},
        {"attempt": "mjlab-obs-direct-zero", "anchor_index": 7, "velocity_order": "lin_ang", "target_mode": "direct", "default": zero, "default_name": "zero"},
        {"attempt": "mjlab-obs-scaled-zero", "anchor_index": 7, "velocity_order": "lin_ang", "target_mode": "mjlab_scaled", "default": zero, "default_name": "zero"},
        {"attempt": "mjlab-obs-scaled-knees-bent", "anchor_index": 7, "velocity_order": "lin_ang", "target_mode": "mjlab_scaled", "default": knees, "default_name": "mjlab_knees_bent"},
    ]


def write_summary(result: dict[str, Any]) -> None:
    lines = [
        "# G1 mjlab Action/Observation Contract Probe Summary",
        "",
        "| Attempt | Verdict | Drop | Knee | Hip | Slip | Fell | Action range | Target range | Obs max |",
        "|---|---|---:|---:|---:|---:|---|---|---|---:|",
    ]
    for run in result["runs"]:
        fell = "never" if run["fell_at"] is None else f"{run['fell_at']:.2f}s"
        lines.append(
            f"| {run['attempt']} | {run['visible_verdict']} | {run['visible_drop']:.3f}m | {run['max_knee_delta_rad']:.3f} | "
            f"{run['max_hip_pitch_delta_rad']:.3f} | {run['foot_slip_distance']:.3f}m | {fell} | "
            f"{run['action_min']:.2f}..{run['action_max']:.2f} | {run['target_min']:.2f}..{run['target_max']:.2f} | {run['obs_abs_max']:.2f} |"
        )
    lines.extend(["", f"Verdict: **{result['verdict']}**", ""])
    (VERIFY / "g1-mjlab-action-observation-contract-summary.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=6.0)
    args = parser.parse_args()
    VERIFY.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="g1_exp101_") as tmp_name:
        tmp = Path(tmp_name)
        blobs = {name: fetch(url) for name, url in {
            "onnx": ONNX_URL,
            "npz": NPZ_URL,
            "run_policy": RUN_POLICY_URL,
            "mjlab_g1_cfg": MJLAB_G1_CFG_URL,
            "mjlab_tracking_cfg": MJLAB_TRACKING_CFG_URL,
            "mjlab_g1_constants": MJLAB_G1_CONSTANTS_URL,
        }.items()}
        onnx_path = tmp / "policy.onnx"
        npz_path = tmp / "motion.npz"
        onnx_path.write_bytes(blobs["onnx"])
        npz_path.write_bytes(blobs["npz"])
        sess = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
        with np.load(npz_path) as motion_npz:
            motion = {key: motion_npz[key].copy() for key in motion_npz.files}
        model = mujoco.MjModel.from_xml_path(str(SCENE))
        runs = []
        for variant in variants():
            run = run_variant(model, sess, motion, variant, args.seconds)
            out_dir = VERIFY / variant["attempt"]
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "native-eval.json").write_text(json.dumps(run, indent=2), encoding="utf-8")
            runs.append(run)

    visible = [run for run in runs if run["visible_8cm_gate"]]
    result = {
        "planning_gate": {
            "team_validation_mode": "manual-pass",
            "spec_delta": "M19 adapter route now tests mjlab tracking observation/action semantics before retraining.",
            "perspectives": {
                "product": "checks whether public G1 Moves ONNX can be stabilized without new training",
                "architecture": "isolates anchor index, velocity order, default offset, and action scale",
                "security": "downloads public source/model/data only and records hashes",
                "qa": "same native visible gate metrics; browser replay gated on native pass",
                "skeptic": "G1 Moves run_policy.py may intentionally differ from current mjlab source, so this can falsify but not prove exact parity",
            },
            "dod": ["run baseline and mjlab contract variants", "record native metrics", "skip browser unless native gate passes"],
        },
        "sources": [
            {"url": RUN_POLICY_URL, "accessed": ACCESS_DATE},
            {"url": MJLAB_G1_CFG_URL, "accessed": ACCESS_DATE},
            {"url": MJLAB_TRACKING_CFG_URL, "accessed": ACCESS_DATE},
            {"url": MJLAB_G1_CONSTANTS_URL, "accessed": ACCESS_DATE},
            {"url": "https://huggingface.co/datasets/exptech/g1-moves/blob/fce747a1677d5e6ffbc45e04f9fbdc0252b276f5/CLAUDE.md", "accessed": ACCESS_DATE},
        ],
        "artifacts": {name: {"sha256": sha256(blob), "size_bytes": len(blob)} for name, blob in blobs.items()},
        "scene": str(SCENE.relative_to(ROOT)),
        "action_scale": [float(v) for v in mjlab_action_scale()],
        "runs": runs,
        "verdict": "PASS_VISIBLE_NATIVE__BROWSER_REPLAY_REQUIRED" if visible else "FAIL_VISIBLE_NATIVE",
        "next": "If all variants fail, the remaining path is exact g1_mode15_square.xml acquisition or retraining a squat tracker in the local scene.",
    }
    (VERIFY / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    write_summary(result)
    print(json.dumps({"verdict": result["verdict"], "visible": [run["attempt"] for run in visible]}, indent=2))
    return 0 if visible else 1


if __name__ == "__main__":
    raise SystemExit(main())
