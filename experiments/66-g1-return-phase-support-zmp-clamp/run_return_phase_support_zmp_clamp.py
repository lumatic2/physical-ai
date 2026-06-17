"""Probe return-phase support/ZMP clamp for the G1 squat corridor."""

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


def select_return_blend(
    *,
    blend_state: float,
    ctrl_dt: float,
    variant: dict[str, Any],
    support_margin: float,
    zmp_margin: float,
    foot_slip: float,
    vertical_velocity: float,
) -> tuple[float, str]:
    healthy = (
        support_margin >= variant["support_floor"]
        and zmp_margin >= variant["zmp_floor"]
        and foot_slip <= variant["slip_floor"]
        and vertical_velocity >= variant["vv_floor"]
    )
    if healthy:
        return max(0.0, blend_state - variant["return_rate"] * ctrl_dt), "release"
    if support_margin < variant["panic_support_floor"] or zmp_margin < variant["panic_zmp_floor"]:
        return max(variant["panic_hold_blend"], blend_state - variant["panic_rate"] * ctrl_dt), "panic_release"
    return max(variant["hold_blend"], blend_state - variant["clamped_rate"] * ctrl_dt), "clamped"


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
    previous_height = start_height
    previous_com_xy = data.subtree_com[0, :2].copy()
    previous_com_vel = np.zeros(2, dtype=np.float64)
    start_qpos = data.qpos.copy()
    pose_indices = {name: EXP62.qpos_index(model, name) for name in POSE_JOINTS}
    blend_state = 0.0

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
    max_pd_torque = 0.0
    max_applied_force = 0.0
    max_inverse_torque = 0.0
    max_inverse_gap = 0.0
    max_lr_imbalance = 0.0
    clamp_counts = {"release": 0, "clamped": 0, "panic_release": 0, "descend": 0}
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
        previous_com_xy = com_xy.copy()
        previous_com_vel = com_vel.copy()
        com_z = max(float(data.subtree_com[0, 2]), 0.05)
        zmp_xy = com_xy - (com_z / G) * com_acc
        zmp_margin = EXP60.support_margin_for_point(zmp_xy, support)
        error_xy = center_xy - com_xy
        contacts = [
            float(data.sensordata[model.sensor_adr[sensor_id]]) > 0
            for sensor_id in foot_contact_sensor_ids
        ]
        both_feet = all(contacts)
        both_feet_contact_count += int(both_feet)
        foot_slip = float(np.max(np.linalg.norm(data.site_xpos[foot_site_ids, :2] - initial_foot_xyz[:, :2], axis=1)))
        support_health = float(np.clip((support["support_margin"] + 0.005) / 0.045, 0.0, 1.0))
        zmp_health = float(np.clip((zmp_margin + 0.005) / 0.045, 0.0, 1.0))
        slip_health = float(np.clip(1.0 - foot_slip / 0.08, 0.0, 1.0))
        desired_fraction, return_phase = EXP60.phase_fraction(t, variant["descend_s"], 0.4, variant["return_s"])
        if return_phase <= 0.0:
            blend_state = variant["max_blend"] * desired_fraction
            clamp_mode = "descend"
        else:
            blend_state, clamp_mode = select_return_blend(
                blend_state=blend_state,
                ctrl_dt=ctrl_dt,
                variant=variant,
                support_margin=support["support_margin"],
                zmp_margin=zmp_margin,
                foot_slip=foot_slip,
                vertical_velocity=vertical_velocity,
            )
        clamp_counts[clamp_mode] += 1

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
        target = EXP62.build_target(
            model=model,
            default_pose=default_pose,
            policy_targets=policy_targets,
            ik_target=ik_target,
            blend=blend_state,
            residual_scale=variant["residual_scale"],
            desired_fraction=desired_fraction,
            support_health=support_health,
            zmp_health=zmp_health,
            slip_health=slip_health,
            error_xy=error_xy,
        )
        data.ctrl[:] = target
        data.qfrc_applied[:] = 0.0
        safety_scale = min(1.0, support_health, zmp_health, slip_health)
        if return_phase > 0.0 and clamp_mode == "release":
            safety_scale = min(1.0, safety_scale + variant["return_safety_boost"])
        pd_qfrc, pd_max = EXP62.lower_pd_torque(
            model=model,
            data=data,
            maps=maps,
            target_qpos=target,
            kp=variant["joint_kp"],
            kd=variant["joint_kd"],
            torque_clip=variant["torque_clip"],
            safety_scale=safety_scale,
        )
        stance_qfrc, stance_diag = EXP62.apply_stance_force(
            model=model,
            data=data,
            foot_site_ids=foot_site_ids,
            initial_foot_xyz=initial_foot_xyz,
            kp_xy=variant["foot_kp_xy"],
            kd_xy=variant["foot_kd_xy"],
            lift_force=variant["foot_lift_force"],
            force_clip=variant["foot_force_clip"],
        )
        data.qfrc_applied[:] = pd_qfrc + stance_qfrc
        max_pd_torque = max(max_pd_torque, pd_max)
        max_applied_force = max(max_applied_force, float(np.max(np.abs(data.qfrc_applied))))
        for _ in range(n_substeps):
            mujoco.mj_step(model, data)
        data.qfrc_applied[:] = 0.0
        last_action = action_np

        visible_drop_now = start_height - height
        if visible_drop_now >= 0.07 and first_7cm_at is None:
            first_7cm_at = round(t, 3)
        min_support_margin = min(min_support_margin, support["support_margin"])
        min_zmp_margin = min(min_zmp_margin, zmp_margin)
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
        inv = EXP42.inverse_summary(model, EXP42.clone_data(model, data) if hasattr(EXP42, "clone_data") else data)
        max_inverse_torque = max(max_inverse_torque, inv["lower_inverse_linf"])
        max_inverse_gap = max(max_inverse_gap, inv["qfrc_inverse_minus_actuator_linf"])
        max_lr_imbalance = max(max_lr_imbalance, wrench["lr_normal_imbalance"])

        if step % max(1, int(0.2 / ctrl_dt)) == 0:
            samples.append({
                "t": round(t, 3),
                "height": height,
                "visible_drop": visible_drop_now,
                "blend": blend_state,
                "clamp_mode": clamp_mode,
                "support_margin": support["support_margin"],
                "zmp_margin": zmp_margin,
                "both_feet_contact": both_feet,
                "foot_slip_distance": foot_slip,
                "vertical_velocity": vertical_velocity,
                "safety_scale": safety_scale,
                "pd_torque_max": pd_max,
                "qfrc_applied_max": float(np.max(np.abs(data.qfrc_applied))),
                "stance_force": stance_diag,
                "knee_delta": max_knee_delta,
                "hip_delta": max_hip_delta,
                "up_z": up_z,
            })

    visible_drop = start_height - min_height
    foot_contact_ratio = both_feet_contact_count / max(1, total_steps)
    native = {
        "attempt": variant["attempt"],
        "variant": variant,
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
        "max_pd_torque": max_pd_torque,
        "max_qfrc_applied": max_applied_force,
        "max_lower_inverse_torque": max_inverse_torque,
        "max_inverse_minus_actuator": max_inverse_gap,
        "max_lr_normal_imbalance": max_lr_imbalance,
        "clamp_counts": clamp_counts,
        "samples": samples,
    }
    annotate(native)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "native-eval.json").write_text(json.dumps(native, indent=2), encoding="utf-8")
    return native


