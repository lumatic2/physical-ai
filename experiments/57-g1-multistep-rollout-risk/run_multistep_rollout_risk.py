"""Multi-step rollout risk selector for the G1 visible squat gate."""

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
EXP44_PATH = ROOT / "experiments/44-g1-qplite-wbc/run_qplite_wbc.py"
EXP55_PATH = ROOT / "experiments/55-g1-com-zmp-feedback-probe/run_com_zmp_feedback_probe.py"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EXP44 = load_module("exp44_qplite", EXP44_PATH)
EXP55 = load_module("exp55_com_zmp", EXP55_PATH)
EXP42 = EXP44.EXP42
EXP36 = EXP44.EXP36
EXP37 = EXP44.EXP37
EXP28 = EXP44.EXP28


def qpos_index(model: mujoco.MjModel, joint_name: str) -> int:
    return int(model.jnt_qposadr[model.joint(joint_name).id])


def clone_data(model: mujoco.MjModel, data: mujoco.MjData) -> mujoco.MjData:
    cand = mujoco.MjData(model)
    cand.time = data.time
    cand.qpos[:] = data.qpos
    cand.qvel[:] = data.qvel
    cand.act[:] = data.act
    cand.ctrl[:] = data.ctrl
    mujoco.mj_forward(model, cand)
    return cand


def zmp_metrics(model: mujoco.MjModel, data: mujoco.MjData, previous: dict[str, np.ndarray], ctrl_dt: float, foot_geom_ids: np.ndarray) -> dict[str, Any]:
    support = EXP37.support_metrics(model, data, foot_geom_ids)
    center = EXP55.support_center(support)
    com_xy = data.subtree_com[0, :2].copy()
    com_vel = (com_xy - previous["com_xy"]) / ctrl_dt
    com_acc = (com_vel - previous["com_vel"]) / ctrl_dt
    com_z = max(float(data.subtree_com[0, 2]), 0.05)
    zmp_xy = com_xy - (com_z / EXP55.G) * com_acc
    return {
        "support": support,
        "center_xy": center,
        "com_xy": com_xy,
        "com_vel": com_vel,
        "zmp_xy": zmp_xy,
        "zmp_margin": EXP55.support_margin_for_point(zmp_xy, support),
    }


def candidate_target(
    *,
    model: mujoco.MjModel,
    policy_targets: np.ndarray,
    ik_target: np.ndarray,
    blend: float,
    error_xy: np.ndarray,
    feedback_scale: float,
    gains: dict[str, float],
    signs: dict[str, float],
) -> np.ndarray:
    target = (1.0 - blend) * policy_targets + blend * ik_target
    if feedback_scale <= 0.0:
        return np.clip(target, model.actuator_ctrlrange[:, 0], model.actuator_ctrlrange[:, 1])
    scaled_gains = dict(gains)
    for key in ("pitch", "ankle_pitch", "roll", "ankle_roll"):
        scaled_gains[key] *= feedback_scale
    return EXP55.apply_feedback(target, model=model, error_xy=error_xy, gains=scaled_gains, signs=signs)


