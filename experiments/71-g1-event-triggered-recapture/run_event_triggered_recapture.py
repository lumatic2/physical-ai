"""Probe event-triggered support recapture for the G1 squat 7cm gate."""

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
EXP67_PATH = ROOT / "experiments/67-g1-qfrc-wbc-return-selector/run_qfrc_wbc_return_selector.py"


def load_exp67():
    spec = importlib.util.spec_from_file_location("exp67_qfrc_wbc_selector", EXP67_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {EXP67_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EXP67 = load_exp67()
EXP62 = EXP67.EXP62
EXP28 = EXP67.EXP28
EXP36 = EXP67.EXP36
EXP37 = EXP67.EXP37
EXP42 = EXP67.EXP42
EXP52 = EXP67.EXP52
EXP60 = EXP67.EXP60
POSE_JOINTS = EXP67.POSE_JOINTS


def recoverable_7cm_gate(run: dict[str, Any]) -> bool:
    return (
        run["fell_at"] is None
        and run["visible_drop"] >= 0.07
        and run["return_to_stand"]
        and run["foot_contact_ratio"] >= 0.90
        and run["foot_slip_distance"] <= 0.08
        and run["max_joint_limit_violation"] <= 0.05
    )


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


def annotate(run: dict[str, Any]) -> dict[str, Any]:
    run["recoverable_7cm_gate"] = recoverable_7cm_gate(run)
    run["visible_8cm_gate"] = visible_8cm_gate(run)
    if run["visible_8cm_gate"]:
        run["transition_verdict"] = "PASS_VISIBLE_8CM_GATE"
    elif run["recoverable_7cm_gate"]:
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


def make_common() -> dict[str, Any]:
    return {
        "policy_weight": 1.0,
        "joint_kd": 1.2,
        "foot_kp_xy": 0.0,
        "foot_force_clip": 0.0,
        "foot_kd_xy": 12.0,
        "foot_lift_force": 120.0,
        "support_floor": 0.008,
        "zmp_floor": -0.020,
        "slip_floor": 0.070,
        "downward_floor": 0.095,
        "stand_height": 0.74,
        "height_floor": 0.620,
        "upright_floor": 0.82,
        "qfrc_soft_cap": 56.0,
        "return_safety_boost": 0.24,
        "return_min_safety": 0.66,
        "descend_rate": 0.040,
        "slow_release": 0.090,
        "fast_release": 0.180,
        "small_hold": 0.006,
        "w_height": 72.0,
        "w_stand": 300.0,
        "w_height_floor": 1200.0,
        "w_upright": 720.0,
        "w_support": 2700.0,
        "w_zmp": 2100.0,
        "w_slip": 1300.0,
        "w_contact": 320.0,
        "w_downward": 170.0,
        "w_qfrc": 2.0,
        "w_smooth": 2.0,
    }


def variants() -> list[dict[str, Any]]:
    common = make_common()
    rows: list[dict[str, Any]] = []
    for trigger_drop in [0.064, 0.066, 0.067, 0.068]:
        for max_blend in [0.536, 0.538, 0.540]:
            for recapture_s in [1.15, 1.25]:
                for hold_s in [0.00, 0.12, 0.20]:
                    # Keep the search bounded around the narrow 6.6-7.0cm transition.
                    if trigger_drop in {0.064, 0.068} and hold_s == 0.20:
                        continue
                    rows.append({
                        **common,
                        "attempt": f"recap-drop{trigger_drop:.3f}-b{max_blend:.3f}-rs{recapture_s:.2f}-hold{hold_s:.2f}".replace(".", "p"),
                        "drop": 0.0835,
                        "max_blend": max_blend,
                        "residual_scale": 0.0682,
                        "joint_kp": 25.5,
                        "torque_clip": 37.0,
                        "descend_s": 3.50,
                        "return_s": recapture_s,
                        "recapture_hold_s": hold_s,
                        "recapture_trigger_drop": trigger_drop,
                        "recapture_support_floor": 0.010,
                        "recapture_zmp_floor": -0.018,
                        "recapture_error_gain": 2.4,
                    })
    rows.sort(key=lambda row: (
        abs(row["recapture_trigger_drop"] - 0.0665),
        abs(row["max_blend"] - 0.538),
        row["recapture_hold_s"],
        row["return_s"],
    ))
    return rows[:24]


def native_eval_event(*, variant: dict[str, Any], seconds: float, out_dir: Path) -> dict[str, Any]:
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
    prev_com_xy = data.subtree_com[0, :2].copy()
    prev_com_vel = np.zeros(2, dtype=np.float64)
    start_qpos = data.qpos.copy()
    pose_indices = {name: EXP62.qpos_index(model, name) for name in POSE_JOINTS}
    prev_blend = 0.0

    min_height = start_height
    final_height = start_height
    fell_at = None
    first_7cm_at = None
    recapture_at = None
    recapture_reason = None
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
        visible_drop_now = start_height - height
        support = EXP37.support_metrics(model, data, foot_geom_ids)
        center_xy = EXP60.support_center(support)
        com_xy, com_vel, zmp = EXP67.zmp_margin(
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

        if recapture_at is None:
            if visible_drop_now >= variant["recapture_trigger_drop"]:
                recapture_at = round(t, 3)
                recapture_reason = "drop"
            elif support["support_margin"] <= variant["recapture_support_floor"] and visible_drop_now >= 0.045:
                recapture_at = round(t, 3)
                recapture_reason = "support"
            elif zmp <= variant["recapture_zmp_floor"] and visible_drop_now >= 0.045:
                recapture_at = round(t, 3)
                recapture_reason = "zmp"

        if recapture_at is None:
            desired_fraction = min(max(t / variant["descend_s"], 0.0), 1.0)
            return_phase = 0.0
        else:
            elapsed = max(0.0, t - recapture_at)
            hold_s = variant["recapture_hold_s"]
            release_elapsed = max(0.0, elapsed - hold_s)
            return_phase = min(release_elapsed / variant["return_s"], 1.0)
            # Hold enough commanded depth briefly so inertia can cross 7cm, then
            # release toward standing while increasing support-center feedback.
            desired_fraction = max(0.0, 1.0 - return_phase)
            error_xy = error_xy * variant["recapture_error_gain"]

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

        target, qfrc, chosen = EXP67.choose_blend(
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
        prev_com_xy = com_xy.copy()
        prev_com_vel = com_vel.copy()

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
                "recapture_active": recapture_at is not None,
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
        "recapture_at": recapture_at,
        "recapture_reason": recapture_reason,
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
        "# G1 Event-Triggered Recapture Summary",
        "",
        "| Attempt | 8cm | 7cm | Verdict | Drop | Recap | Reason | Contact | Slip | CoM min | ZMP min | Final h | Fell |",
        "|---|---|---|---|---:|---:|---|---:|---:|---:|---:|---:|---|",
    ]
    for run in result["runs"]:
        fell = "never" if run["fell_at"] is None else f"{run['fell_at']:.2f}s"
        gate8 = "PASS" if run["visible_8cm_gate"] else "FAIL"
        gate7 = "PASS" if run["recoverable_7cm_gate"] else "FAIL"
        recap = "-" if run["recapture_at"] is None else f"{run['recapture_at']:.2f}s"
        lines.append(
            f"| {run['attempt']} | {gate8} | {gate7} | {run['transition_verdict']} | "
            f"{run['visible_drop']:.4f}m | {recap} | {run['recapture_reason']} | "
            f"{run['foot_contact_ratio']:.2f} | {run['foot_slip_distance']:.3f}m | "
            f"{run['min_support_margin']:.4f}m | {run['min_zmp_margin']:.4f}m | "
            f"{run['final_height']:.4f}m | {fell} |"
        )
    lines.extend([
        "",
        f"Best recoverable run: {result['best_recoverable']}",
        f"Best no-fall run: {result['best_no_fall']}",
        f"Best depth run: {result['best_depth']}",
    ])
    (out_dir / "event-triggered-recapture-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=7.0)
    args = parser.parse_args()
    out_dir = VERIFY / "event-triggered-recapture"
    out_dir.mkdir(parents=True, exist_ok=True)
    result = {
        "evaluation_seconds": args.seconds,
        "planning_gate": {
            "team_validation_mode": "manual-pass",
            "spec_delta": "M19 switches from fixed descend/return schedules to event-triggered support recapture near the 7cm boundary.",
            "perspectives": {
                "product": "targets the exact support/ZMP collapse found in exp70",
                "architecture": "keeps exp67 WBC selector but changes the phase machine from schedule-based to event-triggered",
                "security": "local MuJoCo/JAX only",
                "qa": "native raw JSON records recapture trigger time/reason plus 7cm/8cm gates",
                "skeptic": "triggering too early may preserve standing but never cross 7cm; triggering too late may reproduce collapse",
            },
            "dod": [
                "recapture trigger is visible in raw evidence",
                "summary reports whether any event-triggered candidate passes recoverable_7cm_gate",
            ],
        },
        "sources": [
            {
                "url": "https://arxiv.org/abs/1612.08034",
                "accessed": "2026-06-18",
                "note": "Capture-point recovery controls CP by modulating ZMP/CMP relative to support.",
            },
            {
                "url": "https://usa.honda-ri.com/w/capture-point-a-step-toward-humanoid-push-recovery",
                "accessed": "2026-06-18",
                "note": "Capture point frames recovery as reaching a state that can stop without another step.",
            },
            {
                "url": "https://arxiv.org/html/2504.18698v1",
                "accessed": "2026-06-18",
                "note": "ZMP support-polygon constraints remain a stability gate for biped recovery.",
            },
        ],
        "runs": [],
    }
    for variant in variants():
        result["runs"].append(native_eval_event(
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
        "final_height": best_recoverable["final_height"],
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
    if any(run["visible_8cm_gate"] for run in result["runs"]):
        result["verdict"] = "PASS_VISIBLE_8CM_GATE"
    elif recoverable:
        result["verdict"] = "PASS_RECOVERABLE_7CM_GATE"
    else:
        result["verdict"] = "FAIL_RECOVERABLE_7CM_GATE"
    write_summary(result, out_dir)
    (out_dir / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(result["verdict"], json.dumps({
        "best_recoverable": result["best_recoverable"],
        "best_no_fall": result["best_no_fall"],
        "best_depth": result["best_depth"],
    }, indent=2), flush=True)


if __name__ == "__main__":
    main()