def write_summary(result: dict[str, Any], out_dir: Path) -> None:
    lines = [
        "# G1 Return Phase Support/ZMP Clamp Summary",
        "",
        "| Attempt | 7cm gate | Verdict | Drop | Contact | Slip | CoM min | ZMP min | Final h | Clamp | Fell |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for run in result["runs"]:
        fell = "never" if run["fell_at"] is None else f"{run['fell_at']:.2f}s"
        gate = "PASS" if run["recoverable_7cm_gate"] else "FAIL"
        clamp = ",".join(f"{k}:{v}" for k, v in run["clamp_counts"].items() if v)
        lines.append(
            f"| {run['attempt']} | {gate} | {run['transition_verdict']} | "
            f"{run['visible_drop']:.4f}m | {run['foot_contact_ratio']:.2f} | "
            f"{run['foot_slip_distance']:.3f}m | {run['min_support_margin']:.4f}m | "
            f"{run['min_zmp_margin']:.4f}m | {run['final_height']:.4f}m | {clamp} | {fell} |"
        )
    lines.extend([
        "",
        f"Best recoverable run: {result['best_recoverable']}",
        f"Best no-fall run: {result['best_no_fall']}",
        f"Best depth run: {result['best_depth']}",
        "",
        "This is still an intermediate 7cm corridor gate, not the full M19 exp29 8cm native/browser gate.",
    ])
    (out_dir / "return-phase-support-zmp-clamp-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=6.0)
    args = parser.parse_args()
    out_dir = VERIFY / "return-phase-support-zmp-clamp"
    out_dir.mkdir(parents=True, exist_ok=True)

    common = {
        "policy_weight": 1.0,
        "joint_kd": 1.2,
        "foot_kp_xy": 0.0,
        "foot_force_clip": 0.0,
        "foot_kd_xy": 12.0,
        "foot_lift_force": 120.0,
        "support_floor": 0.010,
        "zmp_floor": -0.030,
        "panic_support_floor": 0.000,
        "panic_zmp_floor": -0.060,
        "slip_floor": 0.070,
        "vv_floor": -0.12,
        "return_safety_boost": 0.12,
    }
    variants = [
        {"attempt": "release-8p5cm-r0p068-t26-rate0p72", "drop": 0.085, "max_blend": 0.52, "residual_scale": 0.068, "joint_kp": 21.0, "torque_clip": 26.0, "descend_s": 4.3, "return_s": 1.7, "return_rate": 0.72, "clamped_rate": 0.48, "panic_rate": 0.90, "hold_blend": 0.00, "panic_hold_blend": 0.00, **common},
        {"attempt": "release-8p5cm-r0p070-t28-rate0p90", "drop": 0.085, "max_blend": 0.53, "residual_scale": 0.070, "joint_kp": 22.0, "torque_clip": 28.0, "descend_s": 4.3, "return_s": 1.6, "return_rate": 0.90, "clamped_rate": 0.60, "panic_rate": 1.10, "hold_blend": 0.00, "panic_hold_blend": 0.00, **common},
        {"attempt": "release-8p3cm-r0p070-t28-rate0p90", "drop": 0.083, "max_blend": 0.53, "residual_scale": 0.070, "joint_kp": 22.0, "torque_clip": 28.0, "descend_s": 4.0, "return_s": 1.7, "return_rate": 0.90, "clamped_rate": 0.60, "panic_rate": 1.10, "hold_blend": 0.00, "panic_hold_blend": 0.00, **common},
        {"attempt": "release-8p2cm-r0p068-t26-rate1p10", "drop": 0.082, "max_blend": 0.52, "residual_scale": 0.068, "joint_kp": 21.0, "torque_clip": 26.0, "descend_s": 4.0, "return_s": 1.6, "return_rate": 1.10, "clamped_rate": 0.75, "panic_rate": 1.30, "hold_blend": 0.00, "panic_hold_blend": 0.00, **common},
        {"attempt": "release-8p0cm-r0p070-t28-rate1p20", "drop": 0.080, "max_blend": 0.53, "residual_scale": 0.070, "joint_kp": 22.0, "torque_clip": 28.0, "descend_s": 3.8, "return_s": 1.6, "return_rate": 1.20, "clamped_rate": 0.85, "panic_rate": 1.40, "hold_blend": 0.00, "panic_hold_blend": 0.00, **common},
    ]
    result = {
        "evaluation_seconds": args.seconds,
        "planning_gate": {
            "team_validation_mode": "manual-pass",
            "spec_delta": "M19 adds return-phase support/ZMP clamp after exp65 showed 7cm depth but return/support-ZMP collapse.",
            "perspectives": {
                "product": "targets the exact blocker between 6cm recoverable and 7cm recoverable squat",
                "architecture": "keeps exp62 qfrc controller but replaces abrupt return blend with a rate-limited support/ZMP clamp",
                "security": "no credentials or external side effects",
                "qa": "native sweep logs clamp mode counts, contact, slip, support/ZMP, return, and fall state",
                "skeptic": "holding blend can preserve stance but may prevent final return within 6s",
            },
            "dod": [
                "raw native JSON per return clamp variant",
                "summary states whether any variant passes recoverable_7cm_gate",
            ],
        },
        "sources": [
            {
                "url": "https://www.mdpi.com/1424-8220/25/2/435",
                "accessed": "2026-06-18",
                "note": "TP-MPC plus WBC squat framing: trajectory optimization plus constraint-following control.",
            },
            {
                "url": "https://arxiv.org/html/2505.19540v1",
                "accessed": "2026-06-18",
                "note": "WB-MPC/ZMP framing: ZMP tracking relative to the support polygon as balance term.",
            },
            {
                "url": "https://par.nsf.gov/servlets/purl/10579190",
                "accessed": "2026-06-18",
                "note": "Safe WBC squat discussion: both feet contact plus ZMP/friction constraints during squatting.",
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
