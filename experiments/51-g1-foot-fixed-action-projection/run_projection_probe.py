"""Evaluate stance-aware action projection for G1 visible squat policies."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import jax
import jax.numpy as jp
import mujoco
import numpy as np


EXP_DIR = Path(__file__).resolve().parent
ROOT = EXP_DIR.parents[1]
VERIFY = EXP_DIR / "verify"
EXP28_PATH = ROOT / "experiments/28-g1-controlled-squat-stage0p74/run_controlled_squat.py"
EXP37_PATH = ROOT / "experiments/37-g1-com-support-squat-guard/run_support_guard.py"
EXP50 = ROOT / "experiments/50-g1-stance-constrained-curriculum-ppo"
EXP50_RUN = EXP50 / "run_stance_constrained.py"
EXP50_PARAMS = EXP50 / "verify/target-0p03-slip-0p08/train/params.pkl"
EXP46_PARAMS = ROOT / "experiments/46-g1-force-torque-residual/verify/stage-0p74/attempts/force-torque-20k/train/params.pkl"

if str(EXP50) not in sys.path:
    sys.path.insert(0, str(EXP50))


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EXP28 = load_module("exp28_controlled_squat", EXP28_PATH)
EXP37 = load_module("exp37_support_guard", EXP37_PATH)
EXP50_RUNNER = load_module("exp50_stance_constrained", EXP50_RUN)


def safe_float(value: Any) -> float:
    return float(np.asarray(value))


def qpos_index(model: mujoco.MjModel, joint_name: str) -> int:
    return int(model.jnt_qposadr[model.joint(joint_name).id])


def residual_clip(action: np.ndarray, desired: np.ndarray, residual_limit: float) -> np.ndarray:
    return desired + np.clip(action - desired, -residual_limit, residual_limit)


def projected_action(
    mode: str,
    action: np.ndarray,
    desired: np.ndarray,
    health: float,
    ankle_indices: list[int],
    residual_limit: float,
) -> np.ndarray:
    health = float(np.clip(health, 0.0, 1.0))
    if mode == "none":
        return action
    if mode == "default-brake":
        return health * action
    if mode == "soft-brake":
        return (0.35 + 0.65 * health) * action
    if mode in {"residual-clamp-only", "ankle-lock-only"}:
        candidate = residual_clip(action, desired, residual_limit)
        if mode == "ankle-lock-only":
            candidate[ankle_indices] = desired[ankle_indices] + np.clip(
                action[ankle_indices] - desired[ankle_indices],
                -0.03,
                0.03,
            )
        return candidate
    if mode in {"residual-clamp", "ankle-lock"}:
        candidate = residual_clip(action, desired, residual_limit)
        if mode == "ankle-lock":
            candidate[ankle_indices] = desired[ankle_indices] + np.clip(
                action[ankle_indices] - desired[ankle_indices],
                -0.03,
                0.03,
            )
        return health * candidate
    raise ValueError(f"unknown projection mode: {mode}")


def verdict(native: dict[str, Any]) -> str:
    if native["pass_gate"]:
        return "PASS_PROJECTED_VISIBLE_SQUAT"
    if native["fell_at"] is not None:
        return "FAIL_FALL"
    if native["visible_drop"] < 0.08:
        return "DEPTH_PENDING"
    if native["max_knee_delta_rad"] < 0.60 or native["max_hip_pitch_delta_rad"] < 0.35:
        return "POSE_GATE_PENDING"
    if not native["return_to_stand"]:
        return "RETURN_PENDING"
    if native["foot_contact_ratio"] < 0.90:
        return "CONTACT_GATE_PENDING"
    if native["foot_slip_distance"] > 0.15:
        return "STANCE_SLIP_PENDING"
    return "GATE_PENDING"


def native_eval(
    params_path: Path,
    target_drop: float,
    mode: str,
    residual_limit: float,
    support_floor: float,
    slip_limit: float,
    seconds: float,
    out_dir: Path,
) -> dict[str, Any]:
    env = EXP50_RUNNER.make_env(target_drop, support_floor, slip_limit)
    policy = EXP50_RUNNER.build_policy(env, params_path)
    model = env.mj_model
    data = mujoco.MjData(model)
    key = model.keyframe("knees_bent")
    data.qpos[:] = key.qpos
    default_pose = key.qpos[7:].astype(np.float32).copy()
    data.ctrl[:] = default_pose
    mujoco.mj_forward(model, data)

    gyro_adr = EXP28.sensor_adr(model, "gyro_pelvis")
    linvel_adr = EXP28.sensor_adr(model, "local_linvel_pelvis")
    imu_site = model.site("imu_in_pelvis").id
    foot_site_ids = np.asarray(env._feet_site_id)
    foot_geom_ids = np.asarray([model.geom("left_foot").id, model.geom("right_foot").id])
    foot_contact_sensor_ids = list(env._feet_floor_found_sensor)
    initial_foot_xy = data.site_xpos[foot_site_ids, :2].copy()
    ctrl_dt = float(env.dt)
    sim_dt = float(model.opt.timestep)
    n_substeps = max(1, round(ctrl_dt / sim_dt))
    total_steps = int(seconds / ctrl_dt)
    phase = np.ones(2, dtype=np.float32) * np.pi
    last_action = np.zeros(env.action_size, dtype=np.float32)
    gravity_down = np.array([0.0, 0.0, -1.0], dtype=np.float32)
    rng = jax.random.PRNGKey(0)
    start_height = float(data.qpos[2])
    start_qpos = data.qpos.copy()

    qpos_indices = {
        "left_hip_pitch_joint": qpos_index(model, "left_hip_pitch_joint"),
        "right_hip_pitch_joint": qpos_index(model, "right_hip_pitch_joint"),
        "left_knee_joint": qpos_index(model, "left_knee_joint"),
        "right_knee_joint": qpos_index(model, "right_knee_joint"),
    }
    ankle_action_indices = [
        model.actuator("left_ankle_pitch_joint").id,
        model.actuator("left_ankle_roll_joint").id,
        model.actuator("right_ankle_pitch_joint").id,
        model.actuator("right_ankle_roll_joint").id,
    ]

    min_height = start_height
    final_height = start_height
    fell_at = None
    first_visible_at = None
    first_support_breach_at = None
    first_slip_breach_at = None
    both_feet_contact_count = 0
    max_foot_slip = 0.0
    min_support_margin = float("inf")
    max_joint_violation = 0.0
    max_knee_delta = 0.0
    max_hip_delta = 0.0
    max_action_norm = 0.0
    max_projected_delta = 0.0
    samples = []

    for step in range(total_steps):
        t = step * ctrl_dt
        command = np.asarray(env._squat_command(jp.asarray(step, dtype=jp.int32)), dtype=np.float32)
        target_pose, _, _ = env._command_target_pose(jp.asarray(step, dtype=jp.int32))
        desired_action = np.asarray(
            jp.clip((target_pose - env._default_pose) / env._config.action_scale, -1.0, 1.0),
            dtype=np.float32,
        )
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
        rng, action_rng = jax.random.split(rng)
        action, _ = policy({"state": jp.asarray(obs, dtype=jp.float32)[None]}, action_rng)
        action_np = np.asarray(action[0], dtype=np.float32)

        support = EXP37.support_metrics(model, data, foot_geom_ids)
        foot_slip_before = float(np.max(np.linalg.norm(data.site_xpos[foot_site_ids, :2] - initial_foot_xy, axis=1)))
        support_health = np.clip((support["support_margin"] - support_floor) / 0.04, 0.0, 1.0)
        slip_health = np.clip(1.0 - foot_slip_before / slip_limit, 0.0, 1.0)
        health = float(support_health * slip_health)
        projected = projected_action(mode, action_np, desired_action, health, ankle_action_indices, residual_limit)

        data.ctrl[:] = np.clip(default_pose + projected * float(env._config.action_scale), model.actuator_ctrlrange[:, 0], model.actuator_ctrlrange[:, 1])
        for _ in range(n_substeps):
            mujoco.mj_step(model, data)
        last_action = projected

        height = float(data.qpos[2])
        final_height = height
        min_height = min(min_height, height)
        visible_drop_now = start_height - height
        if visible_drop_now >= 0.08 and first_visible_at is None:
            first_visible_at = round(t, 3)
        contacts = [
            float(data.sensordata[model.sensor_adr[sensor_id]]) > 0
            for sensor_id in foot_contact_sensor_ids
        ]
        both_feet = all(contacts)
        both_feet_contact_count += int(both_feet)
        support = EXP37.support_metrics(model, data, foot_geom_ids)
        min_support_margin = min(min_support_margin, support["support_margin"])
        if support["support_margin"] < support_floor and first_support_breach_at is None:
            first_support_breach_at = round(t, 3)
        foot_slip = float(np.max(np.linalg.norm(data.site_xpos[foot_site_ids, :2] - initial_foot_xy, axis=1)))
        max_foot_slip = max(max_foot_slip, foot_slip)
        if foot_slip > slip_limit and first_slip_breach_at is None:
            first_slip_breach_at = round(t, 3)
        max_joint_violation = max(max_joint_violation, EXP28.joint_limit_violation(model, data))
        max_knee_delta = max(
            max_knee_delta,
            abs(float(data.qpos[qpos_indices["left_knee_joint"]] - start_qpos[qpos_indices["left_knee_joint"]])),
            abs(float(data.qpos[qpos_indices["right_knee_joint"]] - start_qpos[qpos_indices["right_knee_joint"]])),
        )
        max_hip_delta = max(
            max_hip_delta,
            abs(float(data.qpos[qpos_indices["left_hip_pitch_joint"]] - start_qpos[qpos_indices["left_hip_pitch_joint"]])),
            abs(float(data.qpos[qpos_indices["right_hip_pitch_joint"]] - start_qpos[qpos_indices["right_hip_pitch_joint"]])),
        )
        max_action_norm = max(max_action_norm, float(np.linalg.norm(projected)))
        max_projected_delta = max(max_projected_delta, float(np.max(np.abs(projected - action_np))))
        quat = data.qpos[3:7]
        mat = np.empty(9)
        mujoco.mju_quat2Mat(mat, quat)
        up_z = float(mat.reshape(3, 3)[2, 2])
        if (height < 0.45 or up_z < 0.30) and fell_at is None:
            fell_at = round(t, 3)

        if step % max(1, int(0.2 / ctrl_dt)) == 0:
            samples.append({
                "t": round(t, 3),
                "height": height,
                "visible_drop": visible_drop_now,
                "command": [float(v) for v in command],
                "support_margin": support["support_margin"],
                "health": health,
                "both_feet_contact": both_feet,
                "foot_slip_distance": foot_slip,
                "up_z": up_z,
                "action_norm": float(np.linalg.norm(action_np)),
                "projected_action_norm": float(np.linalg.norm(projected)),
            })

    visible_drop = start_height - min_height
    foot_contact_ratio = both_feet_contact_count / max(1, total_steps)
    return_to_stand = final_height >= 0.74
    native = {
        "mode": mode,
        "params_path": str(params_path),
        "target_drop": target_drop,
        "support_floor": support_floor,
        "slip_limit": slip_limit,
        "residual_limit": residual_limit,
        "start_height": start_height,
        "min_height": min_height,
        "visible_drop": visible_drop,
        "first_visible_at": first_visible_at,
        "fell_at": fell_at,
        "final_height": final_height,
        "return_to_stand": return_to_stand,
        "foot_contact_ratio": foot_contact_ratio,
        "foot_slip_distance": max_foot_slip,
        "min_support_margin": min_support_margin,
        "first_support_breach_at": first_support_breach_at,
        "first_slip_breach_at": first_slip_breach_at,
        "max_joint_limit_violation": max_joint_violation,
        "max_knee_delta_rad": max_knee_delta,
        "max_hip_pitch_delta_rad": max_hip_delta,
        "max_action_norm": max_action_norm,
        "max_projected_delta": max_projected_delta,
        "pass_gate": (
            fell_at is None
            and visible_drop >= 0.08
            and max_knee_delta >= 0.60
            and max_hip_delta >= 0.35
            and return_to_stand
            and foot_contact_ratio >= 0.90
            and max_foot_slip <= 0.15
            and max_joint_violation <= 0.05
        ),
        "samples": samples,
    }
    native["verdict"] = verdict(native)
    path = out_dir / f"{mode}.json"
    path.write_text(json.dumps(native, indent=2), encoding="utf-8")
    return native


def write_summary(result: dict[str, Any], out_dir: Path) -> None:
    lines = [
        "# G1 Foot-Fixed Action Projection Summary",
        "",
        "| Source | Mode | Verdict | Drop | Knee | Hip | Contact | Slip | Final h | Fell |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for run in result["runs"]:
        fell = "never" if run["fell_at"] is None else f"{run['fell_at']:.2f}s"
        lines.append(
            f"| {run['source_name']} | {run['mode']} | {run['verdict']} | "
            f"{run['visible_drop']:.4f}m | {run['max_knee_delta_rad']:.3f} | "
            f"{run['max_hip_pitch_delta_rad']:.3f} | {run['foot_contact_ratio']:.2f} | "
            f"{run['foot_slip_distance']:.3f}m | {run['final_height']:.4f}m | {fell} |"
        )
    lines.extend([
        "",
        "M19 closes only when visible depth, knee/hip pose, no-fall, contact, stance, return, and browser replay gates pass together.",
    ])
    (out_dir / "projection-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=6.0)
    parser.add_argument("--target-drop", type=float, default=0.08)
    parser.add_argument("--support-floor", type=float, default=-0.005)
    parser.add_argument("--slip-limit", type=float, default=0.08)
    parser.add_argument("--residual-limit", type=float, default=0.08)
    parser.add_argument(
        "--modes",
        nargs="+",
        default=[
            "none",
            "soft-brake",
            "default-brake",
            "residual-clamp-only",
            "ankle-lock-only",
            "residual-clamp",
            "ankle-lock",
        ],
    )
    args = parser.parse_args()

    out_dir = VERIFY / f"target-{args.target_drop:.2f}-residual-{args.residual_limit:.2f}".replace(".", "p")
    out_dir.mkdir(parents=True, exist_ok=True)
    sources = [
        ("exp50", EXP50_PARAMS),
        ("exp46", EXP46_PARAMS),
    ]
    result = {
        "planning_gate": {
            "team_validation_mode": "manual-pass",
            "spec_delta": "M19 next probe adds stance-aware action projection between policy output and motor target.",
            "perspectives": {
                "product": "targets the current blocker: visible depth without foot slip",
                "architecture": "evaluation-only projection layer; no checkpoint shape changes",
                "security": "no secrets or external credentials",
                "qa": "native rollout logs depth, knee/hip pose, contact, slip, return, fall",
                "skeptic": "projection may protect stance by killing the squat command entirely",
            },
            "dod": [
                "projection sweep produces raw JSON per mode",
                "summary reports whether M19 native gate improved",
            ],
        },
        "target_drop": args.target_drop,
        "support_floor": args.support_floor,
        "slip_limit": args.slip_limit,
        "residual_limit": args.residual_limit,
        "runs": [],
    }
    for source_name, params_path in sources:
        if not params_path.exists():
            continue
        for mode in args.modes:
            run_dir = out_dir / source_name
            run_dir.mkdir(parents=True, exist_ok=True)
            native = native_eval(
                params_path=params_path,
                target_drop=args.target_drop,
                mode=mode,
                residual_limit=args.residual_limit,
                support_floor=args.support_floor,
                slip_limit=args.slip_limit,
                seconds=args.seconds,
                out_dir=run_dir,
            )
            native["source_name"] = source_name
            result["runs"].append(native)
    best = sorted(
        result["runs"],
        key=lambda item: (
            item["pass_gate"],
            item["fell_at"] is None,
            item["visible_drop"] >= 0.08,
            item["foot_slip_distance"] <= 0.15,
            item["return_to_stand"],
            item["foot_contact_ratio"],
            -item["foot_slip_distance"],
        ),
        reverse=True,
    )[0]
    result["best"] = {
        "source_name": best["source_name"],
        "mode": best["mode"],
        "verdict": best["verdict"],
        "visible_drop": best["visible_drop"],
        "foot_slip_distance": best["foot_slip_distance"],
        "foot_contact_ratio": best["foot_contact_ratio"],
        "return_to_stand": best["return_to_stand"],
    }
    result["verdict"] = "PASS_M19_NATIVE_ONLY" if best["pass_gate"] else "FAIL_M19_NATIVE_GATE"
    write_summary(result, out_dir)
    (out_dir / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(result["verdict"], json.dumps(result["best"], indent=2), flush=True)


if __name__ == "__main__":
    main()
