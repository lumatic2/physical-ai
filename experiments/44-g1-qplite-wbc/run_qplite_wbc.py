"""One-step QP-lite WBC selector for G1 visible squat attempts.

This is not a torque-level QP. It is a small predictive controller that chooses
the IK blend minimizing a WBC-like cost over pelvis height, support margin,
contact force balance, foot slip, vertical momentum, and inverse-dynamics load.
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
EXP42_PATH = ROOT / "experiments/42-g1-contact-inverse-force-probe/run_force_probe.py"


def load_exp42():
    spec = importlib.util.spec_from_file_location("exp42_force_probe", EXP42_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {EXP42_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EXP42 = load_exp42()
EXP41 = EXP42.EXP41
EXP36 = EXP42.EXP36
EXP37 = EXP42.EXP37
EXP28 = EXP42.EXP28


def clone_data(model: mujoco.MjModel, data: mujoco.MjData) -> mujoco.MjData:
    cand = mujoco.MjData(model)
    cand.time = data.time
    cand.qpos[:] = data.qpos
    cand.qvel[:] = data.qvel
    cand.act[:] = data.act
    cand.ctrl[:] = data.ctrl
    mujoco.mj_forward(model, cand)
    return cand


def safe_inverse_summary(model: mujoco.MjModel, data: mujoco.MjData) -> dict:
    probe = clone_data(model, data)
    return EXP42.inverse_summary(model, probe)


def candidate_cost(
    *,
    model: mujoco.MjModel,
    cand: mujoco.MjData,
    start_height: float,
    desired_drop: float,
    previous_blend: float,
    blend: float,
    initial_foot_xy: np.ndarray,
    foot_site_ids: np.ndarray,
    foot_geom_ids: np.ndarray,
    foot_contact_sensor_ids: list[int],
    ctrl_dt: float,
    current_height: float,
    weights: dict[str, float],
) -> tuple[float, dict]:
    height = float(cand.qpos[2])
    vertical_velocity = (height - current_height) / ctrl_dt
    target_height = start_height - desired_drop
    support = EXP37.support_metrics(model, cand, foot_geom_ids)
    wrench = EXP42.contact_wrench_summary(model, cand)
    inv = safe_inverse_summary(model, cand)
    contacts = [
        float(cand.sensordata[model.sensor_adr[sensor_id]]) > 0
        for sensor_id in foot_contact_sensor_ids
    ]
    both_feet = all(contacts)
    foot_slip = float(np.max(np.linalg.norm(cand.site_xpos[foot_site_ids, :2] - initial_foot_xy, axis=1)))
    quat = cand.qpos[3:7]
    mat = np.empty(9)
    mujoco.mju_quat2Mat(mat, quat)
    up_z = float(mat.reshape(3, 3)[2, 2])
    height_err = height - target_height
    support_breach = max(0.0, -support["support_margin"])
    downward = max(0.0, -vertical_velocity - 0.10)
    contact_loss = 0.0 if both_feet else 1.0
    slip_excess = max(0.0, foot_slip - 0.04)
    normal_excess = max(0.0, wrench["total_foot_normal"] - 850.0) / 850.0
    torque_excess = max(0.0, inv["lower_inverse_linf"] - 1800.0) / 1800.0
    gap_excess = max(0.0, inv["qfrc_inverse_minus_actuator_linf"] - 8500.0) / 8500.0
    upright_loss = max(0.0, 0.80 - up_z)
    blend_jump = abs(blend - previous_blend)
    cost_terms = {
        "height": weights["height"] * height_err * height_err,
        "support": weights["support"] * support_breach * support_breach,
        "downward_velocity": weights["downward_velocity"] * downward * downward,
        "contact_loss": weights["contact_loss"] * contact_loss,
        "slip": weights["slip"] * slip_excess * slip_excess,
        "force_imbalance": weights["force_imbalance"] * wrench["lr_normal_imbalance"] ** 2,
        "normal_force": weights["normal_force"] * normal_excess * normal_excess,
        "inverse_torque": weights["inverse_torque"] * torque_excess * torque_excess,
        "inverse_gap": weights["inverse_gap"] * gap_excess * gap_excess,
        "upright": weights["upright"] * upright_loss * upright_loss,
        "blend_jump": weights["blend_jump"] * blend_jump * blend_jump,
    }
    cost = float(sum(cost_terms.values()))
    metrics = {
        "height": height,
        "target_height": target_height,
        "desired_drop": desired_drop,
        "vertical_velocity": vertical_velocity,
        "support_margin": support["support_margin"],
        "both_feet_contact": both_feet,
        "foot_slip_distance": foot_slip,
        "up_z": up_z,
        "contact_wrench": wrench,
        "inverse": inv,
        "cost_terms": cost_terms,
        "cost": cost,
    }
    return cost, metrics


def choose_blend(
    *,
    model: mujoco.MjModel,
    data: mujoco.MjData,
    policy_targets: np.ndarray,
    ik_target: np.ndarray,
    desired_blend: float,
    desired_drop: float,
    previous_blend: float,
    start_height: float,
    initial_foot_xy: np.ndarray,
    foot_site_ids: np.ndarray,
    foot_geom_ids: np.ndarray,
    foot_contact_sensor_ids: list[int],
    ctrl_dt: float,
    n_substeps: int,
    weights: dict[str, float],
    grid_size: int,
) -> tuple[float, dict]:
    if desired_blend <= 1e-6:
        candidates = np.array([0.0], dtype=np.float64)
    else:
        lo = max(0.0, previous_blend - max(0.10, desired_blend * 0.40))
        hi = min(desired_blend, previous_blend + max(0.14, desired_blend * 0.55))
        base = np.linspace(0.0, desired_blend, grid_size)
        local = np.linspace(lo, hi, max(3, grid_size // 2))
        candidates = np.unique(np.round(np.concatenate([base, local, [previous_blend, desired_blend]]), 5))
    current_height = float(data.qpos[2])
    best_blend = 0.0
    best_cost = float("inf")
    best_metrics: dict | None = None
    evaluated = []
    for blend in candidates:
        cand = clone_data(model, data)
        cand.ctrl[:] = (1.0 - blend) * policy_targets + blend * ik_target
        for _ in range(n_substeps):
            mujoco.mj_step(model, cand)
        cost, metrics = candidate_cost(
            model=model,
            cand=cand,
            start_height=start_height,
            desired_drop=desired_drop,
            previous_blend=previous_blend,
            blend=float(blend),
            initial_foot_xy=initial_foot_xy,
            foot_site_ids=foot_site_ids,
            foot_geom_ids=foot_geom_ids,
            foot_contact_sensor_ids=foot_contact_sensor_ids,
            ctrl_dt=ctrl_dt,
            current_height=current_height,
            weights=weights,
        )
        evaluated.append({
            "blend": float(blend),
            "cost": cost,
            "height": metrics["height"],
            "support_margin": metrics["support_margin"],
            "vertical_velocity": metrics["vertical_velocity"],
            "lr_normal_imbalance": metrics["contact_wrench"]["lr_normal_imbalance"],
            "inverse_torque": metrics["inverse"]["lower_inverse_linf"],
        })
        if cost < best_cost:
            best_cost = cost
            best_blend = float(blend)
            best_metrics = metrics
    assert best_metrics is not None
    best_metrics["evaluated_candidates"] = evaluated
    return best_blend, best_metrics


def native_eval(
    *,
    attempt: str,
    drop: float,
    max_blend: float,
    policy_weight: float,
    descend_s: float,
    hold_s: float,
    return_s: float,
    seconds: float,
    params_path: Path,
    out_dir: Path,
    grid_size: int,
    weights: dict[str, float],
    trajectory_out: Path | None,
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

    min_height = start_height
    final_height = start_height
    fell_at = None
    first_visible_at = None
    min_support_margin = float("inf")
    both_feet_contact_count = 0
    max_foot_slip = 0.0
    max_joint_violation = 0.0
    max_normal_force = 0.0
    max_lr_imbalance = 0.0
    max_inverse_torque = 0.0
    max_inverse_gap = 0.0
    max_downward_velocity = 0.0
    previous_blend = 0.0
    max_selected_blend = 0.0
    samples = []
    qpos_frames = []

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
        policy_targets = default_pose + policy_weight * action_np * float(env._config.action_scale)

        desired_blend = EXP41.blend_profile(t, descend_s, hold_s, return_s, max_blend)
        desired_drop = drop * (desired_blend / max(max_blend, 1e-6))
        selected_blend, predicted = choose_blend(
            model=model,
            data=data,
            policy_targets=policy_targets,
            ik_target=ik_target,
            desired_blend=desired_blend,
            desired_drop=desired_drop,
            previous_blend=previous_blend,
            start_height=start_height,
            initial_foot_xy=initial_foot_xy,
            foot_site_ids=foot_site_ids,
            foot_geom_ids=foot_geom_ids,
            foot_contact_sensor_ids=foot_contact_sensor_ids,
            ctrl_dt=ctrl_dt,
            n_substeps=n_substeps,
            weights=weights,
            grid_size=grid_size,
        )
        data.ctrl[:] = (1.0 - selected_blend) * policy_targets + selected_blend * ik_target
        for _ in range(n_substeps):
            mujoco.mj_step(model, data)
        last_action = action_np
        previous_blend = selected_blend
        max_selected_blend = max(max_selected_blend, selected_blend)
        if trajectory_out is not None:
            qpos_frames.append([float(v) for v in data.qpos[: model.nq]])

        height = float(data.qpos[2])
        final_height = height
        min_height = min(min_height, height)
        visible_drop_now = start_height - height
        if visible_drop_now >= 0.08 and first_visible_at is None:
            first_visible_at = round(t, 3)
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
        max_joint_violation = max(max_joint_violation, EXP28.joint_limit_violation(model, data))
        wrench = EXP42.contact_wrench_summary(model, data)
        inv = safe_inverse_summary(model, data)
        max_normal_force = max(max_normal_force, wrench["total_foot_normal"])
        max_lr_imbalance = max(max_lr_imbalance, wrench["lr_normal_imbalance"])
        max_inverse_torque = max(max_inverse_torque, inv["lower_inverse_linf"])
        max_inverse_gap = max(max_inverse_gap, inv["qfrc_inverse_minus_actuator_linf"])
        max_downward_velocity = min(max_downward_velocity, predicted["vertical_velocity"])
        quat = data.qpos[3:7]
        mat = np.empty(9)
        mujoco.mju_quat2Mat(mat, quat)
        up_z = float(mat.reshape(3, 3)[2, 2])
        if (height < 0.45 or up_z < 0.30) and fell_at is None:
            fell_at = round(t, 3)

        if step % max(1, int(0.2 / ctrl_dt)) == 0:
            candidate_rows = predicted["evaluated_candidates"]
            samples.append({
                "t": round(t, 3),
                "base_height": height,
                "visible_drop": visible_drop_now,
                "desired_blend": desired_blend,
                "selected_blend": selected_blend,
                "desired_drop": desired_drop,
                "support_margin": support["support_margin"],
                "both_feet_contact": both_feet,
                "foot_slip_distance": foot_slip,
                "up_z": up_z,
                "contact_wrench": wrench,
                "inverse": inv,
                "predicted": {k: v for k, v in predicted.items() if k != "evaluated_candidates"},
                "best_candidate": min(candidate_rows, key=lambda x: x["cost"]) if candidate_rows else None,
                "candidate_count": len(candidate_rows),
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
        verdict = "PASS_QPLITE_VISIBLE_SQUAT_NATIVE"
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
        "drop": drop,
        "max_blend": max_blend,
        "policy_weight": policy_weight,
        "grid_size": grid_size,
        "weights": weights,
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
        "max_joint_limit_violation": max_joint_violation,
        "max_total_foot_normal_force": max_normal_force,
        "max_lr_normal_imbalance": max_lr_imbalance,
        "max_lower_inverse_torque": max_inverse_torque,
        "max_inverse_minus_actuator": max_inverse_gap,
        "max_downward_velocity": max_downward_velocity,
        "max_selected_blend": max_selected_blend,
        "pass_gate": pass_gate,
        "verdict": verdict,
        "samples": samples,
    }
    if trajectory_out is not None:
        trajectory_out.parent.mkdir(parents=True, exist_ok=True)
        trajectory = {
            "fps": int(round(1.0 / ctrl_dt)),
            "nq": int(model.nq),
            "scene": "g1/scene_g1_policy.xml",
            "note": "G1 QP-lite WBC squat replay from exp44.",
            "source_attempt": attempt,
            "qpos": qpos_frames,
        }
        trajectory_out.write_text(json.dumps(trajectory), encoding="utf-8")
        native["trajectory_out"] = str(trajectory_out)
    (out_dir / "qplite-native-eval.json").write_text(json.dumps(native, indent=2), encoding="utf-8")
    return native


def write_summary(results: list[dict]) -> None:
    lines = [
        "# G1 QP-lite WBC Summary",
        "",
        "| Attempt | Verdict | Drop | Fell at | Final height | Support min | Contact | Slip | Blend max | Normal max | LR imbalance | Inv torque |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for native in results:
        fell = "never" if native["fell_at"] is None else f"{native['fell_at']:.2f}s"
        lines.append(
            f"| {native['attempt']} | {native['verdict']} | {native['visible_drop']:.4f}m | "
            f"{fell} | {native['final_height']:.4f}m | {native['min_support_margin']:.4f}m | "
            f"{native['foot_contact_ratio']:.2f} | {native['foot_slip_distance']:.3f}m | "
            f"{native['max_selected_blend']:.2f} | {native['max_total_foot_normal_force']:.2f} | "
            f"{native['max_lr_normal_imbalance']:.2f} | {native['max_lower_inverse_torque']:.2f} |"
        )
    lines.extend([
        "",
        "M19 closes only when visible depth, no-fall, contact, stance, return, and browser replay gates pass together.",
    ])
    (VERIFY / "qplite-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def weights_for(mode: str) -> dict[str, float]:
    if mode == "force_strict":
        return {
            "height": 55.0,
            "support": 700.0,
            "downward_velocity": 65.0,
            "contact_loss": 80.0,
            "slip": 180.0,
            "force_imbalance": 28.0,
            "normal_force": 18.0,
            "inverse_torque": 16.0,
            "inverse_gap": 10.0,
            "upright": 120.0,
            "blend_jump": 2.5,
        }
    if mode == "depth_biased":
        w = weights_for("force_strict")
        w["height"] = 130.0
        w["support"] = 500.0
        w["force_imbalance"] = 18.0
        w["blend_jump"] = 1.2
        return w
    if mode == "depth_aggressive":
        return {
            "height": 850.0,
            "support": 260.0,
            "downward_velocity": 35.0,
            "contact_loss": 95.0,
            "slip": 160.0,
            "force_imbalance": 2.5,
            "normal_force": 5.0,
            "inverse_torque": 3.0,
            "inverse_gap": 2.0,
            "upright": 120.0,
            "blend_jump": 0.35,
        }
    raise ValueError(f"unknown weight mode {mode}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=None)
    parser.add_argument("--seconds", type=float, default=6.0)
    parser.add_argument("--sweep", action="store_true")
    parser.add_argument("--trajectory-out", type=Path, default=None)
    args = parser.parse_args()
    source = args.source or EXP28.default_source()
    variants = [
        ("qplite-0p08-force-strict", 0.08, 0.90, 1.0, 3.0, 0.2, 2.4, 9, "force_strict"),
        ("qplite-0p08-depth-biased", 0.08, 0.90, 1.0, 3.0, 0.2, 2.4, 9, "depth_biased"),
        ("qplite-0p12-force-strict", 0.12, 0.90, 1.0, 3.2, 0.2, 2.5, 11, "force_strict"),
        ("qplite-0p12-depth-biased", 0.12, 0.90, 1.0, 3.2, 0.2, 2.5, 11, "depth_biased"),
        ("qplite-0p12-depth-aggressive", 0.12, 1.00, 1.0, 3.4, 0.2, 2.7, 13, "depth_aggressive"),
        ("qplite-0p16-depth-aggressive", 0.16, 1.00, 1.0, 3.6, 0.2, 2.8, 13, "depth_aggressive"),
    ] if args.sweep else [
        ("qplite-0p12-depth-aggressive", 0.12, 1.00, 1.0, 3.4, 0.2, 2.7, 13, "depth_aggressive"),
    ]
    VERIFY.mkdir(parents=True, exist_ok=True)
    results = []
    for name, drop, max_blend, policy_weight, descend_s, hold_s, return_s, grid_size, weight_mode in variants:
        out_dir = VERIFY / "attempts" / name
        out_dir.mkdir(parents=True, exist_ok=True)
        trajectory_out = args.trajectory_out
        if args.sweep and trajectory_out is not None:
            trajectory_out = trajectory_out.with_name(f"{trajectory_out.stem}-{name}{trajectory_out.suffix}")
        native = native_eval(
            attempt=name,
            drop=drop,
            max_blend=max_blend,
            policy_weight=policy_weight,
            descend_s=descend_s,
            hold_s=hold_s,
            return_s=return_s,
            seconds=args.seconds,
            params_path=source,
            out_dir=out_dir,
            grid_size=grid_size,
            weights=weights_for(weight_mode),
            trajectory_out=trajectory_out,
        )
        (out_dir / "result.json").write_text(json.dumps({"native": native}, indent=2), encoding="utf-8")
        results.append(native)
    write_summary(results)
    print(json.dumps({"attempts": results}, indent=2), flush=True)


if __name__ == "__main__":
    main()
