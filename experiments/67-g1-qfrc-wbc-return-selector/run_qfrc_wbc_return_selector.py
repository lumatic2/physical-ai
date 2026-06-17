"""Probe qfrc-assisted WBC/QP-lite return selector for G1 squat."""

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
EXP62_PATH = ROOT / "experiments/62-g1-actuator-contact-wbc-probe/run_actuator_contact_wbc_probe.py"
G = 9.81


def load_exp62():
    spec = importlib.util.spec_from_file_location("exp62_actuator_contact", EXP62_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {EXP62_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EXP62 = load_exp62()
EXP28 = EXP62.EXP28
EXP52 = EXP62.EXP52
EXP36 = EXP62.EXP36
EXP37 = EXP62.EXP37
EXP42 = EXP62.EXP42
EXP60 = EXP62.EXP60
POSE_JOINTS = EXP62.POSE_JOINTS


def clone_data(model: mujoco.MjModel, data: mujoco.MjData) -> mujoco.MjData:
    cand = mujoco.MjData(model)
    cand.time = data.time
    cand.qpos[:] = data.qpos
    cand.qvel[:] = data.qvel
    cand.act[:] = data.act
    cand.ctrl[:] = data.ctrl
    cand.qfrc_applied[:] = data.qfrc_applied
    mujoco.mj_forward(model, cand)
    return cand


def zmp_margin(
    *,
    model: mujoco.MjModel,
    data: mujoco.MjData,
    support: dict[str, Any],
    prev_com_xy: np.ndarray,
    prev_com_vel: np.ndarray,
    ctrl_dt: float,
) -> tuple[np.ndarray, np.ndarray, float]:
    com_xy = data.subtree_com[0, :2].copy()
    com_vel = (com_xy - prev_com_xy) / ctrl_dt
    com_acc = (com_vel - prev_com_vel) / ctrl_dt
    com_z = max(float(data.subtree_com[0, 2]), 0.05)
    zmp_xy = com_xy - (com_z / G) * com_acc
    return com_xy, com_vel, EXP60.support_margin_for_point(zmp_xy, support)


def recoverable_7cm_gate(run: dict[str, Any]) -> bool:
    return (
        run["fell_at"] is None
        and run["visible_drop"] >= 0.07
        and run["return_to_stand"]
        and run["foot_contact_ratio"] >= 0.90
        and run["foot_slip_distance"] <= 0.08
        and run["max_joint_limit_violation"] <= 0.05
    )


def annotate(run: dict[str, Any]) -> dict[str, Any]:
    run["recoverable_7cm_gate"] = recoverable_7cm_gate(run)
    if run["recoverable_7cm_gate"]:
        run["transition_verdict"] = "PASS_RECOVERABLE_7CM_GATE"
    elif run["fell_at"] is not None:
        run["transition_verdict"] = "FAIL_FALL"
    elif run["visible_drop"] < 0.07:
        run["transition_verdict"] = "DEPTH_PENDING_7CM"
    elif not run["return_to_stand"]:
        run["transition_verdict"] = "RETURN_PENDING"
    elif run["foot_contact_ratio"] < 0.90:
        run["transition_verdict"] = "CONTACT_PENDING"
    elif run["foot_slip_distance"] > 0.08:
        run["transition_verdict"] = "STANCE_SLIP_PENDING"
    else:
        run["transition_verdict"] = "GATE_PENDING"
    return run


def score_candidate(
    *,
    model: mujoco.MjModel,
    cand: mujoco.MjData,
    start_height: float,
    target_fraction: float,
    variant: dict[str, Any],
    support: dict[str, Any],
    zmp: float,
    foot_slip: float,
    both_feet: bool,
    height_before: float,
    ctrl_dt: float,
    blend: float,
    prev_blend: float,
    qfrc_max: float,
) -> tuple[float, dict[str, float]]:
    height = float(cand.qpos[2])
    quat = cand.qpos[3:7]
    mat = np.empty(9)
    mujoco.mju_quat2Mat(mat, quat)
    up_z = float(mat.reshape(3, 3)[2, 2])
    desired_height = start_height - variant["drop"] * target_fraction
    vertical_velocity = (height - height_before) / ctrl_dt
    support_breach = max(0.0, variant["support_floor"] - support["support_margin"])
    zmp_breach = max(0.0, variant["zmp_floor"] - zmp)
    slip_excess = max(0.0, foot_slip - variant["slip_floor"])
    contact_loss = 0.0 if both_feet else 1.0
    downward = max(0.0, -vertical_velocity - variant["downward_floor"])
    height_err = height - desired_height
    stand_err = max(0.0, variant["stand_height"] - height)
    floor_err = max(0.0, variant["height_floor"] - height)
    upright_err = max(0.0, variant["upright_floor"] - up_z)
    qfrc_excess = max(0.0, qfrc_max - variant["qfrc_soft_cap"]) / variant["qfrc_soft_cap"]
    smooth = blend - prev_blend
    terms = {
        "height": variant["w_height"] * height_err * height_err,
        "stand": variant["w_stand"] * stand_err * stand_err,
        "height_floor": variant["w_height_floor"] * floor_err * floor_err,
        "upright": variant["w_upright"] * upright_err * upright_err,
        "support": variant["w_support"] * support_breach * support_breach,
        "zmp": variant["w_zmp"] * zmp_breach * zmp_breach,
        "slip": variant["w_slip"] * slip_excess * slip_excess,
        "contact": variant["w_contact"] * contact_loss,
        "downward": variant["w_downward"] * downward * downward,
        "qfrc": variant["w_qfrc"] * qfrc_excess * qfrc_excess,
        "smooth": variant["w_smooth"] * smooth * smooth,
    }
    return float(sum(terms.values())), terms


def choose_blend(
    *,
    model: mujoco.MjModel,
    data: mujoco.MjData,
    maps: dict[str, dict[str, int]],
    policy_targets: np.ndarray,
    ik_target: np.ndarray,
    variant: dict[str, Any],
    prev_blend: float,
    desired_fraction: float,
    return_phase: float,
    support_now: dict[str, Any],
    zmp_now: float,
    foot_slip_now: float,
    error_xy: np.ndarray,
    foot_site_ids: np.ndarray,
    initial_foot_xyz: np.ndarray,
    prev_com_xy: np.ndarray,
    prev_com_vel: np.ndarray,
    height_before: float,
    start_height: float,
    ctrl_dt: float,
    n_substeps: int,
    foot_contact_sensor_ids: list[int],
    foot_geom_ids: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    support_health = float(np.clip((support_now["support_margin"] + 0.005) / 0.045, 0.0, 1.0))
    zmp_health = float(np.clip((zmp_now + 0.005) / 0.045, 0.0, 1.0))
    slip_health = float(np.clip(1.0 - foot_slip_now / 0.08, 0.0, 1.0))
    desired_blend = variant["max_blend"] * desired_fraction
    if return_phase > 0.0:
        raw = np.array([
            0.0,
            max(0.0, prev_blend - variant["fast_release"]),
            max(0.0, prev_blend - variant["slow_release"]),
            prev_blend,
            min(desired_blend, prev_blend + variant["small_hold"]),
        ])
    else:
        raw = np.array([
            0.0,
            0.50 * desired_blend,
            0.75 * desired_blend,
            desired_blend,
            min(desired_blend, prev_blend + variant["descend_rate"]),
        ])
    blend_candidates = np.unique(np.round(np.clip(raw, 0.0, variant["max_blend"]), 5))
    best: dict[str, Any] | None = None
    for blend in blend_candidates:
        target = EXP62.build_target(
            model=model,
            default_pose=variant["default_pose"],
            policy_targets=policy_targets,
            ik_target=ik_target,
            blend=float(blend),
            residual_scale=variant["residual_scale"],
            desired_fraction=desired_fraction,
            support_health=support_health,
            zmp_health=zmp_health,
            slip_health=slip_health,
            error_xy=error_xy,
        )
        cand = clone_data(model, data)
        cand.ctrl[:] = target
        safety_scale = min(1.0, support_health, zmp_health, slip_health)
        if return_phase > 0.0:
            safety_scale = max(variant["return_min_safety"], min(1.0, safety_scale + variant["return_safety_boost"]))
        pd_qfrc, _ = EXP62.lower_pd_torque(
            model=model,
            data=cand,
            maps=maps,
            target_qpos=target,
            kp=variant["joint_kp"],
            kd=variant["joint_kd"],
            torque_clip=variant["torque_clip"],
            safety_scale=safety_scale,
        )
        stance_qfrc, _ = EXP62.apply_stance_force(
            model=model,
            data=cand,
            foot_site_ids=foot_site_ids,
            initial_foot_xyz=initial_foot_xyz,
            kp_xy=variant["foot_kp_xy"],
            kd_xy=variant["foot_kd_xy"],
            lift_force=variant["foot_lift_force"],
            force_clip=variant["foot_force_clip"],
        )
        qfrc = pd_qfrc + stance_qfrc
        cand.qfrc_applied[:] = qfrc
        for _ in range(n_substeps):
            mujoco.mj_step(model, cand)
        cand.qfrc_applied[:] = 0.0
        support = EXP37.support_metrics(model, cand, foot_geom_ids)
        _, _, zmp = zmp_margin(
            model=model,
            data=cand,
            support=support,
            prev_com_xy=prev_com_xy,
            prev_com_vel=prev_com_vel,
            ctrl_dt=ctrl_dt,
        )
        contacts = [
            float(cand.sensordata[model.sensor_adr[sensor_id]]) > 0
            for sensor_id in foot_contact_sensor_ids
        ]
        foot_slip = float(np.max(np.linalg.norm(cand.site_xpos[foot_site_ids, :2] - initial_foot_xyz[:, :2], axis=1)))
        target_fraction = max(0.0, desired_fraction - return_phase)
        cost, terms = score_candidate(
            model=model,
            cand=cand,
            start_height=start_height,
            target_fraction=target_fraction,
            variant=variant,
            support=support,
            zmp=zmp,
            foot_slip=foot_slip,
            both_feet=all(contacts),
            height_before=height_before,
            ctrl_dt=ctrl_dt,
            blend=float(blend),
            prev_blend=prev_blend,
            qfrc_max=float(np.max(np.abs(qfrc))),
        )
        row = {
            "blend": float(blend),
            "cost": cost,
            "terms": terms,
            "support_margin": support["support_margin"],
            "zmp_margin": zmp,
            "foot_slip_distance": foot_slip,
            "height": float(cand.qpos[2]),
            "qfrc_max": float(np.max(np.abs(qfrc))),
            "target": target,
            "qfrc": qfrc,
        }
        if best is None or cost < best["cost"]:
            best = row
    assert best is not None
    chosen = {k: v for k, v in best.items() if k not in {"target", "qfrc"}}
    return best["target"], best["qfrc"], chosen


def native_eval(*, variant: dict[str, Any], seconds: float, out_dir: Path) -> dict[str, Any]:
    env = EXP28.ContactAwareSquat(
        stage_height=0.67,
        controller_blend=variant["max_blend"],
        freeze_phase=True,
        blend_schedule="squat",
        reference_scale=1.0,
        config_overrides={"impl": "jax"},
    )
    policy = EXP28.build_policy(env, EXP52.EXP46_PARAMS)
    model = env.mj_model
    maps = EXP62.joint_maps(model)
    data = mujoco.MjData(model)
    key = model.keyframe("knees_bent")
    data.qpos[:] = key.qpos
    default_pose = key.qpos[7:].astype(np.float32).copy()
    variant = {**variant, "default_pose": default_pose}
    data.ctrl[:] = default_pose
    mujoco.mj_forward(model, data)

    foot_site_ids = np.asarray(env._feet_site_id)
    foot_geom_ids = np.asarray([model.geom("left_foot").id, model.geom("right_foot").id])
    foot_contact_sensor_ids = list(env._feet_floor_found_sensor)
    initial_foot_xyz = data.site_xpos[foot_site_ids, :3].copy()
    ik = EXP36.solve_foot_fixed_target(model, key.qpos.copy(), foot_site_ids, variant["drop"])
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
    start_height = float(data.qpos[2])
    prev_height = start_height
    prev_com_xy = data.subtree_com[0, :2].copy()
    prev_com_vel = np.zeros(2, dtype=np.float64)
    start_qpos = data.qpos.copy()
    pose_indices = {name: EXP62.qpos_index(model, name) for name in POSE_JOINTS}
    prev_blend = 0.0

    min_height = start_height
    final_height = start_height
    fell_at = None
    first_7cm_at = None
    both_feet_contact_count = 0
    max_foot_slip = 0.0
    min_support_margin = float("inf")
    min_zmp_margin = float("inf")
    max_joint_violation = 0.0
    max_knee_delta = 0.0
    max_hip_delta = 0.0
    max_qfrc = 0.0
    max_lr_imbalance = 0.0
    samples = []

    for step in range(total_steps):
        t = step * ctrl_dt
        height = float(data.qpos[2])
        final_height = height
        min_height = min(min_height, height)
        support = EXP37.support_metrics(model, data, foot_geom_ids)
        center_xy = EXP60.support_center(support)
        com_xy, com_vel, zmp = zmp_margin(
            model=model,
            data=data,
            support=support,
            prev_com_xy=prev_com_xy,
            prev_com_vel=prev_com_vel,
            ctrl_dt=ctrl_dt,
        )
        error_xy = center_xy - com_xy
        contacts = [
            float(data.sensordata[model.sensor_adr[sensor_id]]) > 0
            for sensor_id in foot_contact_sensor_ids
        ]
        both_feet = all(contacts)
        both_feet_contact_count += int(both_feet)
        foot_slip = float(np.max(np.linalg.norm(data.site_xpos[foot_site_ids, :2] - initial_foot_xyz[:, :2], axis=1)))
        desired_fraction, return_phase = EXP60.phase_fraction(t, variant["descend_s"], 0.4, variant["return_s"])

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
        policy_targets = default_pose + variant["policy_weight"] * action_np * float(env._config.action_scale)

        target, qfrc, chosen = choose_blend(
            model=model,
            data=data,
            maps=maps,
            policy_targets=policy_targets,
            ik_target=ik_target,
            variant=variant,
            prev_blend=prev_blend,
            desired_fraction=desired_fraction,
            return_phase=return_phase,
            support_now=support,
            zmp_now=zmp,
            foot_slip_now=foot_slip,
            error_xy=error_xy,
            foot_site_ids=foot_site_ids,
            initial_foot_xyz=initial_foot_xyz,
            prev_com_xy=prev_com_xy,
            prev_com_vel=prev_com_vel,
            height_before=height,
            start_height=start_height,
            ctrl_dt=ctrl_dt,
            n_substeps=n_substeps,
            foot_contact_sensor_ids=foot_contact_sensor_ids,
            foot_geom_ids=foot_geom_ids,
        )
        data.ctrl[:] = target
        data.qfrc_applied[:] = qfrc
        max_qfrc = max(max_qfrc, float(np.max(np.abs(qfrc))))
        for _ in range(n_substeps):
            mujoco.mj_step(model, data)
        data.qfrc_applied[:] = 0.0
        last_action = action_np
        prev_blend = chosen["blend"]
        prev_height = height
        prev_com_xy = com_xy.copy()
        prev_com_vel = com_vel.copy()

        visible_drop_now = start_height - height
        if visible_drop_now >= 0.07 and first_7cm_at is None:
            first_7cm_at = round(t, 3)
        min_support_margin = min(min_support_margin, support["support_margin"])
        min_zmp_margin = min(min_zmp_margin, zmp)
        max_foot_slip = max(max_foot_slip, foot_slip)
        max_joint_violation = max(max_joint_violation, EXP28.joint_limit_violation(model, data))
        max_knee_delta = max(
            max_knee_delta,
            abs(float(data.qpos[pose_indices["left_knee_joint"]] - start_qpos[pose_indices["left_knee_joint"]])),
            abs(float(data.qpos[pose_indices["right_knee_joint"]] - start_qpos[pose_indices["right_knee_joint"]])),
        )
        max_hip_delta = max(
            max_hip_delta,
            abs(float(data.qpos[pose_indices["left_hip_pitch_joint"]] - start_qpos[pose_indices["left_hip_pitch_joint"]])),
            abs(float(data.qpos[pose_indices["right_hip_pitch_joint"]] - start_qpos[pose_indices["right_hip_pitch_joint"]])),
        )
        quat = data.qpos[3:7]
        mat = np.empty(9)
        mujoco.mju_quat2Mat(mat, quat)
        up_z = float(mat.reshape(3, 3)[2, 2])
        if (height < 0.45 or up_z < 0.30) and fell_at is None:
            fell_at = round(t, 3)
        wrench = EXP42.contact_wrench_summary(model, data)
        max_lr_imbalance = max(max_lr_imbalance, wrench["lr_normal_imbalance"])
        if step % max(1, int(0.2 / ctrl_dt)) == 0:
            samples.append({
                "t": round(t, 3),
                "height": height,
                "visible_drop": visible_drop_now,
                "desired_fraction": desired_fraction,
                "return_phase": return_phase,
                "selected_blend": chosen["blend"],
                "selected_cost": chosen["cost"],
                "support_margin": support["support_margin"],
                "zmp_margin": zmp,
                "both_feet_contact": both_feet,
                "foot_slip_distance": foot_slip,
                "qfrc_max": chosen["qfrc_max"],
                "candidate_height": chosen["height"],
                "candidate_support_margin": chosen["support_margin"],
                "candidate_zmp_margin": chosen["zmp_margin"],
                "knee_delta": max_knee_delta,
                "hip_delta": max_hip_delta,
                "up_z": up_z,
            })

    visible_drop = start_height - min_height
    foot_contact_ratio = both_feet_contact_count / max(1, total_steps)
    native = {
        "attempt": variant["attempt"],
        "variant": {k: v for k, v in variant.items() if k != "default_pose"},
        "ik": ik,
        "start_height": start_height,
        "min_height": min_height,
        "visible_drop": visible_drop,
        "first_7cm_at": first_7cm_at,
        "fell_at": fell_at,
        "final_height": final_height,
        "return_to_stand": final_height >= 0.74,
        "foot_contact_ratio": foot_contact_ratio,
        "foot_slip_distance": max_foot_slip,
        "min_support_margin": min_support_margin,
        "min_zmp_margin": min_zmp_margin,
        "max_joint_limit_violation": max_joint_violation,
        "max_knee_delta_rad": max_knee_delta,
        "max_hip_pitch_delta_rad": max_hip_delta,
        "max_qfrc_applied": max_qfrc,
        "max_lr_normal_imbalance": max_lr_imbalance,
        "samples": samples,
    }
    annotate(native)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "native-eval.json").write_text(json.dumps(native, indent=2), encoding="utf-8")
    return native


def write_summary(result: dict[str, Any], out_dir: Path) -> None:
    lines = [
        "# G1 QFRC WBC Return Selector Summary",
        "",
        "| Attempt | 7cm gate | Verdict | Drop | Contact | Slip | CoM min | ZMP min | qfrc | Final h | Fell |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for run in result["runs"]:
        fell = "never" if run["fell_at"] is None else f"{run['fell_at']:.2f}s"
        gate = "PASS" if run["recoverable_7cm_gate"] else "FAIL"
        lines.append(
            f"| {run['attempt']} | {gate} | {run['transition_verdict']} | "
            f"{run['visible_drop']:.4f}m | {run['foot_contact_ratio']:.2f} | "
            f"{run['foot_slip_distance']:.3f}m | {run['min_support_margin']:.4f}m | "
            f"{run['min_zmp_margin']:.4f}m | {run['max_qfrc_applied']:.1f} | "
            f"{run['final_height']:.4f}m | {fell} |"
        )
    lines.extend([
        "",
        f"Best recoverable run: {result['best_recoverable']}",
        f"Best no-fall run: {result['best_no_fall']}",
        f"Best depth run: {result['best_depth']}",
        "",
        "This is an intermediate 7cm recoverable gate. M19 still requires the exp29 8cm visible native/browser gate.",
    ])
    (out_dir / "qfrc-wbc-return-selector-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=6.0)
    args = parser.parse_args()
    out_dir = VERIFY / "qfrc-wbc-return-selector"
    out_dir.mkdir(parents=True, exist_ok=True)
    common = {
        "policy_weight": 1.0,
        "joint_kd": 1.2,
        "foot_kp_xy": 0.0,
        "foot_force_clip": 0.0,
        "foot_kd_xy": 12.0,
        "foot_lift_force": 120.0,
        "support_floor": 0.006,
        "zmp_floor": -0.040,
        "slip_floor": 0.070,
        "downward_floor": 0.12,
        "stand_height": 0.74,
        "height_floor": 0.60,
        "upright_floor": 0.78,
        "qfrc_soft_cap": 45.0,
        "return_safety_boost": 0.12,
        "return_min_safety": 0.35,
        "descend_rate": 0.045,
        "slow_release": 0.035,
        "fast_release": 0.090,
        "small_hold": 0.015,
        "w_height": 120.0,
        "w_stand": 30.0,
        "w_height_floor": 450.0,
        "w_upright": 240.0,
        "w_support": 1600.0,
        "w_zmp": 1000.0,
        "w_slip": 700.0,
        "w_contact": 180.0,
        "w_downward": 90.0,
        "w_qfrc": 4.0,
        "w_smooth": 1.2,
    }
    variants = [
        {"attempt": "selector-8cm-r0p065-t24", "drop": 0.080, "max_blend": 0.51, "residual_scale": 0.065, "joint_kp": 20.0, "torque_clip": 24.0, "descend_s": 4.2, "return_s": 1.8, **common},
        {"attempt": "selector-8p2cm-r0p068-t26", "drop": 0.082, "max_blend": 0.52, "residual_scale": 0.068, "joint_kp": 21.0, "torque_clip": 26.0, "descend_s": 4.1, "return_s": 1.8, **common},
        {"attempt": "selector-8p5cm-r0p068-t26", "drop": 0.085, "max_blend": 0.52, "residual_scale": 0.068, "joint_kp": 21.0, "torque_clip": 26.0, "descend_s": 4.3, "return_s": 1.8, **common},
        {"attempt": "selector-8p5cm-r0p070-t28", "drop": 0.085, "max_blend": 0.53, "residual_scale": 0.070, "joint_kp": 22.0, "torque_clip": 28.0, "descend_s": 4.3, "return_s": 1.7, **common},
        {**common, "attempt": "selector-8p2cm-return-biased", "drop": 0.082, "max_blend": 0.52, "residual_scale": 0.068, "joint_kp": 21.0, "torque_clip": 26.0, "descend_s": 4.0, "return_s": 1.6, "w_stand": 90.0, "w_height": 80.0},
        {**common, "attempt": "selector-8cm-early-strong-return", "drop": 0.080, "max_blend": 0.51, "residual_scale": 0.065, "joint_kp": 22.0, "torque_clip": 30.0, "descend_s": 3.5, "return_s": 2.1, "w_stand": 180.0, "w_height": 65.0, "w_height_floor": 900.0, "w_upright": 520.0, "return_min_safety": 0.55, "fast_release": 0.13, "slow_release": 0.06},
        {**common, "attempt": "selector-8p2cm-early-strong-return", "drop": 0.082, "max_blend": 0.52, "residual_scale": 0.068, "joint_kp": 23.0, "torque_clip": 32.0, "descend_s": 3.6, "return_s": 2.0, "w_stand": 180.0, "w_height": 70.0, "w_height_floor": 900.0, "w_upright": 520.0, "return_min_safety": 0.55, "fast_release": 0.13, "slow_release": 0.06},
    ]
    result = {
        "evaluation_seconds": args.seconds,
        "planning_gate": {
            "team_validation_mode": "manual-pass",
            "spec_delta": "M19 moves from scalar return clamps to a qfrc-assisted WBC/QP-lite selector over candidate next targets.",
            "perspectives": {
                "product": "targets the exact 7cm recoverable gate blocking visible squat",
                "architecture": "combines exp62 qfrc assistance with one-step candidate rollout and support/ZMP/contact/slip costs",
                "security": "no credentials or external side effects",
                "qa": "native sweep records raw JSON, contact, slip, support/ZMP, qfrc, return, and fall",
                "skeptic": "one-step scoring may still miss delayed whole-body collapse and remain an approximation of real WBC/QP",
            },
            "dod": [
                "raw native JSON per selector variant",
                "summary states whether any variant passes recoverable_7cm_gate",
            ],
        },
        "sources": [
            {
                "url": "https://www.mdpi.com/1424-8220/25/2/435",
                "accessed": "2026-06-18",
                "note": "Humanoid squat framed as trajectory optimization plus WBC.",
            },
            {
                "url": "https://arxiv.org/html/2505.19540v1",
                "accessed": "2026-06-18",
                "note": "WB-MPC/WBC uses ZMP tracking relative to support constraints.",
            },
            {
                "url": "https://www.lirmm.fr/krut/pdf/2014_galdeano_ssd-0568454426/2014_galdeano_ssd.pdf",
                "accessed": "2026-06-18",
                "note": "Task-based WBC adds ZMP regulation and joint-limit avoidance.",
            },
        ],
        "runs": [],
    }
    for variant in variants:
        result["runs"].append(native_eval(
            variant=variant,
            seconds=args.seconds,
            out_dir=out_dir / variant["attempt"],
        ))
    recoverable = [run for run in result["runs"] if run["recoverable_7cm_gate"]]
    no_fall = [run for run in result["runs"] if run["fell_at"] is None]
    best_recoverable = max(recoverable, key=lambda run: run["visible_drop"], default=None)
    best_no_fall = max(no_fall, key=lambda run: run["visible_drop"], default=None)
    best_depth = max(result["runs"], key=lambda run: run["visible_drop"])
    result["best_recoverable"] = None if best_recoverable is None else {
        "attempt": best_recoverable["attempt"],
        "visible_drop": best_recoverable["visible_drop"],
        "return_to_stand": best_recoverable["return_to_stand"],
    }
    result["best_no_fall"] = None if best_no_fall is None else {
        "attempt": best_no_fall["attempt"],
        "visible_drop": best_no_fall["visible_drop"],
        "transition_verdict": best_no_fall["transition_verdict"],
        "final_height": best_no_fall["final_height"],
    }
    result["best_depth"] = {
        "attempt": best_depth["attempt"],
        "visible_drop": best_depth["visible_drop"],
        "fell_at": best_depth["fell_at"],
        "transition_verdict": best_depth["transition_verdict"],
    }
    result["verdict"] = "PASS_RECOVERABLE_7CM_GATE" if recoverable else "FAIL_RECOVERABLE_7CM_GATE"
    write_summary(result, out_dir)
    (out_dir / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(result["verdict"], json.dumps({
        "best_recoverable": result["best_recoverable"],
        "best_no_fall": result["best_no_fall"],
        "best_depth": result["best_depth"],
    }, indent=2), flush=True)


if __name__ == "__main__":
    main()
