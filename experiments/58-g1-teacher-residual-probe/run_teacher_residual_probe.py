"""Probe bounded residuals on top of the exp55 CoM-feedback teacher."""

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
EXP52_PATH = ROOT / "experiments/52-g1-foot-contact-aware-height-controller/run_contact_height_controller.py"


def load_exp52():
    spec = importlib.util.spec_from_file_location("exp52_contact_height", EXP52_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {EXP52_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EXP52 = load_exp52()
EXP28 = EXP52.EXP28
EXP36 = EXP52.EXP36
EXP37 = EXP52.EXP37


G = 9.81


def support_center(support: dict[str, Any]) -> np.ndarray:
    return 0.5 * (np.asarray(support["support_min_xy"]) + np.asarray(support["support_max_xy"]))


def support_margin_for_point(point_xy: np.ndarray, support: dict[str, Any]) -> float:
    min_xy = np.asarray(support["support_min_xy"])
    max_xy = np.asarray(support["support_max_xy"])
    margins = np.array([
        point_xy[0] - min_xy[0],
        max_xy[0] - point_xy[0],
        point_xy[1] - min_xy[1],
        max_xy[1] - point_xy[1],
    ])
    return float(np.min(margins))


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
    zmp_margin: float,
    both_feet: bool,
    foot_slip: float,
    vertical_velocity: float,
    support_floor: float,
    slip_limit: float,
) -> float:
    support_health = np.clip((support_margin - support_floor) / 0.045, 0.0, 1.0)
    zmp_health = np.clip((zmp_margin - support_floor) / 0.045, 0.0, 1.0)
    slip_health = np.clip(1.0 - foot_slip / slip_limit, 0.0, 1.0)
    contact_health = 1.0 if both_feet else 0.0
    velocity_health = np.clip(1.0 - max(0.0, -vertical_velocity - 0.08) / 0.18, 0.0, 1.0)
    return float(support_health * zmp_health * slip_health * contact_health * velocity_health)


def qpos_index(model: mujoco.MjModel, joint_name: str) -> int:
    return int(model.jnt_qposadr[model.joint(joint_name).id])


def ctrl_index(model: mujoco.MjModel, actuator_name: str) -> int:
    return int(model.actuator(actuator_name).id)


def apply_feedback(
    target: np.ndarray,
    *,
    model: mujoco.MjModel,
    error_xy: np.ndarray,
    gains: dict[str, float],
    signs: dict[str, float],
) -> np.ndarray:
    adjusted = target.copy()
    pitch = float(np.clip(signs["pitch"] * gains["pitch"] * error_xy[0], -gains["clip_pitch"], gains["clip_pitch"]))
    ankle_pitch = float(np.clip(signs["ankle_pitch"] * gains["ankle_pitch"] * error_xy[0], -gains["clip_pitch"], gains["clip_pitch"]))
    roll = float(np.clip(signs["roll"] * gains["roll"] * error_xy[1], -gains["clip_roll"], gains["clip_roll"]))
    ankle_roll = float(np.clip(signs["ankle_roll"] * gains["ankle_roll"] * error_xy[1], -gains["clip_roll"], gains["clip_roll"]))
    for name, delta in (
        ("left_hip_pitch_joint", pitch),
        ("right_hip_pitch_joint", pitch),
        ("left_ankle_pitch_joint", ankle_pitch),
        ("right_ankle_pitch_joint", ankle_pitch),
        ("left_hip_roll_joint", roll),
        ("right_hip_roll_joint", -roll),
        ("left_ankle_roll_joint", ankle_roll),
        ("right_ankle_roll_joint", -ankle_roll),
    ):
        idx = ctrl_index(model, name)
        adjusted[idx] += delta
    return np.clip(adjusted, model.actuator_ctrlrange[:, 0], model.actuator_ctrlrange[:, 1])


def apply_residual_pattern(
    target: np.ndarray,
    *,
    model: mujoco.MjModel,
    pattern: str,
    scale: float,
    phase_depth: float,
    support_health: float,
) -> np.ndarray:
    adjusted = target.copy()
    amount = float(scale * phase_depth * np.clip(support_health, 0.0, 1.0))
    if amount <= 0.0 or pattern == "none":
        return adjusted
    if pattern == "knee_only":
        deltas = {
            "left_knee_joint": amount,
            "right_knee_joint": amount,
        }
    elif pattern == "hip_knee":
        deltas = {
            "left_hip_pitch_joint": -0.45 * amount,
            "right_hip_pitch_joint": -0.45 * amount,
            "left_knee_joint": amount,
            "right_knee_joint": amount,
        }
    elif pattern == "counter_ankle":
        deltas = {
            "left_hip_pitch_joint": -0.35 * amount,
            "right_hip_pitch_joint": -0.35 * amount,
            "left_knee_joint": amount,
            "right_knee_joint": amount,
            "left_ankle_pitch_joint": -0.45 * amount,
            "right_ankle_pitch_joint": -0.45 * amount,
        }
    elif pattern == "ankle_recenter":
        deltas = {
            "left_ankle_pitch_joint": -0.70 * amount,
            "right_ankle_pitch_joint": -0.70 * amount,
        }
    else:
        raise ValueError(pattern)
    for name, delta in deltas.items():
        adjusted[ctrl_index(model, name)] += delta
    return np.clip(adjusted, model.actuator_ctrlrange[:, 0], model.actuator_ctrlrange[:, 1])


def classify(native: dict[str, Any]) -> str:
    if native["pass_gate"]:
        return "PASS_COM_ZMP_NATIVE_GATE"
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
    gains: dict[str, float],
    signs: dict[str, float],
    feedback_source: str,
    residual_pattern: str,
    residual_scale: float,
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
    policy = EXP28.build_policy(env, EXP52.EXP46_PARAMS) if policy_weight > 0 else None
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
    previous_com_xy = data.subtree_com[0, :2].copy()
    previous_com_vel = np.zeros(2, dtype=np.float64)
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
    first_zmp_breach_at = None
    both_feet_contact_count = 0
    max_foot_slip = 0.0
    min_support_margin = float("inf")
    min_zmp_margin = float("inf")
    max_joint_violation = 0.0
    max_knee_delta = 0.0
    max_hip_delta = 0.0
    max_blend_observed = 0.0
    max_feedback_norm = 0.0
    samples = []

    for step in range(total_steps):
        t = step * ctrl_dt
        height = float(data.qpos[2])
        vertical_velocity = (height - previous_height) / ctrl_dt
        previous_height = height
        final_height = height
        min_height = min(min_height, height)

        support = EXP37.support_metrics(model, data, foot_geom_ids)
        center_xy = support_center(support)
        com_xy = data.subtree_com[0, :2].copy()
        com_vel = (com_xy - previous_com_xy) / ctrl_dt
        com_acc = (com_vel - previous_com_vel) / ctrl_dt
        previous_com_xy = com_xy.copy()
        previous_com_vel = com_vel.copy()
        com_z = max(float(data.subtree_com[0, 2]), 0.05)
        zmp_xy = com_xy - (com_z / G) * com_acc
        zmp_margin = support_margin_for_point(zmp_xy, support)
        feedback_point = zmp_xy if feedback_source == "zmp" else com_xy
        error_xy = center_xy - feedback_point
        max_feedback_norm = max(max_feedback_norm, float(np.linalg.norm(error_xy)))

        desired_fraction, return_phase = phase_fraction(t, descend_s, hold_s, return_s)
        desired_blend = max_blend * desired_fraction
        contacts = [
            float(data.sensordata[model.sensor_adr[sensor_id]]) > 0
            for sensor_id in foot_contact_sensor_ids
        ]
        both_feet = all(contacts)
        both_feet_contact_count += int(both_feet)
        foot_slip = float(np.max(np.linalg.norm(data.site_xpos[foot_site_ids, :2] - initial_foot_xy, axis=1)))
        health = health_factor(
            support_margin=support["support_margin"],
            zmp_margin=zmp_margin,
            both_feet=both_feet,
            foot_slip=foot_slip,
            vertical_velocity=vertical_velocity,
            support_floor=support_floor,
            slip_limit=slip_limit,
        )
        if return_phase > 0.0:
            blend_state = max(0.0, blend_state - max_blend * ctrl_dt / max(return_s, ctrl_dt))
        elif health >= 0.55:
            blend_state = min(desired_blend, blend_state + adapt_gain * health * ctrl_dt)
        else:
            blend_state = max(0.0, blend_state - adapt_gain * (0.55 - health) * ctrl_dt)
        max_blend_observed = max(max_blend_observed, blend_state)

        visible_drop_now = start_height - height
        if visible_drop_now >= 0.08 and first_visible_at is None:
            first_visible_at = round(t, 3)
        min_support_margin = min(min_support_margin, support["support_margin"])
        min_zmp_margin = min(min_zmp_margin, zmp_margin)
        if support["support_margin"] < support_floor and first_support_breach_at is None:
            first_support_breach_at = round(t, 3)
        if zmp_margin < support_floor and first_zmp_breach_at is None:
            first_zmp_breach_at = round(t, 3)
        max_foot_slip = max(max_foot_slip, foot_slip)
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
        target = apply_feedback(target, model=model, error_xy=error_xy, gains=gains, signs=signs)
        target = apply_residual_pattern(
            target,
            model=model,
            pattern=residual_pattern,
            scale=residual_scale,
            phase_depth=desired_fraction,
            support_health=health,
        )
        data.ctrl[:] = target
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
                "zmp_margin": zmp_margin,
                "com_xy": [float(v) for v in com_xy],
                "zmp_xy": [float(v) for v in zmp_xy],
                "support_center_xy": [float(v) for v in center_xy],
                "feedback_error_xy": [float(v) for v in error_xy],
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
        "feedback_source": feedback_source,
        "residual_pattern": residual_pattern,
        "residual_scale": residual_scale,
        "gains": gains,
        "signs": signs,
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
        "min_zmp_margin": min_zmp_margin,
        "first_support_breach_at": first_support_breach_at,
        "first_zmp_breach_at": first_zmp_breach_at,
        "max_joint_limit_violation": max_joint_violation,
        "max_knee_delta_rad": max_knee_delta,
        "max_hip_pitch_delta_rad": max_hip_delta,
        "max_blend_observed": max_blend_observed,
        "max_feedback_norm": max_feedback_norm,
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
        "# G1 CoM/ZMP Feedback Probe Summary",
        "",
        "| Attempt | Verdict | Source | Drop | Knee | Hip | Contact | Slip | CoM min | ZMP min | Final h | Fell |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for run in result["runs"]:
        fell = "never" if run["fell_at"] is None else f"{run['fell_at']:.2f}s"
        lines.append(
            f"| {run['attempt']} | {run['verdict']} | {run['feedback_source']}+{run['residual_pattern']} | "
            f"{run['visible_drop']:.4f}m | {run['max_knee_delta_rad']:.3f} | "
            f"{run['max_hip_pitch_delta_rad']:.3f} | {run['foot_contact_ratio']:.2f} | "
            f"{run['foot_slip_distance']:.3f}m | {run['min_support_margin']:.4f}m | "
            f"{run['min_zmp_margin']:.4f}m | {run['final_height']:.4f}m | {fell} |"
        )
    lines.extend([
        "",
        f"Best no-fall run: {result['best_no_fall']}",
        f"Best depth run: {result['best_depth']}",
        "",
        "M19 closes only when visible depth, knee/hip pose, no-fall, contact, stance, return, and browser replay gates pass together.",
    ])
    (out_dir / "com-zmp-feedback-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=6.0)
    parser.add_argument("--support-floor", type=float, default=-0.005)
    parser.add_argument("--slip-limit", type=float, default=0.08)
    args = parser.parse_args()

    out_dir = VERIFY / "teacher-residual"
    out_dir.mkdir(parents=True, exist_ok=True)
    base_gains = {
        "pitch": 2.0,
        "ankle_pitch": -1.4,
        "roll": 1.6,
        "ankle_roll": -1.0,
        "clip_pitch": 0.16,
        "clip_roll": 0.08,
    }
    signs_a = {"pitch": 1.0, "ankle_pitch": 1.0, "roll": 1.0, "ankle_roll": 1.0}
    variants = [
        {"attempt": "teacher-best", "source": "com", "signs": signs_a, "max_blend": 0.50, "adapt_gain": 0.14, "descend_s": 3.0, "pattern": "none", "scale": 0.0},
        {"attempt": "teacher-knee-r0p04", "source": "com", "signs": signs_a, "max_blend": 0.50, "adapt_gain": 0.14, "descend_s": 3.0, "pattern": "knee_only", "scale": 0.04},
        {"attempt": "teacher-hip-knee-r0p06", "source": "com", "signs": signs_a, "max_blend": 0.50, "adapt_gain": 0.14, "descend_s": 3.0, "pattern": "hip_knee", "scale": 0.06},
        {"attempt": "teacher-counter-ankle-r0p06", "source": "com", "signs": signs_a, "max_blend": 0.50, "adapt_gain": 0.14, "descend_s": 3.0, "pattern": "counter_ankle", "scale": 0.06},
        {"attempt": "teacher-ankle-recenter-r0p05", "source": "com", "signs": signs_a, "max_blend": 0.50, "adapt_gain": 0.14, "descend_s": 3.0, "pattern": "ankle_recenter", "scale": 0.05},
    ]
    result = {
        "planning_gate": {
            "team_validation_mode": "manual-pass",
            "spec_delta": "M19 probes bounded residual patterns on top of the exp55 CoM-feedback teacher before launching a longer residual fine-tune.",
            "perspectives": {
                "product": "tests the next visible squat blocker identified in ROADMAP",
                "architecture": "wraps exp55 teacher and adds small support-health-gated joint residuals",
                "security": "no credentials or external side effects",
                "qa": "native sweep logs CoM/ZMP margins, stance, pose, contact, return, fall",
                "skeptic": "hand-designed residuals may expose whether residual capacity helps, but do not replace learned fine-tuning",
            },
            "dod": [
                "native JSON per CoM/ZMP feedback variant",
                "summary identifies whether bounded residuals deepen the exp55 teacher without breaking M19 gates",
            ],
        },
        "runs": [],
    }
    for variant in variants:
        run = native_eval(
            attempt=variant["attempt"],
            drop=0.08,
            max_blend=variant["max_blend"],
            policy_weight=1.0,
            adapt_gain=variant["adapt_gain"],
            descend_s=variant.get("descend_s", 2.6),
            hold_s=0.4,
            return_s=variant.get("return_s", 1.4),
            seconds=args.seconds,
            support_floor=args.support_floor,
            slip_limit=args.slip_limit,
            gains=base_gains,
            signs=variant["signs"],
            feedback_source=variant["source"],
            residual_pattern=variant["pattern"],
            residual_scale=variant["scale"],
            out_dir=out_dir / variant["attempt"],
        )
        result["runs"].append(run)
    no_fall = [run for run in result["runs"] if run["fell_at"] is None]
    best_no_fall = max(no_fall, key=lambda run: run["visible_drop"], default=None)
    best_depth = max(result["runs"], key=lambda run: run["visible_drop"])
    result["best_no_fall"] = None if best_no_fall is None else {
        "attempt": best_no_fall["attempt"],
        "visible_drop": best_no_fall["visible_drop"],
        "min_support_margin": best_no_fall["min_support_margin"],
        "min_zmp_margin": best_no_fall["min_zmp_margin"],
        "return_to_stand": best_no_fall["return_to_stand"],
    }
    result["best_depth"] = {
        "attempt": best_depth["attempt"],
        "visible_drop": best_depth["visible_drop"],
        "fell_at": best_depth["fell_at"],
        "min_support_margin": best_depth["min_support_margin"],
        "min_zmp_margin": best_depth["min_zmp_margin"],
    }
    result["verdict"] = "PASS_M19_NATIVE_ONLY" if any(run["pass_gate"] for run in result["runs"]) else "FAIL_M19_NATIVE_GATE"
    write_summary(result, out_dir)
    (out_dir / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(result["verdict"], json.dumps({"best_no_fall": result["best_no_fall"], "best_depth": result["best_depth"]}, indent=2), flush=True)


if __name__ == "__main__":
    main()
