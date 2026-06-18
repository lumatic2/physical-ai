"""Search finite-horizon trajectory plans around the G1 squat contact-safe branch."""

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
VERIFY = EXP_DIR / "verify"
EXP67_PATH = ROOT / "experiments/67-g1-qfrc-wbc-return-selector/run_qfrc_wbc_return_selector.py"


def load_exp67():
    spec = importlib.util.spec_from_file_location("exp67_qfrc_wbc", EXP67_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {EXP67_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EXP67 = load_exp67()
EXP62 = EXP67.EXP62
EXP37 = EXP67.EXP37


def pose_delta(model: mujoco.MjModel, data: mujoco.MjData) -> dict[str, float]:
    start = model.keyframe("knees_bent").qpos
    qpos_index = EXP62.qpos_index
    lk = qpos_index(model, "left_knee_joint")
    rk = qpos_index(model, "right_knee_joint")
    lh = qpos_index(model, "left_hip_pitch_joint")
    rh = qpos_index(model, "right_hip_pitch_joint")
    return {
        "knee": max(abs(float(data.qpos[lk] - start[lk])), abs(float(data.qpos[rk] - start[rk]))),
        "hip": max(abs(float(data.qpos[lh] - start[lh])), abs(float(data.qpos[rh] - start[rh]))),
    }


def bell_window(x: float, start: float, peak: float, end: float) -> float:
    if x <= start or x >= end:
        return 0.0
    if x <= peak:
        return float(np.clip((x - start) / max(1e-6, peak - start), 0.0, 1.0))
    return float(np.clip((end - x) / max(1e-6, end - peak), 0.0, 1.0))


def apply_pose_bias(
    model: mujoco.MjModel,
    target: np.ndarray,
    variant: dict[str, Any],
    desired_fraction: float,
    return_phase: float,
    support_health: float,
    zmp_health: float,
    slip_health: float,
) -> tuple[np.ndarray, dict[str, float]]:
    biased = target.copy()
    phase_mode = variant.get("_phase_mode", "descend")
    if phase_mode == "stand":
        return biased, {
            "pose_bias_scale": 0.0,
            "pose_health": float(min(support_health, zmp_health, slip_health)),
            "pose_health_scale": 0.0,
        }
    descend_window = bell_window(
        desired_fraction,
        variant["pose_start"],
        variant["pose_peak"],
        variant["pose_end"],
    )
    return_scale = max(0.0, 1.0 - return_phase) * variant["return_pose_scale"]
    health = min(support_health, zmp_health, slip_health)
    health_scale = float(np.clip((health - variant["pose_health_floor"]) / max(1e-6, 1.0 - variant["pose_health_floor"]), 0.0, 1.0))
    scale = max(descend_window, return_scale) * health_scale
    biased[3] += variant["knee_amp"] * scale
    biased[9] += variant["knee_amp"] * scale
    biased[0] -= variant["hip_bias"] * scale
    biased[6] -= variant["hip_bias"] * scale
    ctrlrange = model.actuator_ctrlrange
    np.clip(biased, ctrlrange[:, 0], ctrlrange[:, 1], out=biased)
    return biased, {
        "pose_bias_scale": float(scale),
        "pose_health": float(health),
        "pose_health_scale": float(health_scale),
    }


def return_policy_targets(policy_targets: np.ndarray, variant: dict[str, Any], return_phase: float) -> np.ndarray:
    default = variant["default_pose"]
    keep = float(variant["return_policy_weight"]) * max(0.0, 1.0 - return_phase)
    return default + keep * (policy_targets - default)


def apply_stance_preload(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    foot_site_ids: np.ndarray,
    initial_foot_xyz: np.ndarray,
    foot_contact_sensor_ids: list[int],
    preload_force: float,
    height_kp: float,
    force_clip: float,
) -> tuple[np.ndarray, dict[str, Any]]:
    qfrc = np.zeros(model.nv)
    diagnostics: list[dict[str, float | bool]] = []
    if preload_force <= 0.0 or force_clip <= 0.0:
        return qfrc, {"stance_preload": diagnostics, "stance_preload_max_force": 0.0}
    max_force = 0.0
    for idx, site_id in enumerate(foot_site_ids):
        jacp = np.zeros((3, model.nv))
        jacr = np.zeros((3, model.nv))
        mujoco.mj_jacSite(model, data, jacp, jacr, int(site_id))
        sensor_id = foot_contact_sensor_ids[idx]
        contact = float(data.sensordata[model.sensor_adr[sensor_id]]) > 0.0
        height_err = float(data.site_xpos[site_id, 2] - initial_foot_xyz[idx, 2])
        contact_mult = 1.0 if contact else 1.6
        down_force = min(force_clip, preload_force * contact_mult + height_kp * max(0.0, height_err))
        force = np.array([0.0, 0.0, -down_force])
        qfrc += jacp.T @ force
        max_force = max(max_force, float(down_force))
        diagnostics.append({
            "contact": contact,
            "height_err": float(height_err),
            "down_force": float(down_force),
        })
    return qfrc, {"stance_preload": diagnostics, "stance_preload_max_force": max_force}


def apply_pose_qfrc_assist(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    variant: dict[str, Any],
    desired_fraction: float,
    phase_mode: str,
    support_health: float,
    zmp_health: float,
    slip_health: float,
    foot_contact_sensor_ids: list[int],
) -> tuple[np.ndarray, dict[str, float]]:
    qfrc = np.zeros(model.nv, dtype=np.float64)
    if variant["pose_qfrc_kp"] <= 0.0 or variant["pose_qfrc_clip"] <= 0.0 or phase_mode == "stand":
        return qfrc, {"pose_qfrc_max": 0.0, "pose_qfrc_scale": 0.0}
    contacts = [
        float(data.sensordata[model.sensor_adr[sensor_id]]) > 0.0
        for sensor_id in foot_contact_sensor_ids
    ]
    contact_health = 1.0 if all(contacts) else variant["pose_contact_loss_scale"]
    health = min(support_health, zmp_health, slip_health, contact_health)
    health_scale = float(np.clip(
        (health - variant["pose_qfrc_health_floor"]) / max(1e-6, 1.0 - variant["pose_qfrc_health_floor"]),
        0.0,
        1.0,
    ))
    if phase_mode == "recapture":
        phase_scale = variant["pose_qfrc_recapture_scale"] * min(1.0, max(0.0, desired_fraction))
    else:
        phase_scale = min(1.0, max(0.0, desired_fraction))
    scale = variant["pose_qfrc_scale"] * phase_scale * health_scale
    if scale <= 0.0:
        return qfrc, {"pose_qfrc_max": 0.0, "pose_qfrc_scale": 0.0}
    start = model.keyframe("knees_bent").qpos
    joint_specs = [
        ("left_knee_joint", variant["target_knee_delta"]),
        ("right_knee_joint", variant["target_knee_delta"]),
        ("left_hip_pitch_joint", -variant["target_hip_delta"]),
        ("right_hip_pitch_joint", -variant["target_hip_delta"]),
    ]
    max_tau = 0.0
    for name, signed_delta in joint_specs:
        qidx = EXP62.qpos_index(model, name)
        didx = EXP62.dof_index(model, name)
        desired_q = float(start[qidx] + signed_delta * phase_scale)
        tau = scale * (
            variant["pose_qfrc_kp"] * (desired_q - float(data.qpos[qidx]))
            - variant["pose_qfrc_kd"] * float(data.qvel[didx])
        )
        tau = float(np.clip(tau, -variant["pose_qfrc_clip"], variant["pose_qfrc_clip"]))
        qfrc[didx] += tau
        max_tau = max(max_tau, abs(tau))
    return qfrc, {"pose_qfrc_max": max_tau, "pose_qfrc_scale": float(scale)}


def phase_mode_and_progress(variant: dict[str, Any], return_phase: float) -> tuple[str, float]:
    if return_phase <= 0.0:
        return "descend", 0.0
    recapture_ratio = float(variant["recapture_s"]) / max(1e-6, float(variant["return_s"]))
    if return_phase < recapture_ratio:
        return "recapture", float(return_phase / max(1e-6, recapture_ratio))
    return "stand", float((return_phase - recapture_ratio) / max(1e-6, 1.0 - recapture_ratio))


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


def visible_gap(run: dict[str, Any]) -> dict[str, float]:
    return {
        "drop_shortfall_m": max(0.0, 0.08 - run["visible_drop"]),
        "knee_shortfall_rad": max(0.0, 0.60 - run["max_knee_delta_rad"]),
        "hip_shortfall_rad": max(0.0, 0.35 - run["max_hip_pitch_delta_rad"]),
        "slip_excess_m": max(0.0, run["foot_slip_distance"] - 0.08),
    }


def annotate_visible(run: dict[str, Any]) -> dict[str, Any]:
    run["visible_8cm_gate"] = visible_8cm_gate(run)
    run["visible_gap"] = visible_gap(run)
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


def multi_step_choose_blend(**kwargs):
    model = kwargs["model"]
    data = kwargs["data"]
    variant = kwargs["variant"]
    support_now = kwargs["support_now"]
    zmp_now = kwargs["zmp_now"]
    foot_slip_now = kwargs["foot_slip_now"]
    prev_blend = kwargs["prev_blend"]
    desired_fraction = kwargs["desired_fraction"]
    return_phase = kwargs["return_phase"]
    ctrl_dt = kwargs["ctrl_dt"]
    n_substeps = kwargs["n_substeps"]
    horizon_steps = int(variant.get("horizon_steps", 4))
    phase_mode, phase_progress = phase_mode_and_progress(variant, return_phase)
    variant = {**variant, "_phase_mode": phase_mode, "_phase_progress": phase_progress}

    support_health = float(np.clip((support_now["support_margin"] + 0.005) / 0.045, 0.0, 1.0))
    zmp_health = float(np.clip((zmp_now + 0.005) / 0.045, 0.0, 1.0))
    slip_health = float(np.clip(1.0 - foot_slip_now / 0.08, 0.0, 1.0))
    desired_blend = variant["max_blend"] * desired_fraction
    if phase_mode in {"recapture", "stand"}:
        raw = np.array([
            0.0,
            max(0.0, prev_blend - variant["fast_release"]),
            max(0.0, prev_blend - variant["slow_release"]),
            prev_blend,
            min(desired_blend, prev_blend + variant["small_hold"]),
        ])
    else:
        raw = np.array([
            0.35 * desired_blend,
            0.55 * desired_blend,
            0.75 * desired_blend,
            desired_blend,
            min(desired_blend, prev_blend + variant["descend_rate"]),
        ])
    blend_candidates = np.unique(np.round(np.clip(raw, 0.0, variant["max_blend"]), 5))
    best: dict[str, Any] | None = None
    for blend in blend_candidates:
        if phase_mode == "stand":
            policy_targets = return_policy_targets(kwargs["policy_targets"], variant, return_phase)
            ik_target = variant["default_pose"]
            build_blend = 0.0
            build_fraction = 0.0
            residual_scale = variant["return_residual_scale"]
        elif phase_mode == "recapture":
            policy_targets = kwargs["policy_targets"]
            ik_target = kwargs["ik_target"]
            build_blend = min(float(blend), variant["recapture_blend"])
            build_fraction = variant["recapture_fraction"]
            residual_scale = variant["recapture_residual_scale"]
        else:
            policy_targets = kwargs["policy_targets"]
            ik_target = kwargs["ik_target"]
            build_blend = float(blend)
            build_fraction = desired_fraction
            residual_scale = variant["residual_scale"]
        target = EXP62.build_target(
            model=model,
            default_pose=variant["default_pose"],
            policy_targets=policy_targets,
            ik_target=ik_target,
            blend=build_blend,
            residual_scale=residual_scale,
            desired_fraction=build_fraction,
            support_health=support_health,
            zmp_health=zmp_health,
            slip_health=slip_health,
            error_xy=kwargs["error_xy"],
        )
        target, pose_bias_terms = apply_pose_bias(
            model=model,
            target=target,
            variant=variant,
            desired_fraction=desired_fraction,
            return_phase=return_phase,
            support_health=support_health,
            zmp_health=zmp_health,
            slip_health=slip_health,
        )
        cand = EXP67.clone_data(model, data)
        cand.ctrl[:] = target
        safety_scale = min(1.0, support_health, zmp_health, slip_health)
        if phase_mode == "stand":
            safety_scale = max(variant["return_min_safety"], min(1.0, safety_scale + variant["return_safety_boost"]))
        elif phase_mode == "recapture":
            safety_scale = max(variant["recapture_min_safety"], min(1.0, safety_scale + variant["recapture_safety_boost"]))
        pd_qfrc, _ = EXP62.lower_pd_torque(
            model=model,
            data=cand,
            maps=kwargs["maps"],
            target_qpos=target,
            kp=variant["return_joint_kp"] if phase_mode == "stand" else variant["joint_kp"],
            kd=variant["return_joint_kd"] if phase_mode == "stand" else variant["joint_kd"],
            torque_clip=variant["return_torque_clip"] if phase_mode == "stand" else variant["torque_clip"],
            safety_scale=safety_scale,
        )
        stance_qfrc, _ = EXP62.apply_stance_force(
            model=model,
            data=cand,
            foot_site_ids=kwargs["foot_site_ids"],
            initial_foot_xyz=kwargs["initial_foot_xyz"],
            kp_xy=variant["foot_kp_xy"],
            kd_xy=variant["foot_kd_xy"],
            lift_force=variant["foot_lift_force"],
            force_clip=variant["foot_force_clip"],
        )
        preload_qfrc, preload_terms = apply_stance_preload(
            model=model,
            data=cand,
            foot_site_ids=kwargs["foot_site_ids"],
            initial_foot_xyz=kwargs["initial_foot_xyz"],
            foot_contact_sensor_ids=kwargs["foot_contact_sensor_ids"],
            preload_force=variant["preload_force"],
            height_kp=variant["preload_height_kp"],
            force_clip=variant["preload_force_clip"],
        )
        pose_qfrc, pose_qfrc_terms = apply_pose_qfrc_assist(
            model=model,
            data=cand,
            variant=variant,
            desired_fraction=desired_fraction,
            phase_mode=phase_mode,
            support_health=support_health,
            zmp_health=zmp_health,
            slip_health=slip_health,
            foot_contact_sensor_ids=kwargs["foot_contact_sensor_ids"],
        )
        qfrc = pd_qfrc + stance_qfrc + preload_qfrc + pose_qfrc
        cand.qfrc_applied[:] = qfrc

        min_support = float("inf")
        min_zmp = float("inf")
        max_slip = 0.0
        contact_loss_count = 0
        prev_com_xy = kwargs["prev_com_xy"].copy()
        prev_com_vel = kwargs["prev_com_vel"].copy()
        height_before = kwargs["height_before"]
        final_height = float(cand.qpos[2])
        for _ in range(max(1, horizon_steps)):
            for _ in range(n_substeps):
                mujoco.mj_step(model, cand)
            support = EXP37.support_metrics(model, cand, kwargs["foot_geom_ids"])
            com_xy, com_vel, zmp = EXP67.zmp_margin(
                model=model,
                data=cand,
                support=support,
                prev_com_xy=prev_com_xy,
                prev_com_vel=prev_com_vel,
                ctrl_dt=ctrl_dt,
            )
            contacts = [
                float(cand.sensordata[model.sensor_adr[sensor_id]]) > 0
                for sensor_id in kwargs["foot_contact_sensor_ids"]
            ]
            foot_slip = float(np.max(np.linalg.norm(
                cand.site_xpos[kwargs["foot_site_ids"], :2] - kwargs["initial_foot_xyz"][:, :2],
                axis=1,
            )))
            min_support = min(min_support, support["support_margin"])
            min_zmp = min(min_zmp, zmp)
            max_slip = max(max_slip, foot_slip)
            contact_loss_count += 0 if all(contacts) else 1
            prev_com_xy = com_xy.copy()
            prev_com_vel = com_vel.copy()
            final_height = float(cand.qpos[2])
        cand.qfrc_applied[:] = 0.0

        support = EXP37.support_metrics(model, cand, kwargs["foot_geom_ids"])
        _, _, zmp = EXP67.zmp_margin(
            model=model,
            data=cand,
            support=support,
            prev_com_xy=kwargs["prev_com_xy"],
            prev_com_vel=kwargs["prev_com_vel"],
            ctrl_dt=ctrl_dt,
        )
        target_fraction = max(0.0, desired_fraction - return_phase)
        pose = pose_delta(model, cand)
        pose_fraction = 0.0 if phase_mode == "stand" else min(1.0, max(0.0, desired_fraction))
        knee_shortfall = max(0.0, variant["target_knee_delta"] * pose_fraction - pose["knee"])
        hip_shortfall = max(0.0, variant["target_hip_delta"] * pose_fraction - pose["hip"])
        immediate_cost, terms = EXP67.score_candidate(
            model=model,
            cand=cand,
            start_height=kwargs["start_height"],
            target_fraction=target_fraction,
            variant=variant,
            support=support,
            zmp=zmp,
            foot_slip=max_slip,
            both_feet=contact_loss_count == 0,
            height_before=height_before,
            ctrl_dt=ctrl_dt,
            blend=float(blend),
            prev_blend=prev_blend,
            qfrc_max=float(np.max(np.abs(qfrc))),
        )
        horizon_cost = (
            variant["w_support"] * (variant["recapture_support_mult"] if phase_mode == "recapture" else 1.0) * max(0.0, variant["support_floor"] - min_support) ** 2
            + variant["w_zmp"] * (variant["recapture_zmp_mult"] if phase_mode == "recapture" else 1.0) * max(0.0, variant["zmp_floor"] - min_zmp) ** 2
            + variant["w_slip"] * (variant["recapture_slip_mult"] if phase_mode == "recapture" else 1.0) * max(0.0, max_slip - variant["slip_floor"]) ** 2
            + variant["w_contact"] * contact_loss_count
            + variant["w_depth_cap"] * max(0.0, kwargs["start_height"] - final_height - variant["depth_cap"]) ** 2
            + variant["w_recapture_height"] * max(0.0, abs((kwargs["start_height"] - final_height) - variant["recapture_drop"]) - variant["recapture_drop_band"]) ** 2 * (1.0 if phase_mode == "recapture" else 0.0)
            + variant["w_knee"] * knee_shortfall ** 2
            + variant["w_hip"] * hip_shortfall ** 2
            + variant["w_stand"] * max(0.0, variant["stand_height"] - final_height) ** 2 * max(0.0, return_phase)
            + variant["w_return_slip"] * max(0.0, max_slip - variant["return_slip_floor"]) ** 2 * max(0.0, return_phase)
        )
        cost = immediate_cost + float(variant.get("horizon_weight", 1.0)) * horizon_cost
        row = {
            "blend": float(blend),
            "cost": cost,
            "terms": terms,
            "horizon_cost": horizon_cost,
            "horizon_min_support": min_support,
            "horizon_min_zmp": min_zmp,
            "horizon_max_slip": max_slip,
            "horizon_contact_loss_count": contact_loss_count,
            "horizon_knee_delta": pose["knee"],
            "horizon_hip_delta": pose["hip"],
            "horizon_knee_shortfall": knee_shortfall,
            "horizon_hip_shortfall": hip_shortfall,
            "phase_mode": phase_mode,
            "phase_progress": phase_progress,
            **pose_bias_terms,
            "support_margin": support["support_margin"],
            "zmp_margin": zmp,
            "foot_slip_distance": max_slip,
            "height": final_height,
            "qfrc_max": float(np.max(np.abs(qfrc))),
            "stance_preload_max_force": preload_terms["stance_preload_max_force"],
            "pose_qfrc_max": pose_qfrc_terms["pose_qfrc_max"],
            "pose_qfrc_scale": pose_qfrc_terms["pose_qfrc_scale"],
            "target": target,
            "qfrc": qfrc,
        }
        if best is None or cost < best["cost"]:
            best = row
    assert best is not None
    chosen = {k: v for k, v in best.items() if k not in {"target", "qfrc"}}
    return best["target"], best["qfrc"], chosen


def optimizer_score(run: dict[str, Any]) -> float:
    gap = run["visible_gap"]
    score = 0.0
    score += 1000.0 if run["fell_at"] is not None else 0.0
    score += 260.0 * gap["drop_shortfall_m"] / 0.08
    score += 160.0 * gap["knee_shortfall_rad"] / 0.60
    score += 160.0 * gap["hip_shortfall_rad"] / 0.35
    score += 180.0 * gap["slip_excess_m"] / 0.08
    score += 180.0 * max(0.0, 0.90 - run["foot_contact_ratio"])
    score += 220.0 * max(0.0, 0.74 - run["final_height"])
    score += 80.0 * max(0.0, -run["min_support_margin"])
    score += 80.0 * max(0.0, -run["min_zmp_margin"])
    if not run["return_to_stand"]:
        score += 120.0
    if run["visible_8cm_gate"]:
        score -= 500.0
    return float(score)


def annotate_optimizer(run: dict[str, Any]) -> dict[str, Any]:
    run["optimizer_score"] = optimizer_score(run)
    run["optimizer_rank_basis"] = {
        "primary": "visible_8cm_gate",
        "penalties": [
            "fall",
            "drop_shortfall",
            "knee_shortfall",
            "hip_shortfall",
            "slip_excess",
            "contact_shortfall",
            "stand_return_shortfall",
            "support_zmp_negative_margin",
        ],
    }
    return run


def variants() -> list[dict[str, Any]]:
    common = {
        "policy_weight": 1.0,
        "joint_kd": 1.4,
        "foot_kd_xy": 22.0,
        "foot_lift_force": 180.0,
        "support_floor": 0.006,
        "zmp_floor": -0.020,
        "slip_floor": 0.055,
        "downward_floor": 0.10,
        "stand_height": 0.74,
        "height_floor": 0.62,
        "upright_floor": 0.82,
        "qfrc_soft_cap": 58.0,
        "return_safety_boost": 0.20,
        "return_min_safety": 0.55,
        "return_policy_weight": 0.05,
        "return_residual_scale": 0.0,
        "return_joint_kp": 38.0,
        "return_joint_kd": 2.0,
        "return_torque_clip": 56.0,
        "return_slip_floor": 0.065,
        "recapture_s": 1.2,
        "recapture_blend": 0.46,
        "recapture_fraction": 0.82,
        "recapture_residual_scale": 0.040,
        "recapture_min_safety": 0.72,
        "recapture_safety_boost": 0.32,
        "recapture_support_mult": 2.4,
        "recapture_zmp_mult": 2.4,
        "recapture_slip_mult": 2.6,
        "recapture_drop": 0.12,
        "recapture_drop_band": 0.035,
        "descend_rate": 0.040,
        "slow_release": 0.035,
        "fast_release": 0.090,
        "small_hold": 0.012,
        "w_height": 135.0,
        "w_stand": 150.0,
        "w_height_floor": 850.0,
        "w_upright": 620.0,
        "w_support": 4200.0,
        "w_zmp": 3200.0,
        "w_slip": 2800.0,
        "w_contact": 480.0,
        "w_downward": 160.0,
        "w_qfrc": 5.0,
        "w_smooth": 2.0,
        "w_knee": 44.0,
        "w_hip": 40.0,
        "w_return_slip": 6200.0,
        "w_recapture_height": 9000.0,
        "w_depth_cap": 1200.0,
        "depth_cap": 0.22,
        "horizon_weight": 1.1,
        "target_knee_delta": 0.60,
        "target_hip_delta": 0.35,
        "pose_start": 0.30,
        "pose_peak": 0.78,
        "pose_end": 1.02,
        "pose_health_floor": 0.25,
        "return_pose_scale": 0.25,
        "preload_force": 0.0,
        "preload_height_kp": 0.0,
        "preload_force_clip": 0.0,
        "pose_qfrc_scale": 0.0,
        "pose_qfrc_kp": 0.0,
        "pose_qfrc_kd": 1.2,
        "pose_qfrc_clip": 0.0,
        "pose_qfrc_health_floor": 0.18,
        "pose_qfrc_recapture_scale": 0.55,
        "pose_contact_loss_scale": 0.25,
    }
    teacher = {**common, "drop": 0.080, "joint_kp": 26.0, "torque_clip": 36.0, "foot_kp_xy": 500.0, "foot_force_clip": 380.0, "descend_s": 3.8, "recapture_s": 1.6, "return_s": 2.6, "horizon_steps": 9, "w_support": 9800.0, "w_slip": 8400.0, "w_stand": 880.0, "return_joint_kp": 46.0, "return_torque_clip": 66.0, "knee_amp": 0.08, "hip_bias": 0.14, "w_knee": 58.0, "w_hip": 320.0, "pose_health_floor": 0.16, "w_depth_cap": 22000.0, "recapture_drop": 0.10}
    return [
        {**teacher, "attempt": "baseline-exp90-contact", "max_blend": 0.505, "residual_scale": 0.060, "w_height": 118.0, "depth_cap": 0.18, "w_contact": 760.0, "w_slip": 11200.0, "w_stand": 1120.0, "return_s": 2.8, "preload_force": 35.0, "preload_height_kp": 600.0, "preload_force_clip": 110.0},
        {**teacher, "attempt": "plan-8cm-slip-tight", "max_blend": 0.492, "residual_scale": 0.052, "w_height": 116.0, "depth_cap": 0.105, "w_depth_cap": 85000.0, "w_contact": 1200.0, "w_slip": 26000.0, "w_knee": 260.0, "w_hip": 360.0, "foot_kp_xy": 620.0, "foot_force_clip": 470.0, "preload_force": 34.0, "preload_height_kp": 660.0, "preload_force_clip": 108.0, "knee_amp": 0.105, "hip_bias": 0.145, "pose_health_floor": 0.32, "descend_s": 4.2, "recapture_s": 1.9, "return_s": 3.1, "recapture_drop": 0.085},
        {**teacher, "attempt": "plan-8cm-knee-bias", "max_blend": 0.498, "residual_scale": 0.054, "w_height": 118.0, "depth_cap": 0.115, "w_depth_cap": 72000.0, "w_contact": 1100.0, "w_slip": 24000.0, "w_knee": 340.0, "w_hip": 360.0, "foot_kp_xy": 590.0, "foot_force_clip": 450.0, "preload_force": 34.0, "preload_height_kp": 640.0, "preload_force_clip": 110.0, "knee_amp": 0.120, "hip_bias": 0.140, "pose_health_floor": 0.36, "descend_s": 4.1, "recapture_s": 2.0, "return_s": 3.2, "recapture_drop": 0.090},
        {**teacher, "attempt": "plan-9cm-terminal", "max_blend": 0.500, "residual_scale": 0.052, "w_height": 120.0, "depth_cap": 0.120, "w_depth_cap": 90000.0, "w_contact": 1240.0, "w_slip": 27000.0, "w_stand": 1500.0, "w_knee": 300.0, "w_hip": 380.0, "return_joint_kp": 54.0, "return_torque_clip": 74.0, "foot_kp_xy": 610.0, "foot_force_clip": 470.0, "preload_force": 34.0, "preload_height_kp": 660.0, "preload_force_clip": 108.0, "knee_amp": 0.112, "hip_bias": 0.150, "pose_health_floor": 0.36, "descend_s": 4.3, "recapture_s": 2.1, "return_s": 3.3, "recapture_drop": 0.090},
        {**teacher, "attempt": "plan-low-residual-long-horizon", "max_blend": 0.486, "residual_scale": 0.046, "w_height": 112.0, "depth_cap": 0.100, "w_depth_cap": 100000.0, "w_contact": 1320.0, "w_slip": 30000.0, "w_knee": 360.0, "w_hip": 420.0, "horizon_steps": 12, "foot_kp_xy": 640.0, "foot_force_clip": 490.0, "preload_force": 32.0, "preload_height_kp": 680.0, "preload_force_clip": 104.0, "knee_amp": 0.125, "hip_bias": 0.135, "pose_health_floor": 0.42, "descend_s": 4.5, "recapture_s": 2.2, "return_s": 3.4, "recapture_drop": 0.080},
        {**teacher, "attempt": "plan-light-pose-qfrc", "max_blend": 0.492, "residual_scale": 0.050, "w_height": 114.0, "depth_cap": 0.105, "w_depth_cap": 95000.0, "w_contact": 1300.0, "w_slip": 29000.0, "w_knee": 360.0, "w_hip": 420.0, "foot_kp_xy": 620.0, "foot_force_clip": 480.0, "preload_force": 33.0, "preload_height_kp": 660.0, "preload_force_clip": 106.0, "knee_amp": 0.105, "hip_bias": 0.145, "pose_health_floor": 0.40, "pose_qfrc_scale": 0.25, "pose_qfrc_kp": 22.0, "pose_qfrc_clip": 8.0, "pose_qfrc_health_floor": 0.55, "descend_s": 4.4, "recapture_s": 2.1, "return_s": 3.3, "recapture_drop": 0.085},
        {**teacher, "attempt": "plan-terminal-micro-qfrc", "max_blend": 0.498, "residual_scale": 0.052, "w_height": 118.0, "depth_cap": 0.112, "w_depth_cap": 98000.0, "w_contact": 1350.0, "w_slip": 33000.0, "w_stand": 1700.0, "w_knee": 430.0, "w_hip": 430.0, "return_joint_kp": 56.0, "return_torque_clip": 76.0, "foot_kp_xy": 640.0, "foot_force_clip": 500.0, "preload_force": 32.0, "preload_height_kp": 690.0, "preload_force_clip": 104.0, "knee_amp": 0.120, "hip_bias": 0.150, "pose_health_floor": 0.45, "pose_qfrc_scale": 0.10, "pose_qfrc_kp": 18.0, "pose_qfrc_clip": 4.0, "pose_qfrc_health_floor": 0.65, "descend_s": 4.4, "recapture_s": 2.2, "return_s": 3.4, "recapture_drop": 0.085},
        {**teacher, "attempt": "plan-terminal-narrow-qfrc", "max_blend": 0.496, "residual_scale": 0.050, "w_height": 116.0, "depth_cap": 0.105, "w_depth_cap": 110000.0, "w_contact": 1420.0, "w_slip": 36000.0, "w_stand": 1800.0, "w_knee": 460.0, "w_hip": 440.0, "return_joint_kp": 56.0, "return_torque_clip": 76.0, "foot_kp_xy": 660.0, "foot_force_clip": 510.0, "preload_force": 31.0, "preload_height_kp": 700.0, "preload_force_clip": 102.0, "knee_amp": 0.128, "hip_bias": 0.150, "pose_health_floor": 0.50, "pose_qfrc_scale": 0.16, "pose_qfrc_kp": 18.0, "pose_qfrc_clip": 5.0, "pose_qfrc_health_floor": 0.72, "descend_s": 4.5, "recapture_s": 2.2, "return_s": 3.5, "recapture_drop": 0.080},
    ]


def write_summary(result: dict[str, Any], out_dir: Path) -> None:
    lines = [
        "# G1 Finite-Horizon Trajectory Optimizer Summary",
        "",
        "| Rank | Attempt | Score | Visible gate | Verdict | Drop | Knee | Hip | Contact | Slip | Final h | Fell |",
        "|---:|---|---:|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for rank, run in enumerate(sorted(result["runs"], key=lambda item: item["optimizer_score"]), start=1):
        fell = "never" if run["fell_at"] is None else f"{run['fell_at']:.2f}s"
        gate = "PASS" if run["visible_8cm_gate"] else "FAIL"
        lines.append(
            f"| {rank} | {run['attempt']} | {run['optimizer_score']:.1f} | {gate} | {run['visible_verdict']} | "
            f"{run['visible_drop']:.4f}m | {run['max_knee_delta_rad']:.3f} | "
            f"{run['max_hip_pitch_delta_rad']:.3f} | {run['foot_contact_ratio']:.2f} | "
            f"{run['foot_slip_distance']:.3f}m | {run['final_height']:.4f}m | {fell} |"
        )
    lines.extend([
        "",
        f"Best optimizer run: {result['best_optimizer']}",
        f"Best visible run: {result['best_visible']}",
        f"Best no-fall run: {result['best_no_fall']}",
        f"Best depth run: {result['best_depth']}",
        "",
        "M19 closes only when visible native and browser replay both pass.",
    ])
    (out_dir / "finite-horizon-trajectory-optimizer-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=6.0)
    args = parser.parse_args()
    out_dir = VERIFY / "finite-horizon-trajectory-optimizer"
    out_dir.mkdir(parents=True, exist_ok=True)
    EXP67.choose_blend = multi_step_choose_blend
    result = {
        "evaluation_seconds": args.seconds,
        "planning_gate": {
            "team_validation_mode": "manual-pass",
                "spec_delta": "M19 tests finite-horizon trajectory plan candidates around the exp90/91 contact-safe branch before attempting browser replay.",
            "perspectives": {
                "product": "tests whether planning the full down-recapture-stand trajectory can close the visible squat native gate",
                "architecture": "keeps exp87's 3-phase teacher and evaluates full-rollout trajectory plans over depth cap, timing, pose bias, stance preload, and slip costs",
                "security": "no credentials or external side effects",
                "qa": "native sweep records raw JSON, visible gate metrics, trajectory candidates, and optimizer score per full rollout",
                "skeptic": "a coarse hand-built plan grid may still only rediscover the exp90/91 local optimum",
            },
            "dod": [
                "raw native JSON per finite-horizon trajectory plan",
                "summary ranks variants and states whether any variant passes visible_8cm_gate",
            ],
        },
        "sources": [
            {
                "url": "https://robotsguide.com/robots/unitree-g1",
                "accessed": "2026-06-18",
                "note": "IEEE Robots Guide shows Unitree G1 in a deep squat-like pose, supporting kinematic plausibility before dynamics testing.",
            },
            {
                "url": "https://www.mdpi.com/1424-8220/25/2/435",
                "accessed": "2026-06-18",
                "note": "Humanoid squat research frames squatting as a whole-body coordination task requiring foot-force and dynamic constraints.",
            },
            {
                "url": "https://arxiv.org/html/2506.05115v1",
                "accessed": "2026-06-18",
                "note": "Whole-body constrained learning motivates adding contact and foot-terrain constraints in a low-level whole-body follower instead of reward-only tuning.",
            },
            {
                "url": "https://arxiv.org/html/2503.04613v2",
                "accessed": "2026-06-18",
                "note": "MuJoCo whole-body MPC work supports using simulator dynamics and contact modeling for legged whole-body control experiments.",
            },
            {
                "url": "https://github.com/google-deepmind/mujoco_mpc",
                "accessed": "2026-06-18",
                "note": "MuJoCo MPC supports multiple shooting and predictive sampling style planners, motivating a finite-horizon native rollout search.",
            },
        ],
        "runs": [],
    }
    for variant in variants():
        run = EXP67.native_eval(
            variant=variant,
            seconds=args.seconds,
            out_dir=out_dir / variant["attempt"],
        )
        result["runs"].append(annotate_optimizer(annotate_visible(run)))
    visible = [run for run in result["runs"] if run["visible_8cm_gate"]]
    no_fall = [run for run in result["runs"] if run["fell_at"] is None]
    best_visible = max(visible, key=lambda run: run["visible_drop"], default=None)
    best_no_fall = max(no_fall, key=lambda run: run["visible_drop"], default=None)
    best_depth = max(result["runs"], key=lambda run: run["visible_drop"])
    best_optimizer = min(result["runs"], key=lambda run: run["optimizer_score"])
    result["best_optimizer"] = {
        "attempt": best_optimizer["attempt"],
        "optimizer_score": best_optimizer["optimizer_score"],
        "visible_drop": best_optimizer["visible_drop"],
        "max_knee_delta_rad": best_optimizer["max_knee_delta_rad"],
        "max_hip_pitch_delta_rad": best_optimizer["max_hip_pitch_delta_rad"],
        "visible_gap": best_optimizer["visible_gap"],
        "visible_verdict": best_optimizer["visible_verdict"],
        "fell_at": best_optimizer["fell_at"],
    }
    result["best_visible"] = None if best_visible is None else {
        "attempt": best_visible["attempt"],
        "visible_drop": best_visible["visible_drop"],
        "max_knee_delta_rad": best_visible["max_knee_delta_rad"],
        "max_hip_pitch_delta_rad": best_visible["max_hip_pitch_delta_rad"],
    }
    result["best_no_fall"] = None if best_no_fall is None else {
        "attempt": best_no_fall["attempt"],
        "visible_drop": best_no_fall["visible_drop"],
        "max_knee_delta_rad": best_no_fall["max_knee_delta_rad"],
        "max_hip_pitch_delta_rad": best_no_fall["max_hip_pitch_delta_rad"],
        "visible_gap": best_no_fall["visible_gap"],
        "visible_verdict": best_no_fall["visible_verdict"],
    }
    result["best_depth"] = {
        "attempt": best_depth["attempt"],
        "visible_drop": best_depth["visible_drop"],
        "fell_at": best_depth["fell_at"],
        "visible_verdict": best_depth["visible_verdict"],
    }
    result["verdict"] = "PASS_VISIBLE_8CM_GATE" if visible else "FAIL_VISIBLE_8CM_GATE"
    write_summary(result, out_dir)
    (out_dir / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(result["verdict"], json.dumps({
        "best_optimizer": result["best_optimizer"],
        "best_visible": result["best_visible"],
        "best_no_fall": result["best_no_fall"],
        "best_depth": result["best_depth"],
    }, indent=2), flush=True)


if __name__ == "__main__":
    main()
