"""Probe a foot-contact-aware low-dimensional height controller for G1 squat."""

from __future__ import annotations

import argparse
import importlib.util
import json
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
EXP36_PATH = ROOT / "experiments/36-g1-wbc-ik-squat-prototype/run_ik_squat.py"
EXP37_PATH = ROOT / "experiments/37-g1-com-support-squat-guard/run_support_guard.py"
EXP46_PARAMS = ROOT / "experiments/46-g1-force-torque-residual/verify/stage-0p74/attempts/force-torque-20k/train/params.pkl"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EXP28 = load_module("exp28_controlled_squat", EXP28_PATH)
EXP36 = load_module("exp36_ik_squat", EXP36_PATH)
EXP37 = load_module("exp37_support_guard", EXP37_PATH)


def qpos_index(model: mujoco.MjModel, joint_name: str) -> int:
    return int(model.jnt_qposadr[model.joint(joint_name).id])


def phase_fraction(t: float, descend_s: float, hold_s: float, return_s: float) -> tuple[float, float]:
    if t < descend_s:
        return min(max(t / descend_s, 0.0), 1.0), 0.0
    if t < descend_s + hold_s:
        return 1.0, 0.0
    if t < descend_s + hold_s + return_s:
        ret = min(max((t - descend_s - hold_s) / return_s, 0.0), 1.0)
        return 1.0 - ret, ret
    return 0.0, 1.0


def health_factor(
    *,
    support_margin: float,
    both_feet: bool,
    foot_slip: float,
    vertical_velocity: float,
    support_floor: float,
    slip_limit: float,
) -> float:
    support_health = np.clip((support_margin - support_floor) / 0.045, 0.0, 1.0)
    slip_health = np.clip(1.0 - foot_slip / slip_limit, 0.0, 1.0)
    contact_health = 1.0 if both_feet else 0.0
    velocity_health = np.clip(1.0 - max(0.0, -vertical_velocity - 0.08) / 0.18, 0.0, 1.0)
    return float(support_health * slip_health * contact_health * velocity_health)