def candidate_cost(
    *,
    model: mujoco.MjModel,
    cand: mujoco.MjData,
    start_height: float,
    desired_drop: float,
    previous_height: float,
    previous_com: dict[str, np.ndarray],
    ctrl_dt: float,
    initial_foot_xy: np.ndarray,
    foot_site_ids: np.ndarray,
    foot_geom_ids: np.ndarray,
    foot_contact_sensor_ids: list[int],
    blend: float,
    previous_blend: float,
    feedback_scale: float,
    weights: dict[str, float],
) -> tuple[float, dict[str, Any]]:
    height = float(cand.qpos[2])
    target_height = start_height - desired_drop
    vertical_velocity = (height - previous_height) / ctrl_dt
    zmp = zmp_metrics(model, cand, previous_com, ctrl_dt, foot_geom_ids)
    support = zmp["support"]
    contacts = [float(cand.sensordata[model.sensor_adr[sensor_id]]) > 0 for sensor_id in foot_contact_sensor_ids]
    both_feet = all(contacts)
    foot_slip = float(np.max(np.linalg.norm(cand.site_xpos[foot_site_ids, :2] - initial_foot_xy, axis=1)))
    wrench = EXP42.contact_wrench_summary(model, cand)
    inv = EXP44.safe_inverse_summary(model, cand)
    quat = cand.qpos[3:7]
    mat = np.empty(9)
    mujoco.mju_quat2Mat(mat, quat)
    up_z = float(mat.reshape(3, 3)[2, 2])

    height_err = height - target_height
    support_breach = max(0.0, -support["support_margin"])
    zmp_breach = max(0.0, -zmp["zmp_margin"])
    downward = max(0.0, -vertical_velocity - 0.10)
    contact_loss = 0.0 if both_feet else 1.0
    slip_excess = max(0.0, foot_slip - 0.04)
    normal_excess = max(0.0, wrench["total_foot_normal"] - 900.0) / 900.0
    torque_excess = max(0.0, inv["lower_inverse_linf"] - 1900.0) / 1900.0
    gap_excess = max(0.0, inv["qfrc_inverse_minus_actuator_linf"] - 8500.0) / 8500.0
    upright_loss = max(0.0, 0.82 - up_z)
    blend_jump = abs(blend - previous_blend)
    cost_terms = {
        "height": weights["height"] * height_err * height_err,
        "support": weights["support"] * support_breach * support_breach,
        "zmp": weights["zmp"] * zmp_breach * zmp_breach,
        "downward_velocity": weights["downward_velocity"] * downward * downward,
        "contact_loss": weights["contact_loss"] * contact_loss,
        "slip": weights["slip"] * slip_excess * slip_excess,
        "force_imbalance": weights["force_imbalance"] * wrench["lr_normal_imbalance"] ** 2,
        "normal_force": weights["normal_force"] * normal_excess * normal_excess,
        "inverse_torque": weights["inverse_torque"] * torque_excess * torque_excess,
        "inverse_gap": weights["inverse_gap"] * gap_excess * gap_excess,
        "upright": weights["upright"] * upright_loss * upright_loss,
        "blend_jump": weights["blend_jump"] * blend_jump * blend_jump,
        "feedback": weights["feedback"] * feedback_scale * feedback_scale,
    }
    return float(sum(cost_terms.values())), {
        "height": height,
        "target_height": target_height,
        "vertical_velocity": vertical_velocity,
        "support_margin": support["support_margin"],
        "zmp_margin": zmp["zmp_margin"],
        "both_feet_contact": both_feet,
        "foot_slip_distance": foot_slip,
        "up_z": up_z,
        "contact_wrench": wrench,
        "inverse": inv,
        "cost_terms": cost_terms,
    }


