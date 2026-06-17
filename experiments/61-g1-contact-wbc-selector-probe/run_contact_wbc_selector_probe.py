"""Probe a contact/torque-aware WBC-style selector for G1 squat.

This stays in the existing position-control sandbox, but makes the missing
WBC contract explicit: pick each control target by one-step contact prediction,
not by hand-scaled residuals alone.
"""

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
EXP60_PATH = ROOT / "experiments/60-g1-safe-combo-curriculum-probe/run_safe_combo_curriculum_probe.py"
EXP42_PATH = ROOT / "experiments/42-g1-contact-inverse-force-probe/run_force_probe.py"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EXP60 = load_module("exp60_safe_combo", EXP60_PATH)
EXP42 = load_module("exp42_force_probe", EXP42_PATH)
EXP52 = EXP60.EXP52
EXP28 = EXP60.EXP28
EXP36 = EXP60.EXP36
EXP37 = EXP60.EXP37

G = 9.81


def clone_data(model: mujoco.MjModel, data: mujoco.MjData) -> mujoco.MjData:
    cand = mujoco.MjData(model)
    cand.time = data.time
    cand.qpos[:] = data.qpos
    cand.qvel[:] = data.qvel
    cand.act[:] = data.act
    cand.ctrl[:] = data.ctrl
    mujoco.mj_forward(model, cand)
    return cand


def zmp_margin_for_candidate(
    *,
    model: mujoco.MjModel,
    cand: mujoco.MjData,
    support: dict[str, Any],
    current_com_xy: np.ndarray,
    previous_com_vel: np.ndarray,
    ctrl_dt: float,
) -> tuple[np.ndarray, float]:
    com_xy = cand.subtree_com[0, :2].copy()
    com_vel = (com_xy - current_com_xy) / ctrl_dt
    com_acc = (com_vel - previous_com_vel) / ctrl_dt
    com_z = max(float(cand.subtree_com[0, 2]), 0.05)
    zmp_xy = com_xy - (com_z / G) * com_acc
    return zmp_xy, EXP60.support_margin_for_point(zmp_xy, support)


