"""Soft operational-space WBC proxy for G1 visible squat."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import jax
import jax.numpy as jp
import mujoco
import numpy as np


EXP_DIR = Path(__file__).resolve().parent
ROOT = EXP_DIR.parents[1]
VERIFY = EXP_DIR / "verify"
EXP36_PATH = ROOT / "experiments/36-g1-wbc-ik-squat-prototype/run_ik_squat.py"
EXP37_PATH = ROOT / "experiments/37-g1-com-support-squat-guard/run_support_guard.py"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EXP36 = load_module("exp36_ik_squat", EXP36_PATH)
EXP37 = load_module("exp37_support_guard", EXP37_PATH)
EXP28 = EXP36.EXP28


def blend_profile(t: float, descend_s: float, hold_s: float, return_s: float, max_blend: float) -> float:
    return EXP36.blend_profile(t, descend_s, hold_s, return_s, max_blend)


def soft_factor(value: float, lo: float, hi: float) -> float:
    if hi <= lo:
        return 1.0
    return float(np.clip((value - lo) / (hi - lo), 0.0, 1.0))


def native_eval(
    *,
    attempt: str,
    mode: str,
    drop: float,
    max_blend: float,
    policy_weight: float,
    descend_s: float,
    hold_s: float,
    return_s: float,
    support_lo: float,
    support_hi: float,
    velocity_lo: float,
    velocity_hi: float,
    seconds: float,
    params_path: Path,
    out_dir: Path,
) -> dict:
    env = EXP28.ContactAwareSquat(
        stage_height=0.67,
        controller_blend=max_blend,
        freeze_phase=True,
        blend_schedule="squat",
        reference_scale=1.0,
        config_overrides={"impl": "jax"},
    )
    policy = EXP28.build_policy(env, params_path)
    model = env.mj_model
    data = mujoco.MjData(model)
    key = model.keyframe("knees_bent")
    data.qpos[:] = key.qpos
    default_pose = key.qpos[7:].astype(np.float32).copy()
    data.ctrl[:] = default_pose
    mujoco.mj_forward(model, data)

    foot_site_ids = np.asarray(env._feet_site_id)
    foot_geom_ids = np.asarray([model.geom("left_foot").id, model.geom("right_foot").id])
    ik = EXP36.solve_foot_fixed_target(model, key.qpos.copy(), foot_site_ids, drop)
    ik_target = default_pose.copy()
    ik_target[:15] = np.asarray(ik["lower_body_target"], dtype=np.float32)

    gyro_adr = EXP28.sensor_adr(model, "gyro_pelvis")
    linvel_adr = EXP28.sensor_adr(model, "local_linvel_pelvis")
    imu_site = model.site("imu_in_pelvis").id
    foot_contact_sensor_ids = list(env._feet_floor_found_sensor)
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
    last_height = start_height

    min_height = start_height
    final_height = start_height
    fell_at = None
    first_visible_at = None
    first_support_breach_at = None
    min_support_margin = float("inf")
    max_downward_velocity = 0.0
    both_feet_contact_count = 0
    max_foot_slip = 0.0
    max_joint_violation = 0.0
    max_desired_blend = 0.0
    max_effective_blend = 0.0
    min_blend_factor = 1.0
    samples = []

    for step in range(total_steps):
        t = step * ctrl_dt
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

        height = float(data.qpos[2])
        final_height = height
        min_height = min(min_height, height)
        visible_drop_now = start_height - height
        if visible_drop_now >= 0.08 and first_visible_at is None:
            first_visible_at = round(t, 3)
        vertical_velocity = (height - last_height) / ctrl_dt if step > 0 else 0.0
        max_downward_velocity = min(max_downward_velocity, vertical_velocity)
        support = EXP37.support_metrics(model, data, foot_geom_ids)
        min_support_margin = min(min_support_margin, support["support_margin"])
        if support["support_margin"] < 0.0 and first_support_breach_at is None:
            first_support_breach_at = round(t, 3)
        quat = data.qpos[3:7]
        mat = np.empty(9)
        mujoco.mju_quat2Mat(mat, quat)
        up_z = float(mat.reshape(3, 3)[2, 2])
        contacts = [
            float(data.sensordata[model.sensor_adr[sensor_id]]) > 0
            for sensor_id in foot_contact_sensor_ids
        ]
        both_feet = all(contacts)
        both_feet_contact_count += int(both_feet)
        foot_slip = float(np.max(np.linalg.norm(data.site_xpos[foot_site_ids, :2] - initial_foot_xy, axis=1)))
        max_foot_slip = max(max_foot_slip, foot_slip)
        max_joint_violation = max(max_joint_violation, EXP28.joint_limit_violation(model, data))
        if (height < 0.45 or up_z < 0.30) and fell_at is None:
            fell_at = round(t, 3)

        desired_blend = blend_profile(t, descend_s, hold_s, return_s, max_blend)
        support_factor = soft_factor(support["support_margin"], support_lo, support_hi)
        velocity_factor = soft_factor(vertical_velocity, velocity_lo, velocity_hi)
        contact_factor = 1.0 if both_feet else 0.15
        if mode == "fixed":
            blend_factor = 1.0
        elif mode == "support":
            blend_factor = min(support_factor, contact_factor)
        elif mode == "support-velocity":
            blend_factor = min(support_factor, velocity_factor, contact_factor)
        else:
            raise ValueError(f"unknown mode {mode}")
        effective_blend = desired_blend * blend_factor
        max_desired_blend = max(max_desired_blend, desired_blend)
        max_effective_blend = max(max_effective_blend, effective_blend)
        min_blend_factor = min(min_blend_factor, blend_factor)

        policy_targets = default_pose + policy_weight * action_np * float(env._config.action_scale)
        data.ctrl[:] = (1.0 - effective_blend) * policy_targets + effective_blend * ik_target
        for _ in range(n_substeps):
            mujoco.mj_step(model, data)
        last_action = action_np
        last_height = height

        if step % max(1, int(0.2 / ctrl_dt)) == 0:
            samples.append({
                "t": round(t, 3),
                "base_height": height,
                "visible_drop": visible_drop_now,
                "vertical_velocity": vertical_velocity,
                "up_z": up_z,
                "both_feet_contact": both_feet,
                "foot_slip_distance": foot_slip,
                "support_margin": support["support_margin"],
                "desired_blend": desired_blend,
                "effective_blend": effective_blend,
                "support_factor": support_factor,
                "velocity_factor": velocity_factor,
                "blend_factor": blend_factor,
            })

    foot_contact_ratio = both_feet_contact_count / max(1, total_steps)
    visible_drop = start_height - min_height
    return_to_stand = final_height >= 0.74
    pass_gate = (
        fell_at is None
        and visible_drop >= 0.08
        and return_to_stand
        and foot_contact_ratio >= 0.90
        and max_foot_slip <= 0.15
        and max_joint_violation <= 0.05
    )
    if pass_gate:
        verdict = "PASS_SOFT_WBC_VISIBLE_SQUAT"
    elif fell_at is not None:
        verdict = "FAIL_FALL"
    elif visible_drop < 0.08:
        verdict = "DEPTH_PENDING"
    elif not return_to_stand:
        verdict = "RETURN_PENDING"
    elif foot_contact_ratio < 0.90:
        verdict = "CONTACT_GATE_PENDING"
    elif max_foot_slip > 0.15:
        verdict = "STANCE_SLIP_PENDING"
    else:
        verdict = "GATE_PENDING"

    native = {
        "attempt": attempt,
        "mode": mode,
        "drop": drop,
        "max_blend": max_blend,
        "policy_weight": policy_weight,
        "support_lo": support_lo,
        "support_hi": support_hi,
        "velocity_lo": velocity_lo,
        "velocity_hi": velocity_hi,
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
        "max_downward_velocity": max_downward_velocity,
        "max_joint_limit_violation": max_joint_violation,
        "max_desired_blend": max_desired_blend,
        "max_effective_blend": max_effective_blend,
        "min_blend_factor": min_blend_factor,
        "pass_gate": pass_gate,
        "verdict": verdict,
        "samples": samples,
    }
    (out_dir / "soft-wbc-native-eval.json").write_text(json.dumps(native, indent=2), encoding="utf-8")
    return native


def write_summary(results: list[dict]) -> None:
    lines = [
        "# G1 Soft Operational-Space WBC Summary",
        "",
        "| Attempt | Verdict | Drop | Fell at | Support min | Contact | Slip | Blend max |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for native in results:
        fell = "never" if native["fell_at"] is None else f"{native['fell_at']:.2f}s"
        lines.append(
            f"| {native['attempt']} | {native['verdict']} | {native['visible_drop']:.4f}m | "
            f"{fell} | {native['min_support_margin']:.4f}m | {native['foot_contact_ratio']:.2f} | "
            f"{native['foot_slip_distance']:.3f}m | {native['max_effective_blend']:.2f} |"
        )
    lines.extend([
        "",
        "M19 closes only when visible depth, no-fall, contact, stance, return, and browser replay gates pass together.",
    ])
    (VERIFY / "soft-wbc-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=None)
    parser.add_argument("--seconds", type=float, default=6.0)
    parser.add_argument("--sweep", action="store_true")
    args = parser.parse_args()
    source = args.source or EXP28.default_source()
    variants = [
        ("fixed-0p25", "fixed", 0.08, 0.25, 1.0, 3.0, 0.2, 2.4, 0.00, 0.05, -0.45, -0.10),
        ("fixed-0p35", "fixed", 0.08, 0.35, 1.0, 3.0, 0.2, 2.4, 0.00, 0.05, -0.45, -0.10),
        ("support-0p45", "support", 0.08, 0.45, 1.0, 3.0, 0.2, 2.4, 0.00, 0.06, -0.45, -0.10),
        ("support-velocity-0p45", "support-velocity", 0.08, 0.45, 1.0, 3.0, 0.2, 2.4, 0.00, 0.06, -0.35, -0.05),
        ("support-velocity-0p60", "support-velocity", 0.08, 0.60, 1.0, 3.0, 0.2, 2.4, 0.00, 0.06, -0.35, -0.05),
        ("support-velocity-0p80", "support-velocity", 0.08, 0.80, 1.0, 3.0, 0.2, 2.4, 0.00, 0.06, -0.35, -0.05),
        ("support-velocity-1p00", "support-velocity", 0.08, 1.00, 1.0, 3.0, 0.2, 2.4, 0.00, 0.06, -0.35, -0.05),
    ] if args.sweep else [
        ("support-velocity-0p45", "support-velocity", 0.08, 0.45, 1.0, 3.0, 0.2, 2.4, 0.00, 0.06, -0.35, -0.05),
    ]
    VERIFY.mkdir(parents=True, exist_ok=True)
    results = []
    for variant in variants:
        name, mode, drop, max_blend, policy_weight, descend_s, hold_s, return_s, support_lo, support_hi, velocity_lo, velocity_hi = variant
        out_dir = VERIFY / "attempts" / name
        out_dir.mkdir(parents=True, exist_ok=True)
        native = native_eval(
            attempt=name,
            mode=mode,
            drop=drop,
            max_blend=max_blend,
            policy_weight=policy_weight,
            descend_s=descend_s,
            hold_s=hold_s,
            return_s=return_s,
            support_lo=support_lo,
            support_hi=support_hi,
            velocity_lo=velocity_lo,
            velocity_hi=velocity_hi,
            seconds=args.seconds,
            params_path=source,
            out_dir=out_dir,
        )
        (out_dir / "result.json").write_text(json.dumps({"native": native}, indent=2), encoding="utf-8")
        results.append(native)
    write_summary(results)
    print(json.dumps({"attempts": results}, indent=2), flush=True)


if __name__ == "__main__":
    main()