def classify(native: dict[str, Any]) -> str:
    if native["pass_gate"]:
        return "PASS_CONTACT_HEIGHT_NATIVE"
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
    *,
    attempt: str,
    drop: float,
    max_blend: float,
    policy_weight: float,
    adapt_gain: float,
    descend_s: float,
    hold_s: float,
    return_s: float,
    seconds: float,
    support_floor: float,
    slip_limit: float,
    out_dir: Path,
) -> dict[str, Any]:
    env = EXP28.ContactAwareSquat(
        stage_height=0.67,
        controller_blend=max_blend,
        freeze_phase=True,
        blend_schedule="squat",
        reference_scale=1.0,
        config_overrides={"impl": "jax"},
    )
    policy = EXP28.build_policy(env, EXP46_PARAMS) if policy_weight > 0 else None
    model = env.mj_model
    data = mujoco.MjData(model)
    key = model.keyframe("knees_bent")
    data.qpos[:] = key.qpos
    default_pose = key.qpos[7:].astype(np.float32).copy()
    data.ctrl[:] = default_pose
    mujoco.mj_forward(model, data)

    foot_site_ids = np.asarray(env._feet_site_id)
    foot_geom_ids = np.asarray([model.geom("left_foot").id, model.geom("right_foot").id])
    foot_contact_sensor_ids = list(env._feet_floor_found_sensor)
    ik = EXP36.solve_foot_fixed_target(model, key.qpos.copy(), foot_site_ids, drop)
    ik_target = default_pose.copy()
    ik_target[:15] = np.asarray(ik["lower_body_target"], dtype=np.float32)

    gyro_adr = EXP28.sensor_adr(model, "gyro_pelvis")
    linvel_adr = EXP28.sensor_adr(model, "local_linvel_pelvis")
    imu_site = model.site("imu_in_pelvis").id
    ctrl_dt = float(env.dt)
    sim_dt = float(model.opt.timestep)
    n_substeps = max(1, round(ctrl_dt / sim_dt))
    total_steps = int(seconds / ctrl_dt)
    phase = np.ones(2, dtype=np.float32) * np.pi
    command = np.zeros(3, dtype=np.float32)
    last_action = np.zeros(env.action_size, dtype=np.float32)
    gravity_down = np.array([0.0, 0.0, -1.0], dtype=np.float32)
    rng = jax.random.PRNGKey(0)
    initial_foot_xy = data.site_xpos[foot_site_ids, :2].copy()
    start_height = float(data.qpos[2])
    previous_height = start_height
    start_qpos = data.qpos.copy()
    blend_state = 0.0

    qpos_indices = {
        "left_hip_pitch_joint": qpos_index(model, "left_hip_pitch_joint"),
        "right_hip_pitch_joint": qpos_index(model, "right_hip_pitch_joint"),
        "left_knee_joint": qpos_index(model, "left_knee_joint"),
        "right_knee_joint": qpos_index(model, "right_knee_joint"),
    }

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
    max_blend_observed = 0.0
    samples = []

    for step in range(total_steps):
        t = step * ctrl_dt
        height = float(data.qpos[2])
        vertical_velocity = (height - previous_height) / ctrl_dt
        previous_height = height
        final_height = height
        min_height = min(min_height, height)
        desired_fraction, return_phase = phase_fraction(t, descend_s, hold_s, return_s)
        desired_blend = max_blend * desired_fraction

        contacts = [
            float(data.sensordata[model.sensor_adr[sensor_id]]) > 0
            for sensor_id in foot_contact_sensor_ids
        ]
        both_feet = all(contacts)
        both_feet_contact_count += int(both_feet)
        support = EXP37.support_metrics(model, data, foot_geom_ids)
        foot_slip = float(np.max(np.linalg.norm(data.site_xpos[foot_site_ids, :2] - initial_foot_xy, axis=1)))
        health = health_factor(
            support_margin=support["support_margin"],
            both_feet=both_feet,
            foot_slip=foot_slip,
            vertical_velocity=vertical_velocity,
            support_floor=support_floor,
            slip_limit=slip_limit,
        )
        if return_phase > 0.0:
            blend_state = max(0.0, blend_state - max_blend * ctrl_dt / max(return_s, ctrl_dt))
        elif health >= 0.65:
            blend_state = min(desired_blend, blend_state + adapt_gain * health * ctrl_dt)
        else:
            blend_state = max(0.0, blend_state - adapt_gain * (0.65 - health) * ctrl_dt)
        max_blend_observed = max(max_blend_observed, blend_state)

        visible_drop_now = start_height - height
        if visible_drop_now >= 0.08 and first_visible_at is None:
            first_visible_at = round(t, 3)
        min_support_margin = min(min_support_margin, support["support_margin"])
        if support["support_margin"] < support_floor and first_support_breach_at is None:
            first_support_breach_at = round(t, 3)
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
        quat = data.qpos[3:7]
        mat = np.empty(9)
        mujoco.mju_quat2Mat(mat, quat)
        up_z = float(mat.reshape(3, 3)[2, 2])
        if (height < 0.45 or up_z < 0.30) and fell_at is None:
            fell_at = round(t, 3)

        policy_targets = default_pose
        if policy is not None:
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
            policy_targets = default_pose + policy_weight * action_np * float(env._config.action_scale)
            last_action = action_np
        target = (1.0 - blend_state) * policy_targets + blend_state * ik_target
        data.ctrl[:] = np.clip(target, model.actuator_ctrlrange[:, 0], model.actuator_ctrlrange[:, 1])
        for _ in range(n_substeps):
            mujoco.mj_step(model, data)

        if step % max(1, int(0.2 / ctrl_dt)) == 0:
            samples.append({
                "t": round(t, 3),
                "height": height,
                "visible_drop": visible_drop_now,
                "desired_blend": desired_blend,
                "blend_state": blend_state,
                "health": health,
                "support_margin": support["support_margin"],
                "both_feet_contact": both_feet,
                "foot_slip_distance": foot_slip,
                "vertical_velocity": vertical_velocity,
                "up_z": up_z,
            })

    visible_drop = start_height - min_height
    foot_contact_ratio = both_feet_contact_count / max(1, total_steps)
    return_to_stand = final_height >= 0.74
    native = {
        "attempt": attempt,
        "drop": drop,
        "max_blend": max_blend,
        "policy_weight": policy_weight,
        "adapt_gain": adapt_gain,
        "support_floor": support_floor,
        "slip_limit": slip_limit,
        "ik": ik,
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
        "max_blend_observed": max_blend_observed,
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
    native["verdict"] = classify(native)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "native-eval.json").write_text(json.dumps(native, indent=2), encoding="utf-8")
    return native


