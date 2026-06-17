"""Probe CoM/ZMP-feasible target trajectories for G1 squat.

This experiment moves the planning layer above exp62's torque assistance:
first solve foot-fixed static targets with an explicit CoM-centering term,
then track a rate-limited target-drop envelope instead of pushing pose residuals.
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
from scipy.optimize import least_squares


EXP_DIR = Path(__file__).resolve().parent
ROOT = EXP_DIR.parents[1]
VERIFY = EXP_DIR / "verify"
EXP62_PATH = ROOT / "experiments/62-g1-actuator-contact-wbc-probe/run_actuator_contact_wbc_probe.py"


def load_exp62():
    spec = importlib.util.spec_from_file_location("exp62_actuator_contact", EXP62_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {EXP62_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EXP62 = load_exp62()
EXP60 = EXP62.EXP60
EXP52 = EXP62.EXP52
EXP28 = EXP62.EXP28
EXP37 = EXP62.EXP37

G = 9.81


def smoothstep(x: float) -> float:
    y = float(np.clip(x, 0.0, 1.0))
    return y * y * (3.0 - 2.0 * y)


def support_center(support: dict[str, Any]) -> np.ndarray:
    return 0.5 * (np.asarray(support["support_min_xy"]) + np.asarray(support["support_max_xy"]))


def support_margin_for_point(point_xy: np.ndarray, support: dict[str, Any]) -> float:
    min_xy = np.asarray(support["support_min_xy"])
    max_xy = np.asarray(support["support_max_xy"])
    return float(np.min(np.array([
        point_xy[0] - min_xy[0],
        max_xy[0] - point_xy[0],
        point_xy[1] - min_xy[1],
        max_xy[1] - point_xy[1],
    ])))


def qpos_index(model: mujoco.MjModel, joint_name: str) -> int:
    return int(model.jnt_qposadr[model.joint(joint_name).id])


def solve_com_feasible_target(
    model: mujoco.MjModel,
    start_qpos: np.ndarray,
    foot_site_ids: np.ndarray,
    foot_geom_ids: np.ndarray,
    drop: float,
    *,
    com_weight: float,
) -> dict[str, Any]:
    data = mujoco.MjData(model)
    data.qpos[:] = start_qpos
    mujoco.mj_forward(model, data)
    start_height = float(data.qpos[2])
    target_height = start_height - drop
    target_feet = data.site_xpos[foot_site_ids].copy()
    start_xy = start_qpos[:2].copy()
    default_lower = start_qpos[7:22].copy()
    lower_bounds = model.actuator_ctrlrange[:15, 0].copy()
    upper_bounds = model.actuator_ctrlrange[:15, 1].copy()
    support0 = EXP37.support_metrics(model, data, foot_geom_ids)
    support_xy = support_center(support0)

    def unpack(x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        pelvis_xy = start_xy + x[:2]
        lower = x[2:]
        return pelvis_xy, lower

    def residual(x: np.ndarray) -> np.ndarray:
        pelvis_xy, lower = unpack(x)
        data.qpos[:] = start_qpos
        data.qpos[:2] = pelvis_xy
        data.qpos[2] = target_height
        data.qpos[7:22] = lower
        mujoco.mj_forward(model, data)
        foot_error = (data.site_xpos[foot_site_ids] - target_feet).reshape(-1)
        com_error = data.subtree_com[0, :2] - support_xy
        reg = lower - default_lower
        pelvis_reg = pelvis_xy - start_xy
        knee_sym = np.array([lower[3] - lower[9]], dtype=np.float64)
        roll_sym = np.array([lower[1] + lower[7], lower[5] + lower[11]], dtype=np.float64)
        waist_reg = lower[12:15] - default_lower[12:15]
        return np.concatenate([
            42.0 * foot_error,
            com_weight * com_error,
            0.35 * reg,
            1.2 * pelvis_reg,
            1.0 * knee_sym,
            0.8 * roll_sym,
            2.0 * waist_reg,
        ])

    bounds_lo = np.concatenate([np.array([-0.05, -0.04]), lower_bounds])
    bounds_hi = np.concatenate([np.array([0.05, 0.04]), upper_bounds])
    result = least_squares(
        residual,
        np.concatenate([np.zeros(2), default_lower]),
        bounds=(bounds_lo, bounds_hi),
        max_nfev=900,
        xtol=1e-8,
        ftol=1e-8,
        gtol=1e-8,
    )
    pelvis_xy, lower = unpack(result.x)
    data.qpos[:] = start_qpos
    data.qpos[:2] = pelvis_xy
    data.qpos[2] = target_height
    data.qpos[7:22] = lower
    mujoco.mj_forward(model, data)
    foot_errors = np.linalg.norm(data.site_xpos[foot_site_ids] - target_feet, axis=1)
    support = EXP37.support_metrics(model, data, foot_geom_ids)
    com_xy = data.subtree_com[0, :2].copy()
    return {
        "drop": drop,
        "target_height": target_height,
        "success": bool(result.success),
        "cost": float(result.cost),
        "nfev": int(result.nfev),
        "pelvis_xy_offset": [float(v) for v in (pelvis_xy - start_xy)],
        "rms_foot_error": float(np.sqrt(np.mean(np.square(foot_errors)))),
        "max_foot_error": float(np.max(foot_errors)),
        "com_xy": [float(v) for v in com_xy],
        "support_center_xy": [float(v) for v in support_xy],
        "com_support_margin": support_margin_for_point(com_xy, support),
        "support_margin": support["support_margin"],
        "lower_body_target": [float(v) for v in lower],
    }


def interpolate_target(default_pose: np.ndarray, target: np.ndarray, fraction: float) -> np.ndarray:
    out = default_pose.copy()
    out[:15] = (1.0 - fraction) * default_pose[:15] + fraction * target
    return out


def phase_target_drop(t: float, target_drop: float, descend_s: float, hold_s: float, return_s: float) -> tuple[float, bool]:
    if t < descend_s:
        return target_drop * smoothstep(t / descend_s), False
    if t < descend_s + hold_s:
        return target_drop, False
    if t < descend_s + hold_s + return_s:
        r = smoothstep((t - descend_s - hold_s) / return_s)
        return target_drop * (1.0 - r), True
    return 0.0, True


def classify(native: dict[str, Any]) -> str:
    if native["pass_gate"]:
        return "PASS_COM_FEASIBLE_TRAJECTORY_NATIVE_GATE"
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


def native_eval(*, variant: dict[str, Any], seconds: float, out_dir: Path) -> dict[str, Any]:
    env = EXP28.ContactAwareSquat(
        stage_height=0.67,
        controller_blend=0.0,
        freeze_phase=True,
        blend_schedule="squat",
        reference_scale=1.0,
        config_overrides={"impl": "jax"},
    )
    policy = EXP28.build_policy(env, EXP52.EXP46_PARAMS) if variant["policy_weight"] > 0 else None
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
    initial_foot_xy = data.site_xpos[foot_site_ids, :2].copy()
    static_targets = []
    for drop in variant["target_grid"]:
        static_targets.append(solve_com_feasible_target(
            model,
            key.qpos.copy(),
            foot_site_ids,
            foot_geom_ids,
            drop,
            com_weight=variant["com_weight"],
        ))
    target = static_targets[-1]
    target_lower = np.asarray(target["lower_body_target"], dtype=np.float32)

    maps = EXP62.joint_maps(model)
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
    start_qpos = data.qpos.copy()
    previous_height = start_height
    previous_com_xy = data.subtree_com[0, :2].copy()
    previous_com_vel = np.zeros(2, dtype=np.float64)
    planned_drop = 0.0
    pose_indices = {
        "left_hip_pitch_joint": EXP62.qpos_index(model, "left_hip_pitch_joint"),
        "right_hip_pitch_joint": EXP62.qpos_index(model, "right_hip_pitch_joint"),
        "left_knee_joint": EXP62.qpos_index(model, "left_knee_joint"),
        "right_knee_joint": EXP62.qpos_index(model, "right_knee_joint"),
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
    max_pd_torque = 0.0
    samples = []

    for step in range(total_steps):
        t = step * ctrl_dt
        height = float(data.qpos[2])
        vertical_velocity = (height - previous_height) / ctrl_dt
        previous_height = height
        final_height = height
        min_height = min(min_height, height)
        support = EXP37.support_metrics(model, data, foot_geom_ids)
        center_xy = support_center(support)
        com_xy = data.subtree_com[0, :2].copy()
        com_vel = (com_xy - previous_com_xy) / ctrl_dt
        com_acc = (com_vel - previous_com_vel) / ctrl_dt
        previous_com_xy = com_xy.copy()
        previous_com_vel = com_vel.copy()
        com_z = max(float(data.subtree_com[0, 2]), 0.05)
        zmp_xy = com_xy - (com_z / G) * com_acc
        zmp_margin = support_margin_for_point(zmp_xy, support)
        contacts = [
            float(data.sensordata[model.sensor_adr[sensor_id]]) > 0
            for sensor_id in foot_contact_sensor_ids
        ]
        both_feet = all(contacts)
        both_feet_contact_count += int(both_feet)
        foot_slip = float(np.max(np.linalg.norm(data.site_xpos[foot_site_ids, :2] - initial_foot_xy, axis=1)))

        desired_drop, returning = phase_target_drop(
            t,
            variant["target_drop"],
            variant["descend_s"],
            variant["hold_s"],
            variant["return_s"],
        )
        feasible = (
            support["support_margin"] >= variant["support_floor"]
            and zmp_margin >= variant["zmp_floor"]
            and foot_slip <= variant["slip_limit"]
            and vertical_velocity >= -variant["down_velocity_limit"]
        )
        rate = variant["return_rate"] if returning else variant["descend_rate"]
        if feasible or returning:
            delta = float(np.clip(desired_drop - planned_drop, -rate * ctrl_dt, rate * ctrl_dt))
        else:
            delta = -variant["retreat_rate"] * ctrl_dt
        planned_drop = float(np.clip(planned_drop + delta, 0.0, variant["target_drop"]))
        fraction = planned_drop / max(variant["target_drop"], 1e-6)

        policy_targets = default_pose
        if policy is not None:
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
            last_action = action_np
        target_pose = interpolate_target(default_pose, target_lower, fraction)
        target_pose = (1.0 - variant["stabilizer_mix"]) * target_pose + variant["stabilizer_mix"] * policy_targets
        data.ctrl[:] = np.clip(target_pose, model.actuator_ctrlrange[:, 0], model.actuator_ctrlrange[:, 1])
        data.qfrc_applied[:] = 0.0
        if variant["torque_clip"] > 0:
            support_health = float(np.clip((support["support_margin"] + 0.005) / 0.045, 0.0, 1.0))
            zmp_health = float(np.clip((zmp_margin + 0.005) / 0.045, 0.0, 1.0))
            slip_health = float(np.clip(1.0 - foot_slip / variant["slip_limit"], 0.0, 1.0))
            pd_qfrc, pd_max = EXP62.lower_pd_torque(
                model=model,
                data=data,
                maps=maps,
                target_qpos=data.ctrl,
                kp=variant["joint_kp"],
                kd=variant["joint_kd"],
                torque_clip=variant["torque_clip"],
                safety_scale=min(1.0, support_health, zmp_health, slip_health),
            )
            data.qfrc_applied[:] = pd_qfrc
            max_pd_torque = max(max_pd_torque, pd_max)
        for _ in range(n_substeps):
            mujoco.mj_step(model, data)
        data.qfrc_applied[:] = 0.0

        visible_drop_now = start_height - height
        if visible_drop_now >= 0.08 and first_visible_at is None:
            first_visible_at = round(t, 3)
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

        if step % max(1, int(0.2 / ctrl_dt)) == 0:
            samples.append({
                "t": round(t, 3),
                "height": height,
                "visible_drop": visible_drop_now,
                "desired_drop": desired_drop,
                "planned_drop": planned_drop,
                "fraction": fraction,
                "feasible": feasible,
                "support_margin": support["support_margin"],
                "zmp_margin": zmp_margin,
                "com_xy": [float(v) for v in com_xy],
                "support_center_xy": [float(v) for v in center_xy],
                "both_feet_contact": both_feet,
                "foot_slip_distance": foot_slip,
                "vertical_velocity": vertical_velocity,
                "knee_delta": max_knee_delta,
                "hip_delta": max_hip_delta,
                "pd_torque_max": max_pd_torque,
                "up_z": up_z,
            })

    visible_drop = start_height - min_height
    foot_contact_ratio = both_feet_contact_count / max(1, total_steps)
    return_to_stand = final_height >= 0.74
    native = {
        "attempt": variant["attempt"],
        "variant": variant,
        "static_targets": static_targets,
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
        "max_pd_torque": max_pd_torque,
        "max_planned_drop": max(sample["planned_drop"] for sample in samples) if samples else planned_drop,
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
        "# G1 CoM-Feasible Trajectory Probe Summary",
        "",
        "| Attempt | Verdict | Drop | Planned | Knee | Hip | Contact | Slip | CoM min | ZMP min | Final h | Fell |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for run in result["runs"]:
        fell = "never" if run["fell_at"] is None else f"{run['fell_at']:.2f}s"
        lines.append(
            f"| {run['attempt']} | {run['verdict']} | {run['visible_drop']:.4f}m | "
            f"{run['max_planned_drop']:.4f}m | {run['max_knee_delta_rad']:.3f} | "
            f"{run['max_hip_pitch_delta_rad']:.3f} | {run['foot_contact_ratio']:.2f} | "
            f"{run['foot_slip_distance']:.3f}m | {run['min_support_margin']:.4f}m | "
            f"{run['min_zmp_margin']:.4f}m | {run['final_height']:.4f}m | {fell} |"
        )
    lines.extend([
        "",
        f"Best no-fall run: {result['best_no_fall']}",
        f"Best depth run: {result['best_depth']}",
        "",
        "M19 closes only when visible depth, knee/hip pose, no-fall, contact, stance, return, and browser replay gates pass together.",
    ])
    (out_dir / "com-feasible-trajectory-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=6.0)
    args = parser.parse_args()
    out_dir = VERIFY / "com-feasible-trajectory"
    out_dir.mkdir(parents=True, exist_ok=True)
    common = {
        "target_grid": [0.0, 0.02, 0.04, 0.06, 0.08],
        "target_drop": 0.08,
        "hold_s": 0.4,
        "return_s": 1.8,
        "support_floor": 0.010,
        "zmp_floor": -0.015,
        "slip_limit": 0.08,
        "down_velocity_limit": 0.08,
        "return_rate": 0.08,
        "retreat_rate": 0.06,
        "policy_weight": 1.0,
        "stabilizer_mix": 0.65,
        "joint_kd": 1.2,
    }
    variants = [
        {"attempt": "com-envelope-slow", "descend_s": 4.2, "descend_rate": 0.020, "com_weight": 18.0, "torque_clip": 0.0, "joint_kp": 0.0, **common},
        {"attempt": "com-envelope-torque", "descend_s": 4.2, "descend_rate": 0.020, "com_weight": 18.0, "torque_clip": 20.0, "joint_kp": 18.0, **common},
        {"attempt": "com-envelope-fast-torque", "descend_s": 3.4, "descend_rate": 0.026, "com_weight": 18.0, "torque_clip": 20.0, "joint_kp": 18.0, **common},
        {"attempt": "com-strong-center-torque", "descend_s": 4.4, "descend_rate": 0.020, "com_weight": 32.0, "torque_clip": 20.0, "joint_kp": 18.0, **common},
        {"attempt": "com-strong-stabilizer-torque", **common, "descend_s": 4.4, "descend_rate": 0.020, "com_weight": 18.0, "stabilizer_mix": 0.78, "torque_clip": 20.0, "joint_kp": 18.0},
    ]
    result = {
        "planning_gate": {
            "team_validation_mode": "manual-pass",
            "spec_delta": "M19 probes TP-MPC-style CoM/ZMP-feasible reference generation before applying pose/torque pushes.",
            "perspectives": {
                "product": "tests the current M19 blocker: visible squat needs feasible trajectory, not stronger torque",
                "architecture": "solves foot-fixed static targets with CoM centering and tracks a guarded drop envelope",
                "security": "no credentials or external side effects",
                "qa": "native sweep logs planned drop, CoM/ZMP margins, pose, contact, slip, return, fall",
                "skeptic": "feasibility guards may preserve balance by refusing to reach visible depth",
            },
            "dod": [
                "native JSON per CoM-feasible trajectory variant under verify/",
                "summary identifies whether feasible trajectory planning expands the stable corridor toward 8cm",
            ],
        },
        "runs": [],
    }
    for variant in variants:
        result["runs"].append(native_eval(variant=variant, seconds=args.seconds, out_dir=out_dir / variant["attempt"]))
    no_fall = [run for run in result["runs"] if run["fell_at"] is None]
    best_no_fall = max(no_fall, key=lambda run: run["visible_drop"], default=None)
    best_depth = max(result["runs"], key=lambda run: run["visible_drop"])
    result["best_no_fall"] = None if best_no_fall is None else {
        "attempt": best_no_fall["attempt"],
        "visible_drop": best_no_fall["visible_drop"],
        "max_planned_drop": best_no_fall["max_planned_drop"],
        "max_knee_delta_rad": best_no_fall["max_knee_delta_rad"],
        "max_hip_pitch_delta_rad": best_no_fall["max_hip_pitch_delta_rad"],
        "min_support_margin": best_no_fall["min_support_margin"],
        "min_zmp_margin": best_no_fall["min_zmp_margin"],
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
