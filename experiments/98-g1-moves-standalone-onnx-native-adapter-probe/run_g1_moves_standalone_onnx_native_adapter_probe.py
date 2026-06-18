#!/usr/bin/env python3
"""Approximate standalone native adapter for G1 Moves ONNX policies.

The upstream G1 Moves README documents the 160-d observation layout. This probe
builds that layout from the public NPZ reference plus local MuJoCo state, runs
the public pure actor ONNX, and checks whether the result is already good enough
for the M19 visible native gate.
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
VERIFY = EXP_DIR / "verify" / "g1-moves-standalone-onnx-native-adapter-probe"
EXP96_PATH = ROOT / "experiments/96-g1-moves-native-reference-tracker-probe/run_g1_moves_native_reference_tracker_probe.py"
REFERENCE_PATH = ROOT / "experiments/95-g1-moves-reference-ingestion-gate/verify/g1-moves-reference-ingestion-gate/g1_moves_reference_excerpt_web_trajectory.json"
BASE = "https://huggingface.co/datasets/exptech/g1-moves/resolve/main/dance/J_Dance4_Broadway"
ONNX_URL = f"{BASE}/policy/J_Dance4_Broadway_policy.onnx"
NPZ_URL = f"{BASE}/training/J_Dance4_Broadway.npz"
ACCESS_DATE = "2026-06-18"


def load_exp96():
    spec = importlib.util.spec_from_file_location("exp96_native_tracker", EXP96_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {EXP96_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EXP96 = load_exp96()
EXP67 = EXP96.EXP67
EXP28 = EXP96.EXP28
EXP37 = EXP96.EXP37


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "physical-ai-exp98/1.0"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def quat_to_mat(quat: np.ndarray) -> np.ndarray:
    mat = np.empty(9, dtype=np.float64)
    q = np.asarray(quat, dtype=np.float64).copy()
    norm = np.linalg.norm(q)
    if norm > 0:
        q /= norm
    mujoco.mju_quat2Mat(mat, q)
    return mat.reshape(3, 3)


def body_frame_vector(data: mujoco.MjData, body_id: int, world_vec: np.ndarray) -> np.ndarray:
    body_rot = data.xmat[body_id].reshape(3, 3)
    return body_rot.T @ world_vec


def first_two_cols_relative(anchor_world_rot: np.ndarray, data: mujoco.MjData, body_id: int) -> np.ndarray:
    body_rot = data.xmat[body_id].reshape(3, 3)
    rel = body_rot.T @ anchor_world_rot
    return rel[:, :2].reshape(-1)


def sensor_vec(model: mujoco.MjModel, data: mujoco.MjData, name: str) -> np.ndarray:
    sensor = model.sensor(name)
    adr = int(sensor.adr[0])
    dim = int(sensor.dim[0])
    return np.asarray(data.sensordata[adr : adr + dim], dtype=np.float32)


def load_reference_qpos() -> np.ndarray:
    reference = json.loads(REFERENCE_PATH.read_text(encoding="utf-8"))
    qpos = np.asarray(reference["qpos"], dtype=np.float64)
    return np.asarray([EXP96.convert_root_quat(frame, "xyzw_to_wxyz") for frame in qpos], dtype=np.float64)


def make_obs160(
    *,
    model: mujoco.MjModel,
    data: mujoco.MjData,
    motion: dict[str, np.ndarray],
    motion_idx: int,
    default_pose: np.ndarray,
    last_action: np.ndarray,
    anchor_mode: str,
    quat_mode: str,
) -> np.ndarray:
    ref_joint_pos = np.asarray(motion["joint_pos"][motion_idx], dtype=np.float32)
    ref_joint_vel = np.asarray(motion["joint_vel"][motion_idx], dtype=np.float32)
    pelvis_id = model.body("pelvis").id
    torso_ref_index = 7
    if anchor_mode == "reference":
        anchor_world_pos = np.asarray(motion["body_pos_w"][motion_idx, torso_ref_index], dtype=np.float64)
        anchor_quat = np.asarray(motion["body_quat_w"][motion_idx, torso_ref_index], dtype=np.float64)
        if quat_mode == "xyzw_to_wxyz":
            x, y, z, w = anchor_quat.copy()
            anchor_quat = np.asarray([w, x, y, z], dtype=np.float64)
        anchor_pos_b = body_frame_vector(data, pelvis_id, anchor_world_pos - data.xpos[pelvis_id])
        anchor_ori_b = first_two_cols_relative(quat_to_mat(anchor_quat), data, pelvis_id)
    elif anchor_mode == "zero":
        anchor_pos_b = np.zeros(3, dtype=np.float64)
        anchor_ori_b = np.asarray([1.0, 0.0, 0.0, 0.0, 1.0, 0.0], dtype=np.float64)
    else:
        raise ValueError(anchor_mode)
    base_ang_vel = sensor_vec(model, data, "gyro_pelvis")
    base_lin_vel = sensor_vec(model, data, "local_linvel_pelvis")
    joint_pos_rel = np.asarray(data.qpos[7:] - default_pose, dtype=np.float32)
    joint_vel = np.asarray(data.qvel[6:], dtype=np.float32)
    return np.concatenate(
        [
            ref_joint_pos,
            ref_joint_vel,
            anchor_pos_b.astype(np.float32),
            anchor_ori_b.astype(np.float32),
            base_ang_vel,
            base_lin_vel,
            joint_pos_rel,
            joint_vel,
            last_action.astype(np.float32),
        ]
    ).astype(np.float32)


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
    reference_qpos: np.ndarray,
    out_dir: Path,
) -> dict[str, Any]:
    data = mujoco.MjData(model)
    if variant["start_mode"] == "reference":
        data.qpos[:] = reference_qpos[0]
    else:
        data.qpos[:] = model.keyframe("knees_bent").qpos
    mujoco.mj_forward(model, data)
    default_pose = model.keyframe("knees_bent").qpos[7:].copy()
    data.ctrl[:] = data.qpos[7:]
    mujoco.mj_forward(model, data)
    input_name = sess.get_inputs()[0].name
    output_name = "actions"
    ctrl_dt = 1.0 / 50.0
    n_substeps = max(1, round(ctrl_dt / float(model.opt.timestep)))
    total_steps = int(variant["seconds"] / ctrl_dt)
    start_height = float(data.qpos[2])
    start_qpos = data.qpos.copy()
    foot_site_ids = np.asarray([
        model.site("left_foot").id if "left_foot" in [model.site(i).name for i in range(model.nsite)] else model.site("left_foot_site").id,
        model.site("right_foot").id if "right_foot" in [model.site(i).name for i in range(model.nsite)] else model.site("right_foot_site").id,
    ])
    foot_geom_ids = np.asarray([model.geom("left_foot").id, model.geom("right_foot").id])
    initial_foot_xy = data.site_xpos[foot_site_ids, :2].copy()
    foot_sensor_ids = [model.sensor(name).id for name in ["left_foot_floor_found", "right_foot_floor_found"]]
    pose_indices = {name: EXP67.POSE_QPOS[name] if hasattr(EXP67, "POSE_QPOS") and name in EXP67.POSE_QPOS else EXP96.EXP62.qpos_index(model, name) for name in EXP67.POSE_JOINTS}
    last_action = np.zeros(29, dtype=np.float32)
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
    qpos_frames: list[list[float]] = []
    samples: list[dict[str, Any]] = []

    for step in range(total_steps):
        motion_idx = min(int(round(step * 60.0 / 50.0)), motion["joint_pos"].shape[0] - 1)
        obs = make_obs160(
            model=model,
            data=data,
            motion=motion,
            motion_idx=motion_idx,
            default_pose=default_pose,
            last_action=last_action,
            anchor_mode=variant["anchor_mode"],
            quat_mode=variant["quat_mode"],
        )
        obs_abs_max = max(obs_abs_max, float(np.max(np.abs(obs))))
        action = sess.run([output_name], {input_name: obs[None, :]})[0][0].astype(np.float32)
        action_min = min(action_min, float(np.min(action)))
        action_max = max(action_max, float(np.max(action)))
        target = data.qpos[7:] + variant["action_step"] * (action - data.qpos[7:])
        if variant["blend_reference"] > 0.0:
            ref_target = reference_qpos[min(step, len(reference_qpos) - 1), 7:]
            target = (1.0 - variant["blend_reference"]) * target + variant["blend_reference"] * ref_target
        np.clip(target, model.actuator_ctrlrange[:, 0], model.actuator_ctrlrange[:, 1], out=target)
        data.ctrl[:] = target
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
        if step % max(1, int(0.2 / ctrl_dt)) == 0:
            samples.append(
                {
                    "t": round(step * ctrl_dt, 3),
                    "motion_idx": motion_idx,
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
            "samples": samples,
        }
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    if qpos_frames:
        trajectory = {
            "schema": "physical-ai-web-trajectory-v1",
            "source": "g1-moves-standalone-onnx-native-adapter-probe",
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
    common = {"seconds": seconds, "quat_mode": "wxyz", "record_trajectory": True}
    return [
        {**common, "attempt": "reference-anchor-step1p0", "start_mode": "reference", "anchor_mode": "reference", "action_step": 1.0, "blend_reference": 0.0},
        {**common, "attempt": "reference-anchor-step0p5", "start_mode": "reference", "anchor_mode": "reference", "action_step": 0.5, "blend_reference": 0.0},
        {**common, "attempt": "reference-anchor-step0p25", "start_mode": "reference", "anchor_mode": "reference", "action_step": 0.25, "blend_reference": 0.0},
        {**common, "attempt": "zero-anchor-step0p5", "start_mode": "reference", "anchor_mode": "zero", "action_step": 0.5, "blend_reference": 0.0},
        {**common, "attempt": "keyframe-anchor-step0p5", "start_mode": "keyframe", "anchor_mode": "reference", "action_step": 0.5, "blend_reference": 0.0},
        {**common, "attempt": "reference-anchor-step0p5-refblend0p15", "start_mode": "reference", "anchor_mode": "reference", "action_step": 0.5, "blend_reference": 0.15},
    ]


def write_summary(result: dict[str, Any], out_dir: Path) -> None:
    lines = [
        "# G1 Moves Standalone ONNX Native Adapter Probe Summary",
        "",
        "| Attempt | Gate | Verdict | Drop | Knee | Hip | Contact | Slip | Fell | Action range |",
        "|---|---|---|---:|---:|---:|---:|---:|---|---|",
    ]
    for run in result["runs"]:
        fell = "never" if run["fell_at"] is None else f"{run['fell_at']:.2f}s"
        gate = "PASS" if run["visible_8cm_gate"] else "FAIL"
        lines.append(
            f"| {run['attempt']} | {gate} | {run['visible_verdict']} | {run['visible_drop']:.3f}m | "
            f"{run['max_knee_delta_rad']:.3f} | {run['max_hip_pitch_delta_rad']:.3f} | "
            f"{run['foot_contact_ratio']:.2f} | {run['foot_slip_distance']:.3f}m | {fell} | "
            f"{run['action_min']:.2f}..{run['action_max']:.2f} |"
        )
    lines.extend(
        [
            "",
            f"Verdict: **{result['verdict']}**",
            "",
            "This is an approximate adapter based on the public README observation map. Browser replay is only allowed after a native visible PASS.",
            "",
        ]
    )
    (out_dir / "g1-moves-standalone-onnx-native-adapter-summary.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=6.0)
    args = parser.parse_args()
    VERIFY.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="g1_moves_exp98_") as tmp_name:
        tmp = Path(tmp_name)
        onnx_blob = fetch(ONNX_URL)
        npz_blob = fetch(NPZ_URL)
        onnx_path = tmp / "J_Dance4_Broadway_policy.onnx"
        npz_path = tmp / "J_Dance4_Broadway.npz"
        onnx_path.write_bytes(onnx_blob)
        npz_path.write_bytes(npz_blob)
        sess = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
        with np.load(npz_path) as motion_npz:
            motion = {key: motion_npz[key].copy() for key in motion_npz.files}
        env = EXP28.ContactAwareSquat(
            stage_height=0.67,
            controller_blend=0.5,
            freeze_phase=True,
            blend_schedule="squat",
            reference_scale=1.0,
            config_overrides={"impl": "jax"},
        )
        model = env.mj_model
        reference_qpos = load_reference_qpos()
        runs = [
            run_variant(
                variant=variant,
                model=model,
                sess=sess,
                motion=motion,
                reference_qpos=reference_qpos,
                out_dir=VERIFY / variant["attempt"],
            )
            for variant in variants(args.seconds)
        ]
    visible = [run for run in runs if run["visible_8cm_gate"]]
    result = {
        "planning_gate": {
            "team_validation_mode": "manual-pass",
            "spec_delta": "M19 moves from ONNX contract validation to an approximate standalone native adapter probe.",
            "perspectives": {
                "product": "tests whether public G1 Moves actor can directly generate native visible evidence",
                "architecture": "downloads public ONNX/NPZ transiently and records only hashes and rollout metrics",
                "security": "public artifact download only; no credentials",
                "qa": "native rollout is evaluated against exp29 visible gate; browser replay is skipped unless native passes",
                "skeptic": "README-level observation reconstruction may still differ from upstream mjlab command manager alignment",
            },
            "dod": [
                "construct 160-d observation from public README layout",
                "run ONNX actor in local native MuJoCo",
                "evaluate exp29 visible gate and record trajectory candidates",
            ],
        },
        "sources": [
            {"url": "https://github.com/experientialtech/g1-moves", "accessed": ACCESS_DATE},
            {"url": "https://huggingface.co/datasets/exptech/g1-moves", "accessed": ACCESS_DATE},
        ],
        "artifacts": {
            "onnx": {"url": ONNX_URL, "sha256": sha256(onnx_blob), "size_bytes": len(onnx_blob)},
            "npz": {"url": NPZ_URL, "sha256": sha256(npz_blob), "size_bytes": len(npz_blob)},
        },
        "runs": runs,
        "best_visible": max(visible, key=lambda run: run["visible_drop"], default=None),
        "verdict": "PASS_VISIBLE_NATIVE__BROWSER_REPLAY_REQUIRED" if visible else "FAIL_VISIBLE_NATIVE",
        "next": "If FAIL, compare this adapter against upstream run_policy.py or mjlab command manager before another controller sweep.",
    }
    write_summary(result, VERIFY)
    (VERIFY / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"verdict": result["verdict"], "best_visible": None if result["best_visible"] is None else result["best_visible"]["attempt"]}, indent=2))
    return 0 if result["verdict"].startswith("PASS_VISIBLE_NATIVE") else 1


if __name__ == "__main__":
    raise SystemExit(main())