def rollout_candidate_cost(
    *,
    model: mujoco.MjModel,
    start_data: mujoco.MjData,
    target: np.ndarray,
    start_height: float,
    desired_drop: float,
    previous_height: float,
    previous_com: dict[str, np.ndarray],
    ctrl_dt: float,
    n_substeps: int,
    horizon_steps: int,
    initial_foot_xy: np.ndarray,
    foot_site_ids: np.ndarray,
    foot_geom_ids: np.ndarray,
    foot_contact_sensor_ids: list[int],
    blend: float,
    previous_blend: float,
    feedback_scale: float,
    weights: dict[str, float],
) -> tuple[float, dict[str, Any]]:
    cand = clone_data(model, start_data)
    total_cost = 0.0
    rolling_height = previous_height
    rolling_com = {"com_xy": previous_com["com_xy"].copy(), "com_vel": previous_com["com_vel"].copy()}
    horizon = {
        "min_height": float(cand.qpos[2]),
        "min_support_margin": float("inf"),
        "min_zmp_margin": float("inf"),
        "max_foot_slip_distance": 0.0,
        "max_lr_normal_imbalance": 0.0,
        "max_inverse_torque": 0.0,
        "max_inverse_gap": 0.0,
        "fell": False,
    }
    last_metrics: dict[str, Any] = {}
    for horizon_idx in range(max(1, horizon_steps)):
        cand.ctrl[:] = target
        for _ in range(n_substeps):
            mujoco.mj_step(model, cand)
        step_cost, metrics = candidate_cost(
            model=model,
            cand=cand,
            start_height=start_height,
            desired_drop=desired_drop,
            previous_height=rolling_height,
            previous_com=rolling_com,
            ctrl_dt=ctrl_dt,
            initial_foot_xy=initial_foot_xy,
            foot_site_ids=foot_site_ids,
            foot_geom_ids=foot_geom_ids,
            foot_contact_sensor_ids=foot_contact_sensor_ids,
            blend=blend,
            previous_blend=previous_blend,
            feedback_scale=feedback_scale,
            weights=weights,
        )
        total_cost += (1.0 + 0.12 * horizon_idx) * step_cost
        zmp = zmp_metrics(model, cand, rolling_com, ctrl_dt, foot_geom_ids)
        rolling_height = float(cand.qpos[2])
        rolling_com = {"com_xy": zmp["com_xy"].copy(), "com_vel": zmp["com_vel"].copy()}
        horizon["min_height"] = min(horizon["min_height"], rolling_height)
        horizon["min_support_margin"] = min(horizon["min_support_margin"], metrics["support_margin"])
        horizon["min_zmp_margin"] = min(horizon["min_zmp_margin"], metrics["zmp_margin"])
        horizon["max_foot_slip_distance"] = max(horizon["max_foot_slip_distance"], metrics["foot_slip_distance"])
        horizon["max_lr_normal_imbalance"] = max(horizon["max_lr_normal_imbalance"], metrics["contact_wrench"]["lr_normal_imbalance"])
        horizon["max_inverse_torque"] = max(horizon["max_inverse_torque"], metrics["inverse"]["lower_inverse_linf"])
        horizon["max_inverse_gap"] = max(horizon["max_inverse_gap"], metrics["inverse"]["qfrc_inverse_minus_actuator_linf"])
        horizon["fell"] = horizon["fell"] or rolling_height < 0.45 or metrics["up_z"] < 0.30
        last_metrics = metrics
        if horizon["fell"]:
            total_cost += 10000.0 * (horizon_steps - horizon_idx)
            break
    total_cost += 750.0 * max(0.0, horizon["max_foot_slip_distance"] - 0.12) ** 2
    total_cost += 650.0 * max(0.0, -horizon["min_support_margin"]) ** 2
    total_cost += 500.0 * max(0.0, -horizon["min_zmp_margin"]) ** 2
    return total_cost, {"last": last_metrics, "horizon": horizon}