def write_summary(result: dict[str, Any], out_dir: Path) -> None:
    lines = [
        "# G1 Foot-Contact-Aware Height Controller Summary",
        "",
        "| Attempt | Verdict | Drop | Knee | Hip | Contact | Slip | Final h | Max blend | Fell |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for run in result["runs"]:
        fell = "never" if run["fell_at"] is None else f"{run['fell_at']:.2f}s"
        lines.append(
            f"| {run['attempt']} | {run['verdict']} | {run['visible_drop']:.4f}m | "
            f"{run['max_knee_delta_rad']:.3f} | {run['max_hip_pitch_delta_rad']:.3f} | "
            f"{run['foot_contact_ratio']:.2f} | {run['foot_slip_distance']:.3f}m | "
            f"{run['final_height']:.4f}m | {run['max_blend_observed']:.3f} | {fell} |"
        )
    lines.extend([
        "",
        "M19 closes only when visible depth, knee/hip pose, no-fall, contact, stance, return, and browser replay gates pass together.",
    ])
    (out_dir / "contact-height-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=6.0)
    parser.add_argument("--support-floor", type=float, default=-0.005)
    parser.add_argument("--slip-limit", type=float, default=0.08)
    args = parser.parse_args()

    out_dir = VERIFY / "contact-height-sweep"
    attempts = [
        {"attempt": "drop0p08-blend0p25-adapt0p08-policy1p0", "drop": 0.08, "max_blend": 0.25, "policy_weight": 1.0, "adapt_gain": 0.08},
        {"attempt": "drop0p08-blend0p35-adapt0p10-policy1p0", "drop": 0.08, "max_blend": 0.35, "policy_weight": 1.0, "adapt_gain": 0.10},
        {"attempt": "drop0p10-blend0p35-adapt0p10-policy1p0", "drop": 0.10, "max_blend": 0.35, "policy_weight": 1.0, "adapt_gain": 0.10},
        {"attempt": "drop0p12-blend0p45-adapt0p14-policy1p0", "drop": 0.12, "max_blend": 0.45, "policy_weight": 1.0, "adapt_gain": 0.14},
        {"attempt": "drop0p08-blend0p45-adapt0p16-policy0p15", "drop": 0.08, "max_blend": 0.45, "policy_weight": 0.15, "adapt_gain": 0.16},
    ]
    result = {
        "planning_gate": {
            "team_validation_mode": "manual-pass",
            "spec_delta": "M19 next probe moves from action projection to foot-contact-aware low-dimensional height control.",
            "perspectives": {
                "product": "keeps visible squat gate as the only completion target",
                "architecture": "reuses exp36 foot-fixed IK and exp37 support metrics; policy may only add small residual",
                "security": "no credentials or external side effects",
                "qa": "native sweep logs depth, pose, contact, slip, return, fall",
                "skeptic": "strict foot/contact gating may remain shallow and never reach visible depth",
            },
            "dod": [
                "native sweep writes raw JSON for each controller attempt",
                "summary identifies whether native M19 gate is closer or still blocked",
            ],
        },
        "runs": [],
    }
    for attempt in attempts:
        run_dir = out_dir / attempt["attempt"]
        native = native_eval(
            attempt=attempt["attempt"],
            drop=attempt["drop"],
            max_blend=attempt["max_blend"],
            policy_weight=attempt["policy_weight"],
            adapt_gain=attempt["adapt_gain"],
            descend_s=2.6,
            hold_s=0.4,
            return_s=1.4,
            seconds=args.seconds,
            support_floor=args.support_floor,
            slip_limit=args.slip_limit,
            out_dir=run_dir,
        )
        result["runs"].append(native)
    best = sorted(
        result["runs"],
        key=lambda item: (
            item["pass_gate"],
            item["fell_at"] is None,
            item["visible_drop"] >= 0.08,
            item["foot_slip_distance"] <= 0.15,
            item["return_to_stand"],
            item["visible_drop"],
            item["max_knee_delta_rad"],
        ),
        reverse=True,
    )[0]
    result["best"] = {
        "attempt": best["attempt"],
        "verdict": best["verdict"],
        "visible_drop": best["visible_drop"],
        "foot_slip_distance": best["foot_slip_distance"],
        "foot_contact_ratio": best["foot_contact_ratio"],
        "return_to_stand": best["return_to_stand"],
        "fell_at": best["fell_at"],
    }
    result["verdict"] = "PASS_M19_NATIVE_ONLY" if best["pass_gate"] else "FAIL_M19_NATIVE_GATE"
    out_dir.mkdir(parents=True, exist_ok=True)
    write_summary(result, out_dir)
    (out_dir / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(result["verdict"], json.dumps(result["best"], indent=2), flush=True)


if __name__ == "__main__":
    main()