def candidate_cost(
    *,
    model: mujoco.MjModel,
    cand: mujoco.MjData,
    foot_geom_ids: np.ndarray,
    current_height: float,
    start_height: float,
    desired_drop: float,
    desired_fraction: float,
    current_com_xy: np.ndarray,
    previous_com_vel: np.ndarray,
    ctrl_dt: float,
    initial_foot_xy: np.ndarray,
    foot_site_ids: np.ndarray,
    foot_contact_sensor_ids: list[int],
    start_qpos: np.ndarray,
    qpos_indices: dict[str, int],
    blend: float,
    residual_scale: float,
    previous_blend: float,
    previous_residual_scale: float,
    weights: dict[str, float],
) -> tuple[float, dict[str, Any]]:
    height = float(cand.qpos[2])
    vertical_velocity = (height - current_height) / ctrl_dt
    support = EXP37.support_metrics(model, cand, foot_geom_ids)
    zmp_xy, zmp_margin = zmp_margin_for_candidate(
        model=model,
        cand=cand,
        support=support,
        current_com_xy=current_com_xy,
        previous_com_vel=previous_com_vel,
        ctrl_dt=ctrl_dt,
    )
    contacts = [
        float(cand.sensordata[model.sensor_adr[sensor_id]]) > 0
        for sensor_id in foot_contact_sensor_ids
    ]
    both_feet = all(contacts)
    foot_slip = float(np.max(np.linalg.norm(cand.site_xpos[foot_site_ids, :2] - initial_foot_xy, axis=1)))
    wrench = EXP42.contact_wrench_summary(model, cand)
    inv = EXP42.inverse_summary(model, clone_data(model, cand))
    knee_delta = max(
        abs(float(cand.qpos[qpos_indices["left_knee_joint"]] - start_qpos[qpos_indices["left_knee_joint"]])),
        abs(float(cand.qpos[qpos_indices["right_knee_joint"]] - start_qpos[qpos_indices["right_knee_joint"]])),
    )
    hip_delta = max(
        abs(float(cand.qpos[qpos_indices["left_hip_pitch_joint"]] - start_qpos[qpos_indices["left_hip_pitch_joint"]])),
        abs(float(cand.qpos[qpos_indices["right_hip_pitch_joint"]] - start_qpos[qpos_indices["right_hip_pitch_joint"]])),
    )
    quat = cand.qpos[3:7]
    mat = np.empty(9)
    mujoco.mju_quat2Mat(mat, quat)
    up_z = float(mat.reshape(3, 3)[2, 2])

    target_height = start_height - desired_drop
    height_err = height - target_height
    desired_knee = 0.60 * desired_fraction
    desired_hip = 0.35 * desired_fraction
    knee_err = max(0.0, desired_knee - knee_delta)
    hip_err = max(0.0, desired_hip - hip_delta)
    support_breach = max(0.0, 0.012 - float(support["support_margin"]))
    zmp_breach = max(0.0, 0.010 - zmp_margin)
    slip_excess = max(0.0, foot_slip - 0.035)
    downward = max(0.0, -vertical_velocity - 0.08)
    contact_loss = 0.0 if both_feet else 1.0
    upright_loss = max(0.0, 0.80 - up_z)
    normal_excess = max(0.0, wrench["total_foot_normal"] - 850.0) / 850.0
    torque_excess = max(0.0, inv["lower_inverse_linf"] - 1800.0) / 1800.0
    gap_excess = max(0.0, inv["qfrc_inverse_minus_actuator_linf"] - 8500.0) / 8500.0

    terms = {
        "height": weights["height"] * height_err * height_err,
        "pose": weights["pose"] * (knee_err * knee_err + hip_err * hip_err),
        "support": weights["support"] * support_breach * support_breach,
        "zmp": weights["zmp"] * zmp_breach * zmp_breach,
        "slip": weights["slip"] * slip_excess * slip_excess,
        "downward": weights["downward"] * downward * downward,
        "contact": weights["contact"] * contact_loss,
        "force_imbalance": weights["force_imbalance"] * wrench["lr_normal_imbalance"] ** 2,
        "normal_force": weights["normal_force"] * normal_excess * normal_excess,
        "inverse_torque": weights["inverse_torque"] * torque_excess * torque_excess,
        "inverse_gap": weights["inverse_gap"] * gap_excess * gap_excess,
        "upright": weights["upright"] * upright_loss * upright_loss,
        "smooth": weights["smooth"] * ((blend - previous_blend) ** 2 + (residual_scale - previous_residual_scale) ** 2),
    }
    return float(sum(terms.values())), {
        "height": height,
        "vertical_velocity": vertical_velocity,
        "zmp_xy": [float(v) for v in zmp_xy],
        "zmp_margin": zmp_margin,
        "both_feet_contact": both_feet,
        "foot_slip_distance": foot_slip,
        "knee_delta": knee_delta,
        "hip_delta": hip_delta,
        "up_z": up_z,
        "contact_wrench": wrench,
        "inverse": inv,
        "cost_terms": terms,
    }


def apply_candidate_target(
    *,
    model: mujoco.MjModel,
    policy_targets: np.ndarray,
    ik_target: np.ndarray,
    blend: float,
    feedback_error_xy: np.ndarray,
    gains: dict[str, float],
    signs: dict[str, float],
    residual_scale: float,
    desired_fraction: float,
    support_health: float,
    zmp_health: float,
    slip_health: float,
) -> np.ndarray:
    target = (1.0 - blend) * policy_targets + blend * ik_target
    target = EXP60.apply_feedback(target, model=model, error_xy=feedback_error_xy, gains=gains, signs=signs)
    target = EXP60.apply_residual_pattern(
        target,
        model=model,
        pattern="safe_combo",
        scale=residual_scale,
        phase_depth=desired_fraction,
        support_health=support_health,
        zmp_health=zmp_health,
        slip_health=slip_health,
        error_xy=feedback_error_xy,
        filter_mode="soft",
    )
    return np.clip(target, model.actuator_ctrlrange[:, 0], model.actuator_ctrlrange[:, 1])


