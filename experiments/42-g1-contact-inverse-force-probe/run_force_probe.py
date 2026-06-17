"""Probe contact wrench and inverse-dynamics signals for G1 squat attempts."""

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
EXP41_PATH = ROOT / "experiments/41-g1-operational-space-soft-wbc/run_soft_wbc.py"


def load_exp41():
    spec = importlib.util.spec_from_file_location("exp41_soft_wbc", EXP41_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {EXP41_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EXP41 = load_exp41()
EXP36 = EXP41.EXP36
EXP37 = EXP41.EXP37
EXP28 = EXP41.EXP28


def contact_wrench_summary(model: mujoco.MjModel, data: mujoco.MjData) -> dict:
    foot_geom_ids = {
        "left": int(model.geom("left_foot").id),
        "right": int(model.geom("right_foot").id),
    }
    totals = {
        "left": {"normal": 0.0, "tangent": 0.0, "contacts": 0},
        "right": {"normal": 0.0, "tangent": 0.0, "contacts": 0},
        "other": {"normal": 0.0, "tangent": 0.0, "contacts": 0},
    }
    for idx in range(data.ncon):
        contact = data.contact[idx]
        pair = {int(contact.geom1), int(contact.geom2)}
        side = "other"
        if foot_geom_ids["left"] in pair:
            side = "left"
        elif foot_geom_ids["right"] in pair:
            side = "right"
        wrench = np.zeros(6, dtype=np.float64)
        mujoco.mj_contactForce(model, data, idx, wrench)
        normal = abs(float(wrench[0]))
        tangent = float(np.linalg.norm(wrench[1:3]))
        totals[side]["normal"] += normal
        totals[side]["tangent"] += tangent
        totals[side]["contacts"] += 1
    total_normal = totals["left"]["normal"] + totals["right"]["normal"]
    lr_imbalance = 0.0
    if total_normal > 1e-6:
        lr_imbalance = abs(totals["left"]["normal"] - totals["right"]["normal"]) / total_normal
    return {
        "left_normal": totals["left"]["normal"],
        "right_normal": totals["right"]["normal"],
        "total_foot_normal": total_normal,
        "left_tangent": totals["left"]["tangent"],
        "right_tangent": totals["right"]["tangent"],
        "left_contacts": totals["left"]["contacts"],
        "right_contacts": totals["right"]["contacts"],
        "other_contacts": totals["other"]["contacts"],
        "lr_normal_imbalance": lr_imbalance,
    }


def inverse_summary(model: mujoco.MjModel, data: mujoco.MjData) -> dict:
    old_qacc = data.qacc.copy()
    qvel_before = data.qvel.copy()
    # Use current acceleration estimate when available. This is a diagnostic,
    # not a controller command; mj_inverse writes qfrc_inverse.
    data.qacc[:] = old_qacc
    mujoco.mj_inverse(model, data)
    diff = data.qfrc_inverse - data.qfrc_actuator
    data.qvel[:] = qvel_before
    return {
        "qfrc_inverse_linf": float(np.max(np.abs(data.qfrc_inverse))),
        "qfrc_actuator_linf": float(np.max(np.abs(data.qfrc_actuator))),
        "qfrc_inverse_minus_actuator_linf": float(np.max(np.abs(diff))),
        "lower_inverse_linf": float(np.max(np.abs(data.qfrc_inverse[6:21]))),
        "lower_actuator_linf": float(np.max(np.abs(data.qfrc_actuator[6:21]))),
    }


def run_variant(
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
    min_support_margin = float("inf")
    max_downward_velocity = 0.0
    both_feet_contact_count = 0
    max_foot_slip = 0.0
    max_normal_force = 0.0
    max_lr_imbalance = 0.0
    max_inverse_torque = 0.0
    max_inverse_gap = 0.0
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
        vertical_velocity = (height - last_height) / ctrl_dt if step > 0 else 0.0
        max_downward_velocity = min(max_downward_velocity, vertical_velocity)
        support = EXP37.support_metrics(model, data, foot_geom_ids)
        min_support_margin = min(min_support_margin, support["support_margin"])
        contacts = [
            float(data.sensordata[model.sensor_adr[sensor_id]]) > 0
            for sensor_id in foot_contact_sensor_ids
        ]
        both_feet = all(contacts)
        both_feet_contact_count += int(both_feet)
        foot_slip = float(np.max(np.linalg.norm(data.site_xpos[foot_site_ids, :2] - initial_foot_xy, axis=1)))
        max_foot_slip = max(max_foot_slip, foot_slip)
        quat = data.qpos[3:7]
        mat = np.empty(9)
        mujoco.mju_quat2Mat(mat, quat)
        up_z = float(mat.reshape(3, 3)[2, 2])
        if (height < 0.45 or up_z < 0.30) and fell_at is None:
            fell_at = round(t, 3)

        desired_blend = EXP41.blend_profile(t, descend_s, hold_s, return_s, max_blend)
        support_factor = EXP41.soft_factor(support["support_margin"], support_lo, support_hi)
        velocity_factor = EXP41.soft_factor(vertical_velocity, velocity_lo, velocity_hi)
        contact_factor = 1.0 if both_feet else 0.15
        if mode == "fixed":
            blend_factor = 1.0
        elif mode == "support-velocity":
            blend_factor = min(support_factor, velocity_factor, contact_factor)
        else:
            raise ValueError(f"unknown mode {mode}")
        effective_blend = desired_blend * blend_factor
        policy_targets = default_pose + policy_weight * action_np * float(env._config.action_scale)
        data.ctrl[:] = (1.0 - effective_blend) * policy_targets + effective_blend * ik_target
        for _ in range(n_substeps):
            mujoco.mj_step(model, data)

        wrench = contact_wrench_summary(model, data)
        inv = inverse_summary(model, data)
        max_normal_force = max(max_normal_force, wrench["total_foot_normal"])
        max_lr_imbalance = max(max_lr_imbalance, wrench["lr_normal_imbalance"])
        max_inverse_torque = max(max_inverse_torque, inv["lower_inverse_linf"])
        max_inverse_gap = max(max_inverse_gap, inv["qfrc_inverse_minus_actuator_linf"])
        last_action = action_np
        last_height = height

        if step % max(1, int(0.2 / ctrl_dt)) == 0:
            samples.append({
                "t": round(t, 3),
                "base_height": height,
                "visible_drop": start_height - height,
                "vertical_velocity": vertical_velocity,
                "up_z": up_z,
                "both_feet_contact": both_feet,
                "foot_slip_distance": foot_slip,
                "support_margin": support["support_margin"],
                "desired_blend": desired_blend,
                "effective_blend": effective_blend,
                "contact_wrench": wrench,
                "inverse": inv,
            })

    visible_drop = start_height - min_height
    foot_contact_ratio = both_feet_contact_count / max(1, total_steps)
    return_to_stand = final_height >= 0.74
    pass_gate = (
        fell_at is None
        and visible_drop >= 0.08
        and return_to_stand
        and foot_contact_ratio >= 0.90
        and max_foot_slip <= 0.15
    )
    if pass_gate:
        verdict = "PASS_FORCE_INSTRUMENTED_VISIBLE_SQUAT"
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
        "ik": ik,
        "start_height": start_height,
        "min_height": min_height,
        "visible_drop": visible_drop,
        "fell_at": fell_at,
        "final_height": final_height,
        "return_to_stand": return_to_stand,
        "foot_contact_ratio": foot_contact_ratio,
        "foot_slip_distance": max_foot_slip,
        "min_support_margin": min_support_margin,
        "max_downward_velocity": max_downward_velocity,
        "max_total_foot_normal_force": max_normal_force,
        "max_lr_normal_imbalance": max_lr_imbalance,
        "max_lower_inverse_torque": max_inverse_torque,
        "max_inverse_minus_actuator": max_inverse_gap,
        "pass_gate": pass_gate,
        "verdict": verdict,
        "samples": samples,
    }
    (out_dir / "force-native-eval.json").write_text(json.dumps(native, indent=2), encoding="utf-8")
    return native


def write_summary(results: list[dict]) -> None:
    lines = [
        "# G1 Contact and Inverse Force Probe Summary",
        "",
        "| Attempt | Verdict | Drop | Fell at | Normal max | LR imbalance max | Inv torque max | Inv-act gap max |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for native in results:
        fell = "never" if native["fell_at"] is None else f"{native['fell_at']:.2f}s"
        lines.append(
            f"| {native['attempt']} | {native['verdict']} | {native['visible_drop']:.4f}m | "
            f"{fell} | {native['max_total_foot_normal_force']:.2f} | "
            f"{native['max_lr_normal_imbalance']:.2f} | {native['max_lower_inverse_torque']:.2f} | "
            f"{native['max_inverse_minus_actuator']:.2f} |"
        )
    lines.extend([
        "",
        "M19 closes only when visible depth, no-fall, contact, stance, return, and browser replay gates pass together.",
    ])
    (VERIFY / "force-probe-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=None)
    parser.add_argument("--seconds", type=float, default=6.0)
    parser.add_argument("--sweep", action="store_true")
    args = parser.parse_args()
    source = args.source or EXP28.default_source()
    variants = [
        ("fixed-0p25", "fixed", 0.08, 0.25, 1.0, 3.0, 0.2, 2.4, 0.00, 0.06, -0.35, -0.05),
        ("support-velocity-0p60", "support-velocity", 0.08, 0.60, 1.0, 3.0, 0.2, 2.4, 0.00, 0.06, -0.35, -0.05),
        ("support-velocity-0p80", "support-velocity", 0.08, 0.80, 1.0, 3.0, 0.2, 2.4, 0.00, 0.06, -0.35, -0.05),
    ] if args.sweep else [
        ("support-velocity-0p60", "support-velocity", 0.08, 0.60, 1.0, 3.0, 0.2, 2.4, 0.00, 0.06, -0.35, -0.05),
    ]
    VERIFY.mkdir(parents=True, exist_ok=True)
    results = []
    for variant in variants:
        name, mode, drop, max_blend, policy_weight, descend_s, hold_s, return_s, support_lo, support_hi, velocity_lo, velocity_hi = variant
        out_dir = VERIFY / "attempts" / name
        out_dir.mkdir(parents=True, exist_ok=True)
        native = run_variant(
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
