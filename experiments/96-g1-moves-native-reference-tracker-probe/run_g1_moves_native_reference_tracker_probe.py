"""Native dynamics tracking probe for the ingested G1 Moves reference window."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any

import mujoco
import numpy as np


EXP_DIR = Path(__file__).resolve().parent
ROOT = EXP_DIR.parents[1]
VERIFY = EXP_DIR / "verify" / "g1-moves-native-reference-tracker-probe"
EXP67_PATH = ROOT / "experiments/67-g1-qfrc-wbc-return-selector/run_qfrc_wbc_return_selector.py"
REFERENCE_PATH = ROOT / "experiments/95-g1-moves-reference-ingestion-gate/verify/g1-moves-reference-ingestion-gate/g1_moves_reference_excerpt_web_trajectory.json"


def load_exp67():
    spec = importlib.util.spec_from_file_location("exp67_qfrc_wbc", EXP67_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {EXP67_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EXP67 = load_exp67()
EXP28 = EXP67.EXP28
EXP37 = EXP67.EXP37
EXP42 = EXP67.EXP42
EXP60 = EXP67.EXP60
EXP62 = EXP67.EXP62
EXP52 = EXP67.EXP52


def load_reference() -> dict[str, Any]:
    return json.loads(REFERENCE_PATH.read_text(encoding="utf-8"))


def convert_root_quat(frame: np.ndarray, mode: str) -> np.ndarray:
    converted = frame.copy()
    if mode == "xyzw_to_wxyz":
        x, y, z, w = converted[3:7].copy()
        converted[3:7] = [w, x, y, z]
    elif mode == "as_recorded":
        pass
    else:
        raise ValueError(f"unknown quat mode {mode}")
    norm = np.linalg.norm(converted[3:7])
    if norm > 0:
        converted[3:7] /= norm
    return converted


def visible_8cm_gate(run: dict[str, Any]) -> bool:
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


def annotate_visible(run: dict[str, Any]) -> dict[str, Any]:
    run["visible_gap"] = {
        "drop_shortfall_m": max(0.0, 0.08 - run["visible_drop"]),
        "knee_shortfall_rad": max(0.0, 0.60 - run["max_knee_delta_rad"]),
        "hip_shortfall_rad": max(0.0, 0.35 - run["max_hip_pitch_delta_rad"]),
        "slip_excess_m": max(0.0, run["foot_slip_distance"] - 0.08),
        "contact_shortfall": max(0.0, 0.90 - run["foot_contact_ratio"]),
    }
    run["visible_8cm_gate"] = visible_8cm_gate(run)
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


def apply_stance_preload(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    foot_site_ids: np.ndarray,
    initial_foot_xyz: np.ndarray,
    foot_contact_sensor_ids: list[int],
    preload_force: float,
    height_kp: float,
    force_clip: float,
) -> np.ndarray:
    qfrc = np.zeros(model.nv)
    if preload_force <= 0.0 or force_clip <= 0.0:
        return qfrc
    for idx, site_id in enumerate(foot_site_ids):
        jacp = np.zeros((3, model.nv))
        jacr = np.zeros((3, model.nv))
        mujoco.mj_jacSite(model, data, jacp, jacr, int(site_id))
        sensor_id = foot_contact_sensor_ids[idx]
        contact = float(data.sensordata[model.sensor_adr[sensor_id]]) > 0.0
        height_err = float(data.site_xpos[site_id, 2] - initial_foot_xyz[idx, 2])
        contact_mult = 1.0 if contact else 1.6
        down_force = min(force_clip, preload_force * contact_mult + height_kp * max(0.0, height_err))
        qfrc += jacp.T @ np.array([0.0, 0.0, -down_force])
    return qfrc


def policy_targets_for_state(env: Any, policy: Any, data: mujoco.MjData, default_pose: np.ndarray, last_action: np.ndarray, phase: np.ndarray, rng: Any, variant: dict[str, Any]) -> tuple[np.ndarray, np.ndarray, Any]:
    gyro_adr = EXP28.sensor_adr(env.mj_model, "gyro_pelvis")
    linvel_adr = EXP28.sensor_adr(env.mj_model, "local_linvel_pelvis")
    imu_site = env.mj_model.site("imu_in_pelvis").id
    gravity_down = np.array([0.0, 0.0, -1.0], dtype=np.float32)
    command = np.zeros(3, dtype=np.float32)
    gyro = data.sensordata[gyro_adr : gyro_adr + 3]
    linvel = data.sensordata[linvel_adr : linvel_adr + 3]
    gravity = data.site_xmat[imu_site].reshape(3, 3).T @ gravity_down
    obs = np.concatenate([
        linvel,
        gyro,
        gravity,
        command,
        data.qpos[7:] - default_pose,
        data.qvel[6:],
        last_action,
        np.concatenate([np.cos(phase), np.sin(phase)]),
    ]).astype(np.float32)
    rng, action_rng = EXP67.jax.random.split(rng)
    action, _ = policy({"state": EXP67.jp.asarray(obs, dtype=EXP67.jp.float32)[None]}, action_rng)
    action_np = np.asarray(action[0], dtype=np.float32)
    return default_pose + variant["policy_weight"] * action_np * float(env._config.action_scale), action_np, rng


def score_run(run: dict[str, Any]) -> float:
    gap = run["visible_gap"]
    score = 0.0
    score += 1800.0 if run["fell_at"] is not None else 0.0
    score += 500.0 * gap["drop_shortfall_m"] / 0.08
    score += 650.0 * gap["knee_shortfall_rad"] / 0.60
    score += 300.0 * gap["hip_shortfall_rad"] / 0.35
    score += 450.0 * gap["slip_excess_m"] / 0.08
    score += 300.0 * gap["contact_shortfall"]
    if not run["return_to_stand"]:
        score += 250.0
    if run["visible_8cm_gate"]:
        score -= 1200.0
    return float(score)


def native_eval(variant: dict[str, Any], reference: dict[str, Any], out_dir: Path) -> dict[str, Any]:
    env = EXP28.ContactAwareSquat(
        stage_height=0.67,
        controller_blend=0.5,
        freeze_phase=True,
        blend_schedule="squat",
        reference_scale=1.0,
        config_overrides={"impl": "jax"},
    )
    policy = EXP28.build_policy(env, EXP52.EXP46_PARAMS)
    model = env.mj_model
    maps = EXP62.joint_maps(model)
    ref_qpos = np.asarray(reference["qpos"], dtype=np.float64)
    ref_fps = float(reference["fps"])
    ref_qpos = np.asarray([convert_root_quat(frame, variant["quat_mode"]) for frame in ref_qpos], dtype=np.float64)
    data = mujoco.MjData(model)
    if variant["start_mode"] == "reference":
        data.qpos[:] = ref_qpos[0]
    elif variant["start_mode"] == "keyframe_joints":
        key = model.keyframe("knees_bent")
        data.qpos[:] = key.qpos
        data.qpos[7:] = ref_qpos[0, 7:]
    else:
        key = model.keyframe("knees_bent")
        data.qpos[:] = key.qpos
    mujoco.mj_forward(model, data)
    key = model.keyframe("knees_bent")
    default_pose = key.qpos[7:].astype(np.float32).copy()
    data.ctrl[:] = data.qpos[7:]
    mujoco.mj_forward(model, data)

    foot_site_ids = np.asarray(env._feet_site_id)
    foot_geom_ids = np.asarray([model.geom("left_foot").id, model.geom("right_foot").id])
    foot_contact_sensor_ids = list(env._feet_floor_found_sensor)
    initial_foot_xyz = data.site_xpos[foot_site_ids, :3].copy()
    ctrl_dt = float(env.dt)
    sim_dt = float(model.opt.timestep)
    n_substeps = max(1, round(ctrl_dt / sim_dt))
    total_steps = min(int(reference["duration_s"] / ctrl_dt), int(variant["seconds"] / ctrl_dt))
    phase = np.ones(2, dtype=np.float32) * np.pi
    last_action = np.zeros(env.action_size, dtype=np.float32)
    rng = EXP67.jax.random.PRNGKey(0)
    start_height = float(data.qpos[2])
    start_qpos = data.qpos.copy()
    pose_indices = {name: EXP62.qpos_index(model, name) for name in EXP67.POSE_JOINTS}
    prev_com_xy = data.subtree_com[0, :2].copy()
    prev_com_vel = np.zeros(2, dtype=np.float64)

    min_height = start_height
    final_height = start_height
    fell_at = None
    both_feet_contact_count = 0
    max_foot_slip = 0.0
    min_support_margin = float("inf")
    min_zmp_margin = float("inf")
    max_joint_violation = 0.0
    max_knee_delta = 0.0
    max_hip_delta = 0.0
    max_qfrc = 0.0
    max_reference_error = 0.0
    qpos_frames: list[list[float]] = []
    samples: list[dict[str, Any]] = []

    for step in range(total_steps):
        t = step * ctrl_dt
        ref_idx = min(len(ref_qpos) - 1, int(round(t * ref_fps)))
        ref = ref_qpos[ref_idx]
        ref_joint_target = ref[7:].astype(np.float32)
        policy_target, action_np, rng = policy_targets_for_state(env, policy, data, default_pose, last_action, phase, rng, variant)
        target = (1.0 - variant["reference_weight"]) * policy_target + variant["reference_weight"] * ref_joint_target
        target = data.qpos[7:] + variant["tracking_step"] * (target - data.qpos[7:])
        np.clip(target, model.actuator_ctrlrange[:, 0], model.actuator_ctrlrange[:, 1], out=target)

        support = EXP37.support_metrics(model, data, foot_geom_ids)
        com_xy, com_vel, zmp = EXP67.zmp_margin(
            model=model,
            data=data,
            support=support,
            prev_com_xy=prev_com_xy,
            prev_com_vel=prev_com_vel,
            ctrl_dt=ctrl_dt,
        )
        foot_slip = float(np.max(np.linalg.norm(data.site_xpos[foot_site_ids, :2] - initial_foot_xyz[:, :2], axis=1)))
        support_health = float(np.clip((support["support_margin"] + 0.005) / 0.045, 0.0, 1.0))
        zmp_health = float(np.clip((zmp + 0.005) / 0.045, 0.0, 1.0))
        slip_health = float(np.clip(1.0 - foot_slip / variant["slip_release"], 0.0, 1.0))
        safety_scale = max(variant["min_safety_scale"], min(support_health, zmp_health, slip_health))
        pd_qfrc, _ = EXP62.lower_pd_torque(
            model=model,
            data=data,
            maps=maps,
            target_qpos=target,
            kp=variant["joint_kp"],
            kd=variant["joint_kd"],
            torque_clip=variant["torque_clip"],
            safety_scale=safety_scale,
        )
        stance_qfrc, _ = EXP62.apply_stance_force(
            model=model,
            data=data,
            foot_site_ids=foot_site_ids,
            initial_foot_xyz=initial_foot_xyz,
            kp_xy=variant["foot_kp_xy"],
            kd_xy=variant["foot_kd_xy"],
            lift_force=variant["foot_lift_force"],
            force_clip=variant["foot_force_clip"],
        )
        preload_qfrc = apply_stance_preload(
            model=model,
            data=data,
            foot_site_ids=foot_site_ids,
            initial_foot_xyz=initial_foot_xyz,
            foot_contact_sensor_ids=foot_contact_sensor_ids,
            preload_force=variant["preload_force"],
            height_kp=variant["preload_height_kp"],
            force_clip=variant["preload_force_clip"],
        )
        data.ctrl[:] = target
        data.qfrc_applied[:] = pd_qfrc + stance_qfrc + preload_qfrc
        max_qfrc = max(max_qfrc, float(np.max(np.abs(data.qfrc_applied))))
        for _ in range(n_substeps):
            mujoco.mj_step(model, data)
        data.qfrc_applied[:] = 0.0
        last_action = action_np
        prev_com_xy = com_xy.copy()
        prev_com_vel = com_vel.copy()

        height = float(data.qpos[2])
        final_height = height
        min_height = min(min_height, height)
        contacts = [
            float(data.sensordata[model.sensor_adr[sensor_id]]) > 0
            for sensor_id in foot_contact_sensor_ids
        ]
        both_feet = all(contacts)
        both_feet_contact_count += int(both_feet)
        max_foot_slip = max(max_foot_slip, foot_slip)
        min_support_margin = min(min_support_margin, support["support_margin"])
        min_zmp_margin = min(min_zmp_margin, zmp)
        max_joint_violation = max(max_joint_violation, EXP28.joint_limit_violation(model, data))
        max_reference_error = max(max_reference_error, float(np.mean(np.square(data.qpos[7:] - ref[7:]))))
        max_knee_delta = max(
            max_knee_delta,
            abs(float(data.qpos[pose_indices["left_knee_joint"]] - start_qpos[pose_indices["left_knee_joint"]])),
            abs(float(data.qpos[pose_indices["right_knee_joint"]] - start_qpos[pose_indices["right_knee_joint"]])),
        )
        max_hip_delta = max(
            max_hip_delta,
            abs(float(data.qpos[pose_indices["left_hip_pitch_joint"]] - start_qpos[pose_indices["left_hip_pitch_joint"]])),
            abs(float(data.qpos[pose_indices["right_hip_pitch_joint"]] - start_qpos[pose_indices["right_hip_pitch_joint"]])),
        )
        quat = data.qpos[3:7]
        mat = np.empty(9)
        mujoco.mju_quat2Mat(mat, quat)
        up_z = float(mat.reshape(3, 3)[2, 2])
        if (height < 0.45 or up_z < 0.30) and fell_at is None:
            fell_at = round(t, 3)
        if step % max(1, int(0.2 / ctrl_dt)) == 0:
            samples.append({
                "t": round(t, 3),
                "ref_idx": ref_idx,
                "height": height,
                "visible_drop": start_height - height,
                "ref_height": float(ref[2]),
                "reference_error": float(np.mean(np.square(data.qpos[7:] - ref[7:]))),
                "support_margin": support["support_margin"],
                "zmp_margin": zmp,
                "both_feet_contact": both_feet,
                "foot_slip_distance": foot_slip,
                "knee_delta": max_knee_delta,
                "hip_delta": max_hip_delta,
                "qfrc_max": float(max_qfrc),
                "up_z": up_z,
            })
        if variant["record_trajectory"]:
            qpos_frames.append([float(v) for v in data.qpos[: model.nq]])

    run = {
        "attempt": variant["attempt"],
        "variant": {k: v for k, v in variant.items() if k != "record_trajectory"},
        "reference": {
            "path": str(REFERENCE_PATH.relative_to(ROOT)),
            "source": reference.get("source"),
            "source_url": reference.get("source_url"),
            "fps": reference.get("fps"),
            "frames": reference.get("frames"),
            "duration_s": reference.get("duration_s"),
        },
        "start_height": start_height,
        "min_height": min_height,
        "visible_drop": start_height - min_height,
        "fell_at": fell_at,
        "final_height": final_height,
        "return_to_stand": final_height >= 0.74,
        "foot_contact_ratio": both_feet_contact_count / max(1, total_steps),
        "foot_slip_distance": max_foot_slip,
        "min_support_margin": min_support_margin,
        "min_zmp_margin": min_zmp_margin,
        "max_joint_limit_violation": max_joint_violation,
        "max_knee_delta_rad": max_knee_delta,
        "max_hip_pitch_delta_rad": max_hip_delta,
        "max_qfrc_applied": max_qfrc,
        "max_reference_error": max_reference_error,
        "samples": samples,
    }
    annotate_visible(run)
    run["optimizer_score"] = score_run(run)
    out_dir.mkdir(parents=True, exist_ok=True)
    if qpos_frames:
        trajectory = {
            "schema": "physical-ai-web-trajectory-v1",
            "source": "native-g1-moves-reference-tracker",
            "scene": "g1/scene_g1_policy.xml",
            "robot": "unitree_g1",
            "fps": round(1.0 / ctrl_dt),
            "nq": model.nq,
            "frames": len(qpos_frames),
            "duration_s": len(qpos_frames) * ctrl_dt,
            "qpos": qpos_frames,
            "note": "Native MuJoCo rollout from exp96 reference tracker probe.",
        }
        (out_dir / "native_rollout_web_trajectory.json").write_text(json.dumps(trajectory), encoding="utf-8")
        run["trajectory_out"] = str((out_dir / "native_rollout_web_trajectory.json").relative_to(ROOT))
    (out_dir / "native-eval.json").write_text(json.dumps(run, indent=2), encoding="utf-8")
    return run


def variants(seconds: float) -> list[dict[str, Any]]:
    common = {
        "seconds": seconds,
        "policy_weight": 1.0,
        "joint_kd": 1.4,
        "foot_kd_xy": 20.0,
        "foot_lift_force": 160.0,
        "slip_release": 0.08,
        "min_safety_scale": 0.35,
        "record_trajectory": True,
    }
    return [
        {**common, "attempt": "as-recorded-open-loop", "quat_mode": "as_recorded", "start_mode": "reference", "reference_weight": 1.0, "tracking_step": 1.0, "joint_kp": 0.0, "torque_clip": 0.0, "foot_kp_xy": 0.0, "foot_force_clip": 0.0, "preload_force": 0.0, "preload_height_kp": 0.0, "preload_force_clip": 0.0},
        {**common, "attempt": "converted-open-loop", "quat_mode": "xyzw_to_wxyz", "start_mode": "reference", "reference_weight": 1.0, "tracking_step": 1.0, "joint_kp": 0.0, "torque_clip": 0.0, "foot_kp_xy": 0.0, "foot_force_clip": 0.0, "preload_force": 0.0, "preload_height_kp": 0.0, "preload_force_clip": 0.0},
        {**common, "attempt": "converted-pd-weak", "quat_mode": "xyzw_to_wxyz", "start_mode": "reference", "reference_weight": 0.55, "tracking_step": 0.45, "joint_kp": 24.0, "torque_clip": 34.0, "foot_kp_xy": 240.0, "foot_force_clip": 220.0, "preload_force": 12.0, "preload_height_kp": 220.0, "preload_force_clip": 54.0},
        {**common, "attempt": "converted-pd-medium", "quat_mode": "xyzw_to_wxyz", "start_mode": "reference", "reference_weight": 0.75, "tracking_step": 0.60, "joint_kp": 34.0, "torque_clip": 54.0, "foot_kp_xy": 480.0, "foot_force_clip": 420.0, "preload_force": 28.0, "preload_height_kp": 620.0, "preload_force_clip": 104.0},
        {**common, "attempt": "converted-pd-strong", "quat_mode": "xyzw_to_wxyz", "start_mode": "reference", "reference_weight": 0.95, "tracking_step": 0.80, "joint_kp": 44.0, "torque_clip": 74.0, "foot_kp_xy": 640.0, "foot_force_clip": 540.0, "preload_force": 38.0, "preload_height_kp": 760.0, "preload_force_clip": 128.0},
        {**common, "attempt": "keyframe-joints-medium", "quat_mode": "xyzw_to_wxyz", "start_mode": "keyframe_joints", "reference_weight": 0.75, "tracking_step": 0.55, "joint_kp": 34.0, "torque_clip": 54.0, "foot_kp_xy": 520.0, "foot_force_clip": 440.0, "preload_force": 30.0, "preload_height_kp": 660.0, "preload_force_clip": 110.0},
    ]


def write_summary(result: dict[str, Any], out_dir: Path) -> None:
    lines = [
        "# G1 Moves Native Reference Tracker Probe Summary",
        "",
        "| Rank | Attempt | Score | Gate | Verdict | Drop | Knee | Hip | Contact | Slip | Ref err | Final h | Fell |",
        "|---:|---|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for rank, run in enumerate(sorted(result["runs"], key=lambda item: item["optimizer_score"]), start=1):
        fell = "never" if run["fell_at"] is None else f"{run['fell_at']:.2f}s"
        gate = "PASS" if run["visible_8cm_gate"] else "FAIL"
        lines.append(
            f"| {rank} | {run['attempt']} | {run['optimizer_score']:.1f} | {gate} | {run['visible_verdict']} | "
            f"{run['visible_drop']:.4f}m | {run['max_knee_delta_rad']:.3f} | {run['max_hip_pitch_delta_rad']:.3f} | "
            f"{run['foot_contact_ratio']:.2f} | {run['foot_slip_distance']:.3f}m | {run['max_reference_error']:.4f} | "
            f"{run['final_height']:.4f}m | {fell} |"
        )
    lines.extend([
        "",
        f"Best optimizer run: {result['best_optimizer']}",
        f"Best visible run: {result['best_visible']}",
        "",
        "M19 closes only when visible native and browser replay both pass.",
    ])
    (out_dir / "g1-moves-native-reference-tracker-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=6.0)
    args = parser.parse_args()
    VERIFY.mkdir(parents=True, exist_ok=True)
    reference = load_reference()
    result = {
        "planning_gate": {
            "team_validation_mode": "manual-pass",
            "spec_delta": "M19 moves from kinematic G1 Moves ingestion to native dynamics tracking of the selected visible reference window.",
            "perspectives": {
                "product": "tests whether the ingested G1 Moves reference can become showable native squat evidence",
                "architecture": "reuses local G1 policy prior, contact WBC helpers, and exp29 visible metrics while testing quaternion-order semantics",
                "security": "local-only; uses committed exp95 reference artifact and no credentials",
                "qa": "records per-variant native JSON, trajectory artifacts, visible gate metrics, and best-run summary",
                "skeptic": "kinematic reference may exceed what this local model/controller can track without the dataset's trained ONNX policy",
            },
            "dod": [
                "native dynamics sweep over reference-tracking variants",
                "explicit PASS/FAIL against exp29 visible_8cm_gate",
                "browser replay candidate trajectory only if native gate passes",
            ],
        },
        "sources": [
            {
                "url": "https://huggingface.co/datasets/exptech/g1-moves",
                "accessed": "2026-06-18",
                "note": "Provides the retargeted G1 reference and notes that trained ONNX policies are available for direct deployment.",
            },
            {
                "url": "https://huggingface.co/spaces/exptech/g1-moves",
                "accessed": "2026-06-18",
                "note": "Space states that every trained policy is available as a 160-input, 29-output ONNX model.",
            },
            {
                "url": "https://arxiv.org/html/2507.07356v3",
                "accessed": "2026-06-18",
                "note": "UniTracker motivates a learned whole-body tracker rather than raw PD playback for difficult G1 motion sequences.",
            },
        ],
        "reference": {
            "path": str(REFERENCE_PATH.relative_to(ROOT)),
            "source_url": reference.get("source_url"),
            "frames": reference.get("frames"),
            "fps": reference.get("fps"),
            "duration_s": reference.get("duration_s"),
            "note": reference.get("note"),
        },
        "runs": [],
    }
    for variant in variants(args.seconds):
        result["runs"].append(native_eval(variant, reference, VERIFY / variant["attempt"]))
    visible = [run for run in result["runs"] if run["visible_8cm_gate"]]
    best_optimizer = min(result["runs"], key=lambda run: run["optimizer_score"])
    best_visible = max(visible, key=lambda run: run["visible_drop"], default=None)
    result["best_optimizer"] = {
        "attempt": best_optimizer["attempt"],
        "optimizer_score": best_optimizer["optimizer_score"],
        "visible_drop": best_optimizer["visible_drop"],
        "max_knee_delta_rad": best_optimizer["max_knee_delta_rad"],
        "max_hip_pitch_delta_rad": best_optimizer["max_hip_pitch_delta_rad"],
        "visible_verdict": best_optimizer["visible_verdict"],
        "fell_at": best_optimizer["fell_at"],
        "trajectory_out": best_optimizer.get("trajectory_out"),
    }
    result["best_visible"] = None if best_visible is None else {
        "attempt": best_visible["attempt"],
        "visible_drop": best_visible["visible_drop"],
        "trajectory_out": best_visible.get("trajectory_out"),
    }
    result["verdict"] = "PASS_VISIBLE_8CM_GATE" if visible else "FAIL_VISIBLE_8CM_GATE"
    write_summary(result, VERIFY)
    (VERIFY / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(result["verdict"], json.dumps({
        "best_optimizer": result["best_optimizer"],
        "best_visible": result["best_visible"],
    }, indent=2), flush=True)


if __name__ == "__main__":
    main()
