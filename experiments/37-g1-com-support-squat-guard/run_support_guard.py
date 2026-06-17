"""Probe CoM/support-polygon guard signals for G1 visible squat.

This keeps the exp36 foot-fixed IK target and adds whole-body CoM projection
metrics against the current foot support rectangle.
"""

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


def load_exp36():
    spec = importlib.util.spec_from_file_location("exp36_ik_squat", EXP36_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {EXP36_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EXP36 = load_exp36()
EXP28 = EXP36.EXP28


def support_metrics(model: mujoco.MjModel, data: mujoco.MjData, foot_geom_ids: np.ndarray) -> dict:
    corners = []
    for geom_id in foot_geom_ids:
        half_x, half_y = model.geom_size[geom_id, 0], model.geom_size[geom_id, 1]
        geom_pos = data.geom_xpos[geom_id]
        geom_mat = data.geom_xmat[geom_id].reshape(3, 3)
        for sx in (-half_x, half_x):
            for sy in (-half_y, half_y):
                local = np.array([sx, sy, 0.0])
                corners.append((geom_pos + geom_mat @ local)[:2])
    support = np.asarray(corners)
    min_xy = support.min(axis=0)
    max_xy = support.max(axis=0)
    com_xy = data.subtree_com[0, :2].copy()
    margins = np.array([
        com_xy[0] - min_xy[0],
        max_xy[0] - com_xy[0],
        com_xy[1] - min_xy[1],
        max_xy[1] - com_xy[1],
    ])
    return {
        "com_xy": [float(v) for v in com_xy],
        "support_min_xy": [float(v) for v in min_xy],
        "support_max_xy": [float(v) for v in max_xy],
        "support_margin": float(np.min(margins)),
        "inside_support": bool(np.min(margins) >= 0.0),
    }


def native_support_eval(
    *,
    attempt: str,
    drop: float,
    max_blend: float,
    policy_weight: float,
    descend_s: float,
    hold_s: float,
    return_s: float,
    guard: bool,
    margin_min: float,
    vertical_velocity_min: float,
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
    first_support_breach_at = None
    first_fast_drop_at = None
    first_visible_at = None
    first_guard_at = None
    guard_trip_count = 0
    in_return = False
    return_start_t = None
    min_support_margin = float("inf")
    max_downward_velocity = 0.0
    max_foot_slip = 0.0
    both_feet_contact_count = 0
    max_joint_violation = 0.0
    torso_up_min_observed = float("inf")
    max_observed_blend = 0.0
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
        support = support_metrics(model, data, foot_geom_ids)
        min_support_margin = min(min_support_margin, support["support_margin"])
        visible_drop_now = start_height - height
        if visible_drop_now >= 0.08 and first_visible_at is None:
            first_visible_at = round(t, 3)
        if support["support_margin"] < 0.0 and first_support_breach_at is None:
            first_support_breach_at = round(t, 3)
        if vertical_velocity < vertical_velocity_min and first_fast_drop_at is None:
            first_fast_drop_at = round(t, 3)

        quat = data.qpos[3:7]
        mat = np.empty(9)
        mujoco.mju_quat2Mat(mat, quat)
        up_z = float(mat.reshape(3, 3)[2, 2])
        torso_up_min_observed = min(torso_up_min_observed, up_z)
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

        desired_blend = EXP36.blend_profile(t, descend_s, hold_s, return_s, max_blend)
        guard_reason = None
        if guard and not in_return:
            if support["support_margin"] < margin_min:
                guard_reason = "support_margin"
            elif vertical_velocity < vertical_velocity_min:
                guard_reason = "fast_drop"
            elif not both_feet:
                guard_reason = "contact_loss"
            if guard_reason is not None:
                in_return = True
                return_start_t = t
                guard_trip_count += 1
                first_guard_at = first_guard_at if first_guard_at is not None else round(t, 3)
        if in_return:
            elapsed = t - float(return_start_t)
            current_blend = max_blend * max(0.0, 1.0 - elapsed / max(return_s, ctrl_dt))
            current_blend = min(current_blend, desired_blend)
        else:
            current_blend = desired_blend
        max_observed_blend = max(max_observed_blend, current_blend)

        policy_targets = default_pose + policy_weight * action_np * float(env._config.action_scale)
        data.ctrl[:] = (1.0 - current_blend) * policy_targets + current_blend * ik_target
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
                "inside_support": support["inside_support"],
                "controller_blend": current_blend,
                "guard_reason": guard_reason,
            })

    foot_contact_ratio = both_feet_contact_count / max(1, total_steps)
    visible_drop = start_height - min_height
    return_to_stand = final_height >= 0.74
    stance_ok = max_foot_slip <= 0.15
    pass_gate = (
        fell_at is None
        and visible_drop >= 0.08
        and return_to_stand
        and foot_contact_ratio >= 0.90
        and stance_ok
        and max_joint_violation <= 0.05
    )
    if pass_gate:
        verdict = "PASS_SUPPORT_GUARDED_VISIBLE_SQUAT"
    elif fell_at is not None:
        verdict = "FAIL_FALL"
    elif visible_drop < 0.08:
        verdict = "DEPTH_PENDING"
    elif not return_to_stand:
        verdict = "RETURN_PENDING"
    elif foot_contact_ratio < 0.90:
        verdict = "CONTACT_GATE_PENDING"
    elif not stance_ok:
        verdict = "STANCE_SLIP_PENDING"
    else:
        verdict = "GATE_PENDING"

    native = {
        "attempt": attempt,
        "drop": drop,
        "max_blend": max_blend,
        "policy_weight": policy_weight,
        "guard": guard,
        "margin_min": margin_min,
        "vertical_velocity_min": vertical_velocity_min,
        "descend_s": descend_s,
        "hold_s": hold_s,
        "return_s": return_s,
        "seconds": seconds,
        "params_path": str(params_path),
        "ik": ik,
        "start_height": start_height,
        "min_height": min_height,
        "visible_drop": visible_drop,
        "first_visible_at": first_visible_at,
        "fell_at": fell_at,
        "upright_s": seconds if fell_at is None else fell_at,
        "final_height": final_height,
        "return_to_stand": return_to_stand,
        "torso_up_min_observed": torso_up_min_observed,
        "foot_contact_ratio": foot_contact_ratio,
        "foot_slip_distance": max_foot_slip,
        "stance_ok": stance_ok,
        "max_joint_limit_violation": max_joint_violation,
        "min_support_margin": min_support_margin,
        "first_support_breach_at": first_support_breach_at,
        "first_fast_drop_at": first_fast_drop_at,
        "max_downward_velocity": max_downward_velocity,
        "first_guard_at": first_guard_at,
        "guard_trip_count": guard_trip_count,
        "max_observed_blend": max_observed_blend,
        "pass_gate": pass_gate,
        "verdict": verdict,
        "samples": samples,
    }
    (out_dir / "support-native-eval.json").write_text(json.dumps(native, indent=2), encoding="utf-8")
    return native


def write_summary(results: list[dict]) -> None:
    lines = [
        "# G1 CoM Support Guard Summary",
        "",
        "| Attempt | Verdict | Drop | Fell at | Support min | Breach at | Fast drop at | Guard at | Slip |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for native in results:
        fell = "never" if native["fell_at"] is None else f"{native['fell_at']:.2f}s"
        breach = "never" if native["first_support_breach_at"] is None else f"{native['first_support_breach_at']:.2f}s"
        fast = "never" if native["first_fast_drop_at"] is None else f"{native['first_fast_drop_at']:.2f}s"
        guard = "never" if native["first_guard_at"] is None else f"{native['first_guard_at']:.2f}s"
        lines.append(
            f"| {native['attempt']} | {native['verdict']} | {native['visible_drop']:.4f}m | {fell} | "
            f"{native['min_support_margin']:.4f}m | {breach} | {fast} | {guard} | "
            f"{native['foot_slip_distance']:.3f}m |"
        )
    lines.extend([
        "",
        "M19 is closed only if visible depth, no-fall, stance/contact, return, and browser replay gates pass together.",
    ])
    (VERIFY / "support-guard-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=None)
    parser.add_argument("--seconds", type=float, default=6.0)
    parser.add_argument("--sweep", action="store_true")
    args = parser.parse_args()

    source = args.source or EXP28.default_source()
    variants = [
        ("baseline-0p25", 0.08, 0.25, 1.0, 3.0, 0.2, 2.4, False, -0.01, -0.40),
        ("baseline-0p35", 0.08, 0.35, 1.0, 3.0, 0.2, 2.4, False, -0.01, -0.40),
        ("support-guard-0p35", 0.08, 0.35, 1.0, 3.0, 0.2, 2.4, True, 0.015, -0.35),
        ("support-guard-0p45", 0.08, 0.45, 1.0, 3.0, 0.2, 2.4, True, 0.015, -0.35),
        ("velocity-guard-0p45", 0.08, 0.45, 1.0, 3.0, 0.2, 2.4, True, -0.01, -0.25),
    ] if args.sweep else [
        ("support-guard-0p35", 0.08, 0.35, 1.0, 3.0, 0.2, 2.4, True, 0.015, -0.35),
    ]

    VERIFY.mkdir(parents=True, exist_ok=True)
    results = []
    for variant in variants:
        name, drop, max_blend, policy_weight, descend_s, hold_s, return_s, guard, margin_min, velocity_min = variant
        attempt_dir = VERIFY / "attempts" / name
        attempt_dir.mkdir(parents=True, exist_ok=True)
        native = native_support_eval(
            attempt=name,
            drop=drop,
            max_blend=max_blend,
            policy_weight=policy_weight,
            descend_s=descend_s,
            hold_s=hold_s,
            return_s=return_s,
            guard=guard,
            margin_min=margin_min,
            vertical_velocity_min=velocity_min,
            seconds=args.seconds,
            params_path=source,
            out_dir=attempt_dir,
        )
        (attempt_dir / "result.json").write_text(json.dumps({"native": native}, indent=2), encoding="utf-8")
        results.append(native)

    write_summary(results)
    print(json.dumps({"attempts": results}, indent=2), flush=True)


if __name__ == "__main__":
    main()