def choose_target(
    *,
    model: mujoco.MjModel,
    data: mujoco.MjData,
    policy_targets: np.ndarray,
    ik_target: np.ndarray,
    desired_blend: float,
    desired_drop: float,
    desired_fraction: float,
    feedback_error_xy: np.ndarray,
    gains: dict[str, float],
    signs: dict[str, float],
    support: dict[str, Any],
    zmp_margin: float,
    foot_slip: float,
    current_height: float,
    start_height: float,
    current_com_xy: np.ndarray,
    previous_com_vel: np.ndarray,
    ctrl_dt: float,
    n_substeps: int,
    initial_foot_xy: np.ndarray,
    foot_site_ids: np.ndarray,
    foot_geom_ids: np.ndarray,
    foot_contact_sensor_ids: list[int],
    start_qpos: np.ndarray,
    qpos_indices: dict[str, int],
    previous_blend: float,
    previous_residual_scale: float,
    residual_cap: float,
    weights: dict[str, float],
) -> tuple[np.ndarray, dict[str, Any]]:
    support_health = float(np.clip((support["support_margin"] + 0.005) / 0.045, 0.0, 1.0))
    zmp_health = float(np.clip((zmp_margin + 0.005) / 0.045, 0.0, 1.0))
    slip_health = float(np.clip(1.0 - foot_slip / 0.08, 0.0, 1.0))
    blend_candidates = np.unique(np.round(np.array([
        0.0,
        0.50 * desired_blend,
        0.75 * desired_blend,
        desired_blend,
        min(desired_blend, previous_blend + 0.08),
        max(0.0, previous_blend - 0.08),
    ]), 5))
    residual_candidates = np.unique(np.round(np.array([
        0.0,
        0.50 * residual_cap,
        0.75 * residual_cap,
        residual_cap,
        min(residual_cap, previous_residual_scale + 0.015),
        max(0.0, previous_residual_scale - 0.015),
    ]), 5))
    best: dict[str, Any] | None = None
    evaluated = []
    for blend in blend_candidates:
        for residual_scale in residual_candidates:
            target = apply_candidate_target(
                model=model,
                policy_targets=policy_targets,
                ik_target=ik_target,
                blend=float(blend),
                feedback_error_xy=feedback_error_xy,
                gains=gains,
                signs=signs,
                residual_scale=float(residual_scale),
                desired_fraction=desired_fraction,
                support_health=support_health,
                zmp_health=zmp_health,
                slip_health=slip_health,
            )
            cand = clone_data(model, data)
            cand.ctrl[:] = target
            for _ in range(n_substeps):
                mujoco.mj_step(model, cand)
            cost, metrics = candidate_cost(
                model=model,
                cand=cand,
                current_height=current_height,
                start_height=start_height,
                desired_drop=desired_drop,
                desired_fraction=desired_fraction,
                current_com_xy=current_com_xy,
                previous_com_vel=previous_com_vel,
                ctrl_dt=ctrl_dt,
                initial_foot_xy=initial_foot_xy,
                foot_site_ids=foot_site_ids,
                foot_geom_ids=foot_geom_ids,
                foot_contact_sensor_ids=foot_contact_sensor_ids,
                start_qpos=start_qpos,
                qpos_indices=qpos_indices,
                blend=float(blend),
                residual_scale=float(residual_scale),
                previous_blend=previous_blend,
                previous_residual_scale=previous_residual_scale,
                weights=weights,
            )
            row = {
                "blend": float(blend),
                "residual_scale": float(residual_scale),
                "cost": cost,
                "height": metrics["height"],
                "zmp_margin": metrics["zmp_margin"],
                "foot_slip_distance": metrics["foot_slip_distance"],
                "knee_delta": metrics["knee_delta"],
                "hip_delta": metrics["hip_delta"],
                "lower_inverse_linf": metrics["inverse"]["lower_inverse_linf"],
            }
            evaluated.append(row)
            if best is None or cost < best["cost"]:
                best = {"cost": cost, "target": target, "metrics": metrics, **row}
    assert best is not None
    best["evaluated_candidates"] = evaluated
    return best["target"], best


def classify(native: dict[str, Any]) -> str:
    if native["pass_gate"]:
        return "PASS_CONTACT_WBC_NATIVE_GATE"
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