def choose_control(
    *,
    model: mujoco.MjModel,
    data: mujoco.MjData,
    policy_targets: np.ndarray,
    ik_target: np.ndarray,
    desired_blend: float,
    desired_drop: float,
    previous_blend: float,
    previous_height: float,
    previous_com: dict[str, np.ndarray],
    start_height: float,
    initial_foot_xy: np.ndarray,
    foot_site_ids: np.ndarray,
    foot_geom_ids: np.ndarray,
    foot_contact_sensor_ids: list[int],
    ctrl_dt: float,
    n_substeps: int,
    weights: dict[str, float],
    gains: dict[str, float],
    signs: dict[str, float],
    grid_size: int,
    feedback_grid: list[float],
    horizon_steps: int,
) -> tuple[np.ndarray, dict[str, Any]]:
    current_support = EXP37.support_metrics(model, data, foot_geom_ids)
    center_xy = EXP55.support_center(current_support)
    error_xy = center_xy - data.subtree_com[0, :2].copy()
    if desired_blend <= 1e-6:
        blend_candidates = np.array([0.0], dtype=np.float64)
    else:
        lo = max(0.0, previous_blend - max(0.10, desired_blend * 0.35))
        hi = min(desired_blend, previous_blend + max(0.16, desired_blend * 0.55))
        blend_candidates = np.unique(np.round(np.concatenate([
            np.linspace(0.0, desired_blend, grid_size),
            np.linspace(lo, hi, max(3, grid_size // 2)),
            [previous_blend, desired_blend],
        ]), 5))
    best = {"cost": float("inf")}
    best_target = policy_targets.copy()
    evaluated = []
    for blend in blend_candidates:
        for feedback_scale in feedback_grid:
            target = candidate_target(
                model=model,
                policy_targets=policy_targets,
                ik_target=ik_target,
                blend=float(blend),
                error_xy=error_xy,
                feedback_scale=feedback_scale,
                gains=gains,
                signs=signs,
            )
            cost, metrics = rollout_candidate_cost(
                model=model,
                start_data=data,
                target=target,
                start_height=start_height,
                desired_drop=desired_drop,
                previous_height=previous_height,
                previous_com=previous_com,
                ctrl_dt=ctrl_dt,
                n_substeps=n_substeps,
                horizon_steps=horizon_steps,
                initial_foot_xy=initial_foot_xy,
                foot_site_ids=foot_site_ids,
                foot_geom_ids=foot_geom_ids,
                foot_contact_sensor_ids=foot_contact_sensor_ids,
                blend=float(blend),
                previous_blend=previous_blend,
                feedback_scale=feedback_scale,
                weights=weights,
            )
            row = {
                "blend": float(blend),
                "feedback_scale": feedback_scale,
                "cost": cost,
                "height": metrics["last"].get("height"),
                "horizon_min_height": metrics["horizon"]["min_height"],
                "support_margin": metrics["horizon"]["min_support_margin"],
                "zmp_margin": metrics["horizon"]["min_zmp_margin"],
                "foot_slip_distance": metrics["horizon"]["max_foot_slip_distance"],
                "lr_normal_imbalance": metrics["horizon"]["max_lr_normal_imbalance"],
                "inverse_torque": metrics["horizon"]["max_inverse_torque"],
                "horizon_fell": metrics["horizon"]["fell"],
            }
            evaluated.append(row)
            if cost < best["cost"]:
                best = {"cost": cost, "blend": float(blend), "feedback_scale": feedback_scale, "metrics": metrics, "error_xy": error_xy}
                best_target = target
    best["evaluated"] = evaluated
    return best_target, best


def classify(native: dict[str, Any]) -> str:
    if native["pass_gate"]:
        return "PASS_COM_QPLITE_NATIVE_GATE"
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


def weights_for(mode: str) -> dict[str, float]:
    base = {
        "height": 260.0,
        "support": 520.0,
        "zmp": 260.0,
        "downward_velocity": 55.0,
        "contact_loss": 90.0,
        "slip": 200.0,
        "force_imbalance": 16.0,
        "normal_force": 9.0,
        "inverse_torque": 7.0,
        "inverse_gap": 4.0,
        "upright": 130.0,
        "blend_jump": 0.9,
        "feedback": 0.08,
    }
    if mode == "balanced":
        return base
    if mode == "depth":
        base["height"] = 520.0
        base["support"] = 420.0
        base["zmp"] = 180.0
        base["force_imbalance"] = 9.0
        base["blend_jump"] = 0.45
        return base
    if mode == "strict":
        base["height"] = 170.0
        base["support"] = 850.0
        base["zmp"] = 500.0
        base["normal_force"] = 16.0
        base["inverse_torque"] = 14.0
        base["blend_jump"] = 1.8
        return base
    raise ValueError(mode)


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
    feedback_grid: list[float],
    weight_mode: str,
    gains: dict[str, float],
    signs: dict[str, float],
    horizon_s: float,
) -> dict[str, Any]:
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
    horizon_steps = max(1, round(horizon_s / ctrl_dt))
    total_steps = int(seconds / ctrl_dt)
    phase = np.ones(2, dtype=np.float32) * np.pi
    command = np.zeros(3, dtype=np.float32)
    last_action = np.zeros(env.action_size, dtype=np.float32)
    gravity_down = np.array([0.0, 0.0, -1.0], dtype=np.float32)
    rng = jax.random.PRNGKey(0)
    initial_foot_xy = data.site_xpos[foot_site_ids, :2].copy()
    start_height = float(data.qpos[2])
    previous_height = start_height
    previous_blend = 0.0
    previous_com = {"com_xy": data.subtree_com[0, :2].copy(), "com_vel": np.zeros(2, dtype=np.float64)}
    start_qpos = data.qpos.copy()
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
    both_feet_contact_count = 0
    max_foot_slip = 0.0
    min_support_margin = float("inf")
    min_zmp_margin = float("inf")
    max_joint_violation = 0.0
    max_knee_delta = 0.0
    max_hip_delta = 0.0
    max_selected_blend = 0.0
    max_feedback_scale = 0.0
    max_normal_force = 0.0
    max_lr_imbalance = 0.0
    max_inverse_torque = 0.0
    max_inverse_gap = 0.0
    samples = []
    weights = weights_for(weight_mode)

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
        desired_fraction, _ = EXP55.phase_fraction(t, descend_s, hold_s, return_s)
        desired_blend = max_blend * desired_fraction
        desired_drop = drop * desired_fraction
        target, selected = choose_control(
            model=model,
            data=data,
            policy_targets=policy_targets,
            ik_target=ik_target,
            desired_blend=desired_blend,
            desired_drop=desired_drop,
            previous_blend=previous_blend,
            previous_height=previous_height,
            previous_com=previous_com,
            start_height=start_height,
            initial_foot_xy=initial_foot_xy,
            foot_site_ids=foot_site_ids,
            foot_geom_ids=foot_geom_ids,
            foot_contact_sensor_ids=foot_contact_sensor_ids,
            ctrl_dt=ctrl_dt,
            n_substeps=n_substeps,
            weights=weights,
            gains=gains,
            signs=signs,
            grid_size=grid_size,
            feedback_grid=feedback_grid,
            horizon_steps=horizon_steps,
        )
        data.ctrl[:] = target
        for _ in range(n_substeps):
            mujoco.mj_step(model, data)
        last_action = action_np
        previous_blend = float(selected["blend"])
        max_selected_blend = max(max_selected_blend, previous_blend)
        max_feedback_scale = max(max_feedback_scale, float(selected["feedback_scale"]))

        height = float(data.qpos[2])
        final_height = height
        min_height = min(min_height, height)
        visible_drop_now = start_height - height
        if visible_drop_now >= 0.08 and first_visible_at is None:
            first_visible_at = round(t, 3)
        zmp = zmp_metrics(model, data, previous_com, ctrl_dt, foot_geom_ids)
        previous_com = {"com_xy": zmp["com_xy"].copy(), "com_vel": zmp["com_vel"].copy()}
        previous_height = height
        support = zmp["support"]
        min_support_margin = min(min_support_margin, support["support_margin"])
        min_zmp_margin = min(min_zmp_margin, zmp["zmp_margin"])
        contacts = [float(data.sensordata[model.sensor_adr[sensor_id]]) > 0 for sensor_id in foot_contact_sensor_ids]
        both_feet = all(contacts)
        both_feet_contact_count += int(both_feet)
        foot_slip = float(np.max(np.linalg.norm(data.site_xpos[foot_site_ids, :2] - initial_foot_xy, axis=1)))
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
        wrench = EXP42.contact_wrench_summary(model, data)
        inv = EXP44.safe_inverse_summary(model, data)
        max_normal_force = max(max_normal_force, wrench["total_foot_normal"])
        max_lr_imbalance = max(max_lr_imbalance, wrench["lr_normal_imbalance"])
        max_inverse_torque = max(max_inverse_torque, inv["lower_inverse_linf"])
        max_inverse_gap = max(max_inverse_gap, inv["qfrc_inverse_minus_actuator_linf"])
        quat = data.qpos[3:7]
        mat = np.empty(9)
        mujoco.mju_quat2Mat(mat, quat)
        up_z = float(mat.reshape(3, 3)[2, 2])
        if (height < 0.45 or up_z < 0.30) and fell_at is None:
            fell_at = round(t, 3)
        if step % max(1, int(0.2 / ctrl_dt)) == 0:
            evaluated = selected["evaluated"]
            samples.append({
                "t": round(t, 3),
                "height": height,
                "visible_drop": visible_drop_now,
                "desired_blend": desired_blend,
                "selected_blend": selected["blend"],
                "feedback_scale": selected["feedback_scale"],
                "support_margin": support["support_margin"],
                "zmp_margin": zmp["zmp_margin"],
                "both_feet_contact": both_feet,
                "foot_slip_distance": foot_slip,
                "up_z": up_z,
                "contact_wrench": wrench,
                "inverse": inv,
                "best_candidate": min(evaluated, key=lambda item: item["cost"]) if evaluated else None,
                "candidate_count": len(evaluated),
            })

    foot_contact_ratio = both_feet_contact_count / max(1, total_steps)
    visible_drop = start_height - min_height
    return_to_stand = final_height >= 0.74
    native = {
        "attempt": attempt,
        "drop": drop,
        "max_blend": max_blend,
        "policy_weight": policy_weight,
        "weight_mode": weight_mode,
        "weights": weights,
        "grid_size": grid_size,
        "feedback_grid": feedback_grid,
        "horizon_s": horizon_s,
        "horizon_steps": horizon_steps,
        "gains": gains,
        "signs": signs,
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
        "max_joint_limit_violation": max_joint_violation,
        "max_knee_delta_rad": max_knee_delta,
        "max_hip_pitch_delta_rad": max_hip_delta,
        "max_selected_blend": max_selected_blend,
        "max_feedback_scale": max_feedback_scale,
        "max_total_foot_normal_force": max_normal_force,
        "max_lr_normal_imbalance": max_lr_imbalance,
        "max_lower_inverse_torque": max_inverse_torque,
        "max_inverse_minus_actuator": max_inverse_gap,
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
        "# G1 Multi-step Rollout Risk Summary",
        "",
        "| Attempt | Verdict | Horizon | Drop | Knee | Hip | Contact | Slip | CoM min | ZMP min | Blend | Fdbk | Force | Inv torque | Fell |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for run in result["runs"]:
        fell = "never" if run["fell_at"] is None else f"{run['fell_at']:.2f}s"
        lines.append(
            f"| {run['attempt']} | {run['verdict']} | {run['horizon_s']:.1f}s | {run['visible_drop']:.4f}m | "
            f"{run['max_knee_delta_rad']:.3f} | {run['max_hip_pitch_delta_rad']:.3f} | "
            f"{run['foot_contact_ratio']:.2f} | {run['foot_slip_distance']:.3f}m | "
            f"{run['min_support_margin']:.4f}m | {run['min_zmp_margin']:.4f}m | "
            f"{run['max_selected_blend']:.2f} | {run['max_feedback_scale']:.2f} | "
            f"{run['max_total_foot_normal_force']:.1f} | {run['max_lower_inverse_torque']:.1f} | {fell} |"
        )
    lines.extend([
        "",
        f"Best no-fall run: {result['best_no_fall']}",
        f"Best depth run: {result['best_depth']}",
        "",
        "M19 closes only when visible depth, knee/hip pose, no-fall, contact, stance, return, and browser replay gates pass together.",
    ])
    (out_dir / "multistep-rollout-risk-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=None)
    parser.add_argument("--seconds", type=float, default=6.0)
    parser.add_argument("--only", action="append", default=[])
    parser.add_argument("--grid-size", type=int, default=9)
    parser.add_argument("--summarize-only", action="store_true")
    args = parser.parse_args()
    source = args.source or EXP28.default_source()
    out_dir = VERIFY / "multistep-rollout-risk"
    out_dir.mkdir(parents=True, exist_ok=True)
    gains = {
        "pitch": 2.0,
        "ankle_pitch": -1.4,
        "roll": 1.6,
        "ankle_roll": -1.0,
        "clip_pitch": 0.16,
        "clip_roll": 0.08,
    }
    signs = {"pitch": 1.0, "ankle_pitch": 1.0, "roll": 1.0, "ankle_roll": 1.0}
    variants = [
        {"attempt": "h0p4-balanced-0p08", "drop": 0.08, "max_blend": 0.70, "descend_s": 3.2, "return_s": 1.6, "mode": "balanced", "feedback_grid": [0.0, 0.5, 1.0], "horizon_s": 0.4},
        {"attempt": "h0p8-balanced-0p08", "drop": 0.08, "max_blend": 0.70, "descend_s": 3.2, "return_s": 1.6, "mode": "balanced", "feedback_grid": [0.0, 0.5, 1.0], "horizon_s": 0.8},
        {"attempt": "h0p4-depth-0p10", "drop": 0.10, "max_blend": 0.85, "descend_s": 3.8, "return_s": 1.8, "mode": "depth", "feedback_grid": [0.0, 0.5, 1.0], "horizon_s": 0.4},
        {"attempt": "h0p8-depth-0p10", "drop": 0.10, "max_blend": 0.85, "descend_s": 3.8, "return_s": 1.8, "mode": "depth", "feedback_grid": [0.0, 0.5, 1.0], "horizon_s": 0.8},
    ]
    result = {
        "planning_gate": {
            "team_validation_mode": "manual-pass",
            "spec_delta": "M19 probes a 0.4-0.8s rollout selector over blend and CoM feedback scale, using height/support/ZMP/contact-force costs.",
            "perspectives": {
                "product": "directly pursues the native visible squat gate",
                "architecture": "reuses exp44 selector metrics and exp55 CoM feedback, but rolls each candidate forward for multiple MuJoCo control ticks",
                "security": "no credentials or external side effects",
                "qa": "native sweep logs stance, pose, ZMP, contact force, inverse torque, return, fall",
                "skeptic": "multi-step risk may still choose shallow controls if the only stable basin is standing",
            },
            "dod": [
                "native JSON per selector variant",
                "summary identifies whether combined selector closes or improves M19 gate",
            ],
        },
        "runs": [],
    }
    selected = [variant for variant in variants if not args.only or variant["attempt"] in set(args.only)]
    if not args.summarize_only:
        for variant in selected:
            result["runs"].append(native_eval(
                attempt=variant["attempt"],
                drop=variant["drop"],
                max_blend=variant["max_blend"],
                policy_weight=1.0,
                descend_s=variant["descend_s"],
                hold_s=0.4,
                return_s=variant["return_s"],
                seconds=args.seconds,
                params_path=source,
                out_dir=out_dir / variant["attempt"],
                grid_size=args.grid_size,
                feedback_grid=variant["feedback_grid"],
                weight_mode=variant["mode"],
                gains=gains,
                signs=signs,
                horizon_s=variant["horizon_s"],
            ))
    result["runs"] = []
    for variant in variants:
        native_path = out_dir / variant["attempt"] / "native-eval.json"
        if native_path.exists():
            result["runs"].append(json.loads(native_path.read_text(encoding="utf-8")))
    if not result["runs"]:
        raise RuntimeError("no native-eval.json files available to summarize")
    no_fall = [run for run in result["runs"] if run["fell_at"] is None]
    best_no_fall = max(no_fall, key=lambda run: run["visible_drop"], default=None)
    best_depth = max(result["runs"], key=lambda run: run["visible_drop"])
    result["best_no_fall"] = None if best_no_fall is None else {
        "attempt": best_no_fall["attempt"],
        "visible_drop": best_no_fall["visible_drop"],
        "max_knee_delta_rad": best_no_fall["max_knee_delta_rad"],
        "max_hip_pitch_delta_rad": best_no_fall["max_hip_pitch_delta_rad"],
        "return_to_stand": best_no_fall["return_to_stand"],
        "foot_slip_distance": best_no_fall["foot_slip_distance"],
    }
    result["best_depth"] = {
        "attempt": best_depth["attempt"],
        "visible_drop": best_depth["visible_drop"],
        "fell_at": best_depth["fell_at"],
        "foot_slip_distance": best_depth["foot_slip_distance"],
    }
    result["verdict"] = "PASS_M19_NATIVE_ONLY" if any(run["pass_gate"] for run in result["runs"]) else "FAIL_M19_NATIVE_GATE"
    write_summary(result, out_dir)
    (out_dir / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(result["verdict"], json.dumps({"best_no_fall": result["best_no_fall"], "best_depth": result["best_depth"]}, indent=2), flush=True)


if __name__ == "__main__":
    main()