def native_eval(*, attempt: str, drop: float, max_blend: float, residual_cap: float, weights: dict[str, float], seconds: float, out_dir: Path) -> dict[str, Any]:
    env = EXP28.ContactAwareSquat(
        stage_height=0.67,
        controller_blend=max_blend,
        freeze_phase=True,
        blend_schedule="squat",
        reference_scale=1.0,
        config_overrides={"impl": "jax"},
    )
    policy = EXP28.build_policy(env, EXP52.EXP46_PARAMS)
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
    start_qpos = data.qpos.copy()
    previous_height = start_height
    previous_com_xy = data.subtree_com[0, :2].copy()
    previous_com_vel = np.zeros(2, dtype=np.float64)
    previous_blend = 0.0
    previous_residual_scale = 0.0
    qpos_indices = {
        "left_hip_pitch_joint": EXP60.qpos_index(model, "left_hip_pitch_joint"),
        "right_hip_pitch_joint": EXP60.qpos_index(model, "right_hip_pitch_joint"),
        "left_knee_joint": EXP60.qpos_index(model, "left_knee_joint"),
        "right_knee_joint": EXP60.qpos_index(model, "right_knee_joint"),
    }
    gains = {
        "pitch": 2.0,
        "ankle_pitch": -1.4,
        "roll": 1.6,
        "ankle_roll": -1.0,
        "clip_pitch": 0.16,
        "clip_roll": 0.08,
    }
    signs = {"pitch": 1.0, "ankle_pitch": 1.0, "roll": 1.0, "ankle_roll": 1.0}

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
    max_selected_residual = 0.0
    max_inverse_torque = 0.0
    max_inverse_gap = 0.0
    max_lr_imbalance = 0.0
    samples = []

    for step in range(total_steps):
        t = step * ctrl_dt
        height = float(data.qpos[2])
        vertical_velocity = (height - previous_height) / ctrl_dt
        previous_height = height
        final_height = height
        min_height = min(min_height, height)
        support = EXP37.support_metrics(model, data, foot_geom_ids)
        center_xy = EXP60.support_center(support)
        com_xy = data.subtree_com[0, :2].copy()
        com_vel = (com_xy - previous_com_xy) / ctrl_dt
        com_acc = (com_vel - previous_com_vel) / ctrl_dt
        com_z = max(float(data.subtree_com[0, 2]), 0.05)
        zmp_xy = com_xy - (com_z / G) * com_acc
        zmp_margin = EXP60.support_margin_for_point(zmp_xy, support)
        feedback_error_xy = center_xy - com_xy
        desired_fraction, return_phase = EXP60.phase_fraction(t, 3.2, 0.4, 1.8)
        desired_blend = 0.0 if return_phase > 0 else max_blend * desired_fraction
        desired_drop = drop * desired_fraction
        contacts = [
            float(data.sensordata[model.sensor_adr[sensor_id]]) > 0
            for sensor_id in foot_contact_sensor_ids
        ]
        both_feet = all(contacts)
        both_feet_contact_count += int(both_feet)
        foot_slip = float(np.max(np.linalg.norm(data.site_xpos[foot_site_ids, :2] - initial_foot_xy, axis=1)))

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
        policy_targets = default_pose + action_np * float(env._config.action_scale)
        target, selected = choose_target(
            model=model,
            data=data,
            policy_targets=policy_targets,
            ik_target=ik_target,
            desired_blend=desired_blend,
            desired_drop=desired_drop,
            desired_fraction=desired_fraction,
            feedback_error_xy=feedback_error_xy,
            gains=gains,
            signs=signs,
            support=support,
            zmp_margin=zmp_margin,
            foot_slip=foot_slip,
            current_height=height,
            start_height=start_height,
            current_com_xy=com_xy,
            previous_com_vel=previous_com_vel,
            ctrl_dt=ctrl_dt,
            n_substeps=n_substeps,
            initial_foot_xy=initial_foot_xy,
            foot_site_ids=foot_site_ids,
            foot_geom_ids=foot_geom_ids,
            foot_contact_sensor_ids=foot_contact_sensor_ids,
            start_qpos=start_qpos,
            qpos_indices=qpos_indices,
            previous_blend=previous_blend,
            previous_residual_scale=previous_residual_scale,
            residual_cap=residual_cap,
            weights=weights,
        )
        data.ctrl[:] = target
        for _ in range(n_substeps):
            mujoco.mj_step(model, data)
        previous_com_xy = com_xy.copy()
        previous_com_vel = com_vel.copy()
        previous_blend = float(selected["blend"])
        previous_residual_scale = float(selected["residual_scale"])
        max_selected_blend = max(max_selected_blend, previous_blend)
        max_selected_residual = max(max_selected_residual, previous_residual_scale)
        last_action = action_np

        visible_drop_now = start_height - height
        if visible_drop_now >= 0.08 and first_visible_at is None:
            first_visible_at = round(t, 3)
        min_support_margin = min(min_support_margin, support["support_margin"])
        min_zmp_margin = min(min_zmp_margin, zmp_margin)
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
        max_inverse_torque = max(max_inverse_torque, selected["metrics"]["inverse"]["lower_inverse_linf"])
        max_inverse_gap = max(max_inverse_gap, selected["metrics"]["inverse"]["qfrc_inverse_minus_actuator_linf"])
        max_lr_imbalance = max(max_lr_imbalance, selected["metrics"]["contact_wrench"]["lr_normal_imbalance"])

        if step % max(1, int(0.2 / ctrl_dt)) == 0:
            samples.append({
                "t": round(t, 3),
                "height": height,
                "visible_drop": visible_drop_now,
                "vertical_velocity": vertical_velocity,
                "desired_blend": desired_blend,
                "selected_blend": selected["blend"],
                "selected_residual_scale": selected["residual_scale"],
                "selected_cost": selected["cost"],
                "support_margin": support["support_margin"],
                "zmp_margin": zmp_margin,
                "both_feet_contact": both_feet,
                "foot_slip_distance": foot_slip,
                "knee_delta": max_knee_delta,
                "hip_delta": max_hip_delta,
                "up_z": up_z,
                "best_candidate": {k: selected[k] for k in ("blend", "residual_scale", "cost", "height", "zmp_margin", "foot_slip_distance", "knee_delta", "hip_delta", "lower_inverse_linf")},
            })

    visible_drop = start_height - min_height
    foot_contact_ratio = both_feet_contact_count / max(1, total_steps)
    return_to_stand = final_height >= 0.74
    native = {
        "attempt": attempt,
        "drop": drop,
        "max_blend": max_blend,
        "residual_cap": residual_cap,
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
        "min_zmp_margin": min_zmp_margin,
        "max_joint_limit_violation": max_joint_violation,
        "max_knee_delta_rad": max_knee_delta,
        "max_hip_pitch_delta_rad": max_hip_delta,
        "max_selected_blend": max_selected_blend,
        "max_selected_residual": max_selected_residual,
        "max_lower_inverse_torque": max_inverse_torque,
        "max_inverse_minus_actuator": max_inverse_gap,
        "max_lr_normal_imbalance": max_lr_imbalance,
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


def weights_for(mode: str) -> dict[str, float]:
    base = {
        "height": 140.0,
        "pose": 12.0,
        "support": 900.0,
        "zmp": 900.0,
        "slip": 260.0,
        "downward": 65.0,
        "contact": 90.0,
        "force_imbalance": 22.0,
        "normal_force": 16.0,
        "inverse_torque": 16.0,
        "inverse_gap": 10.0,
        "upright": 120.0,
        "smooth": 1.4,
    }
    if mode == "stance_ultra":
        base["height"] = 90.0
        base["pose"] = 4.0
        base["support"] = 1800.0
        base["zmp"] = 1800.0
        base["slip"] = 520.0
        base["downward"] = 120.0
        base["contact"] = 180.0
        base["force_imbalance"] = 45.0
        base["smooth"] = 3.0
        return base
    if mode == "stance_strict":
        return base
    if mode == "pose_balanced":
        base["height"] = 230.0
        base["pose"] = 32.0
        base["support"] = 720.0
        base["zmp"] = 720.0
        return base
    if mode == "pose_push":
        base["height"] = 420.0
        base["pose"] = 70.0
        base["support"] = 540.0
        base["zmp"] = 540.0
        base["smooth"] = 0.7
        return base
    raise ValueError(mode)


def write_summary(result: dict[str, Any], out_dir: Path) -> None:
    lines = [
        "# G1 Contact-WBC Selector Probe Summary",
        "",
        "| Attempt | Verdict | Drop | Knee | Hip | Contact | Slip | CoM min | ZMP min | Blend | Residual | Inv torque | Final h | Fell |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for run in result["runs"]:
        fell = "never" if run["fell_at"] is None else f"{run['fell_at']:.2f}s"
        lines.append(
            f"| {run['attempt']} | {run['verdict']} | {run['visible_drop']:.4f}m | "
            f"{run['max_knee_delta_rad']:.3f} | {run['max_hip_pitch_delta_rad']:.3f} | "
            f"{run['foot_contact_ratio']:.2f} | {run['foot_slip_distance']:.3f}m | "
            f"{run['min_support_margin']:.4f}m | {run['min_zmp_margin']:.4f}m | "
            f"{run['max_selected_blend']:.2f} | {run['max_selected_residual']:.3f} | "
            f"{run['max_lower_inverse_torque']:.1f} | {run['final_height']:.4f}m | {fell} |"
        )
    lines.extend([
        "",
        f"Best no-fall run: {result['best_no_fall']}",
        f"Best depth run: {result['best_depth']}",
        "",
        "M19 closes only when visible depth, knee/hip pose, no-fall, contact, stance, return, and browser replay gates pass together.",
    ])
    (out_dir / "contact-wbc-selector-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=6.0)
    args = parser.parse_args()
    out_dir = VERIFY / "contact-wbc-selector"
    out_dir.mkdir(parents=True, exist_ok=True)
    variants = [
        ("stance-ultra-0p08-r0p06", 0.08, 0.50, 0.06, "stance_ultra"),
        ("stance-strict-0p08-r0p08", 0.08, 0.52, 0.08, "stance_strict"),
        ("pose-balanced-0p08-r0p09", 0.08, 0.56, 0.09, "pose_balanced"),
        ("pose-push-0p08-r0p10", 0.08, 0.60, 0.10, "pose_push"),
        ("pose-balanced-0p10-r0p09", 0.10, 0.58, 0.09, "pose_balanced"),
    ]
    result = {
        "planning_gate": {
            "team_validation_mode": "manual-pass",
            "spec_delta": "M19 moves from hand residual scaling to a contact/torque-aware WBC-style selector for stance foot constraints.",
            "perspectives": {
                "product": "directly tests the current M19 blocker: visible depth without support/ZMP collapse",
                "architecture": "reuses exp60 safe_combo and exp42 force diagnostics, adding one-step contact-aware target selection",
                "security": "no credentials or external side effects",
                "qa": "native sweep logs pose, contact, slip, support, ZMP, inverse torque, return, fall",
                "skeptic": "one-step selection may choose safety by refusing depth, so pose gate remains the key falsifier",
            },
            "dod": [
                "native JSON per selector variant under verify/",
                "summary identifies whether contact-aware selection expands the stable corridor beyond exp60",
            ],
        },
        "runs": [],
    }
    for name, drop, max_blend, residual_cap, mode in variants:
        result["runs"].append(
            native_eval(
                attempt=name,
                drop=drop,
                max_blend=max_blend,
                residual_cap=residual_cap,
                weights=weights_for(mode),
                seconds=args.seconds,
                out_dir=out_dir / name,
            )
        )
    no_fall = [run for run in result["runs"] if run["fell_at"] is None]
    best_no_fall = max(no_fall, key=lambda run: run["visible_drop"], default=None)
    best_depth = max(result["runs"], key=lambda run: run["visible_drop"])
    result["best_no_fall"] = None if best_no_fall is None else {
        "attempt": best_no_fall["attempt"],
        "visible_drop": best_no_fall["visible_drop"],
        "max_knee_delta_rad": best_no_fall["max_knee_delta_rad"],
        "max_hip_pitch_delta_rad": best_no_fall["max_hip_pitch_delta_rad"],
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
