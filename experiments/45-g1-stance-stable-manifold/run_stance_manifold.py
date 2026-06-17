"""Search stance-stable lower-body squat targets and test native tracking."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import jax
import jax.numpy as jp
import mujoco
import numpy as np
from scipy.optimize import least_squares


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
EXP36 = EXP42.EXP36
EXP37 = EXP42.EXP37
EXP28 = EXP42.EXP28


VISIBLE_GATE = {
    "pelvis_drop_m": 0.08,
    "knee_delta_rad": 0.60,
    "hip_pitch_delta_rad": 0.35,
}


def safe_inverse_summary(model: mujoco.MjModel, data: mujoco.MjData) -> dict:
    probe = mujoco.MjData(model)
    mujoco.mj_copyData(probe, model, data)
    return EXP42.inverse_summary(model, probe)


def support_center(model: mujoco.MjModel, data: mujoco.MjData, foot_geom_ids: np.ndarray) -> np.ndarray:
    support = EXP37.support_metrics(model, data, foot_geom_ids)
    return 0.5 * (np.asarray(support["support_min_xy"]) + np.asarray(support["support_max_xy"]))


def joint_value(model: mujoco.MjModel, qpos: np.ndarray, name: str) -> float:
    return float(qpos[model.joint(name).qposadr[0]])


def solve_stance_target(
    model: mujoco.MjModel,
    start_qpos: np.ndarray,
    foot_site_ids: np.ndarray,
    foot_geom_ids: np.ndarray,
    drop: float,
    *,
    com_weight: float,
    posture_weight: float,
) -> dict:
    data = mujoco.MjData(model)
    data.qpos[:] = start_qpos
    mujoco.mj_forward(model, data)
    start_height = float(data.qpos[2])
    target_height = start_height - drop
    target_feet = data.site_xpos[foot_site_ids].copy()
    default_lower = start_qpos[7:22].copy()
    lower_bounds = model.actuator_ctrlrange[:15, 0].copy()
    upper_bounds = model.actuator_ctrlrange[:15, 1].copy()

    def residual(x: np.ndarray) -> np.ndarray:
        data.qpos[:] = start_qpos
        data.qpos[2] = target_height
        data.qpos[7:22] = x
        mujoco.mj_forward(model, data)
        support = EXP37.support_metrics(model, data, foot_geom_ids)
        center = 0.5 * (np.asarray(support["support_min_xy"]) + np.asarray(support["support_max_xy"]))
        com_xy = np.asarray(support["com_xy"])
        foot_error = (data.site_xpos[foot_site_ids] - target_feet).reshape(-1)
        reg = x - default_lower
        knee_sym = np.array([x[3] - x[9]], dtype=np.float64)
        roll_sym = np.array([x[1] + x[7], x[5] + x[11]], dtype=np.float64)
        ankle_sym = np.array([x[4] - x[10]], dtype=np.float64)
        waist_reg = x[12:15] - default_lower[12:15]
        margin_deficit = np.array([max(0.0, 0.025 - support["support_margin"])], dtype=np.float64)
        # Encourage a squat-like visible pose while allowing ankle/hip to shift
        # the CoM projection back toward the stance center.
        knee_target = np.array([x[3] - (default_lower[3] + 0.75), x[9] - (default_lower[9] + 0.75)])
        hip_target = np.array([x[0] - (default_lower[0] - 0.42), x[6] - (default_lower[6] - 0.42)])
        return np.concatenate([
            42.0 * foot_error,
            com_weight * (com_xy - center),
            5.0 * margin_deficit,
            posture_weight * knee_target,
            posture_weight * hip_target,
            0.30 * reg,
            1.5 * knee_sym,
            1.0 * roll_sym,
            0.6 * ankle_sym,
            2.0 * waist_reg,
        ])

    result = least_squares(
        residual,
        default_lower,
        bounds=(lower_bounds, upper_bounds),
        max_nfev=900,
        xtol=1e-8,
        ftol=1e-8,
        gtol=1e-8,
    )
    data.qpos[:] = start_qpos
    data.qpos[2] = target_height
    data.qpos[7:22] = result.x
    mujoco.mj_forward(model, data)
    foot_errors = np.linalg.norm(data.site_xpos[foot_site_ids] - target_feet, axis=1)
    support = EXP37.support_metrics(model, data, foot_geom_ids)
    knee_delta = max(
        abs(joint_value(model, data.qpos, "left_knee_joint") - joint_value(model, start_qpos, "left_knee_joint")),
        abs(joint_value(model, data.qpos, "right_knee_joint") - joint_value(model, start_qpos, "right_knee_joint")),
    )
    hip_delta = max(
        abs(joint_value(model, data.qpos, "left_hip_pitch_joint") - joint_value(model, start_qpos, "left_hip_pitch_joint")),
        abs(joint_value(model, data.qpos, "right_hip_pitch_joint") - joint_value(model, start_qpos, "right_hip_pitch_joint")),
    )
    visible_pose_gate = {
        "pelvis_drop_pass": drop >= VISIBLE_GATE["pelvis_drop_m"],
        "knee_delta_pass": knee_delta >= VISIBLE_GATE["knee_delta_rad"],
        "hip_pitch_delta_pass": hip_delta >= VISIBLE_GATE["hip_pitch_delta_rad"],
    }
    visible_pose_gate["pass"] = all(visible_pose_gate.values())
    center = support_center(model, data, foot_geom_ids)
    return {
        "drop": drop,
        "start_height": start_height,
        "target_height": target_height,
        "success": bool(result.success),
        "cost": float(result.cost),
        "nfev": int(result.nfev),
        "com_weight": com_weight,
        "posture_weight": posture_weight,
        "rms_foot_error": float(np.sqrt(np.mean(np.square(foot_errors)))),
        "max_foot_error": float(np.max(foot_errors)),
        "support_margin": support["support_margin"],
        "inside_support": support["inside_support"],
        "com_xy": support["com_xy"],
        "support_center_xy": [float(v) for v in center],
        "com_center_error": float(np.linalg.norm(np.asarray(support["com_xy"]) - center)),
        "knee_delta_rad": knee_delta,
        "hip_pitch_delta_rad": hip_delta,
        "visible_pose_gate": visible_pose_gate,
        "lower_body_target": [float(v) for v in result.x],
    }


def native_eval(
    *,
    attempt: str,
    target: dict,
    max_blend: float,
    policy_weight: float,
    descend_s: float,
    hold_s: float,
    return_s: float,
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
    target_pose = default_pose.copy()
    target_pose[:15] = np.asarray(target["lower_body_target"], dtype=np.float32)
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
        current_blend = EXP36.blend_profile(t, descend_s, hold_s, return_s, max_blend)
        max_observed_blend = max(max_observed_blend, current_blend)
        policy_targets = default_pose + policy_weight * action_np * float(env._config.action_scale)
        data.ctrl[:] = (1.0 - current_blend) * policy_targets + current_blend * target_pose
        for _ in range(n_substeps):
            mujoco.mj_step(model, data)
        last_action = action_np

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
                "support_margin": support["support_margin"],
                "both_feet_contact": both_feet,
                "foot_slip_distance": foot_slip,
                "controller_blend": current_blend,
                "up_z": up_z,
                "lr_normal_imbalance": wrench["lr_normal_imbalance"],
                "inverse_torque": inv["lower_inverse_linf"],
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
        verdict = "PASS_STANCE_MANIFOLD_VISIBLE_SQUAT"
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
        "target": target,
        "max_blend": max_blend,
        "policy_weight": policy_weight,
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
        "max_observed_blend": max_observed_blend,
        "pass_gate": pass_gate,
        "verdict": verdict,
        "samples": samples,
    }
    (out_dir / "stance-native-eval.json").write_text(json.dumps(native, indent=2), encoding="utf-8")
    return native


def write_summary(results: list[dict]) -> None:
    lines = [
        "# G1 Stance-Stable Manifold Summary",
        "",
        "| Attempt | Static pose | Static support | Native verdict | Drop | Fell at | Contact | Slip | Native support min |",
        "|---|---|---:|---|---:|---:|---:|---:|---:|",
    ]
    for native in results:
        target = native["target"]
        pose = "PASS" if target["visible_pose_gate"]["pass"] else "PENDING"
        fell = "never" if native["fell_at"] is None else f"{native['fell_at']:.2f}s"
        lines.append(
            f"| {native['attempt']} | {pose} | {target['support_margin']:.4f}m | {native['verdict']} | "
            f"{native['visible_drop']:.4f}m | {fell} | {native['foot_contact_ratio']:.2f} | "
            f"{native['foot_slip_distance']:.3f}m | {native['min_support_margin']:.4f}m |"
        )
    lines.extend([
        "",
        "M19 closes only when visible depth, no-fall, contact, stance, return, and browser replay gates pass together.",
    ])
    (VERIFY / "stance-manifold-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=None)
    parser.add_argument("--seconds", type=float, default=6.0)
    parser.add_argument("--sweep", action="store_true")
    args = parser.parse_args()
    source = args.source or EXP28.default_source()
    env = EXP28.ContactAwareSquat(
        stage_height=0.67,
        controller_blend=0.0,
        freeze_phase=True,
        blend_schedule="squat",
        reference_scale=1.0,
        config_overrides={"impl": "jax"},
    )
    model = env.mj_model
    key = model.keyframe("knees_bent")
    foot_site_ids = np.asarray(env._feet_site_id)
    foot_geom_ids = np.asarray([model.geom("left_foot").id, model.geom("right_foot").id])
    variants = [
        ("drop-0p08-com4-posture1", 0.08, 4.0, 1.0, 0.45, 1.0, 3.0, 0.2, 2.5),
        ("drop-0p12-com4-posture1", 0.12, 4.0, 1.0, 0.45, 1.0, 3.2, 0.2, 2.6),
        ("drop-0p12-com8-posture0p6", 0.12, 8.0, 0.6, 0.45, 1.0, 3.2, 0.2, 2.6),
        ("drop-0p16-com8-posture0p6", 0.16, 8.0, 0.6, 0.45, 1.0, 3.5, 0.2, 2.8),
        ("drop-0p12-com12-posture0p3", 0.12, 12.0, 0.3, 0.45, 1.0, 3.4, 0.2, 2.8),
    ] if args.sweep else [
        ("drop-0p12-com8-posture0p6", 0.12, 8.0, 0.6, 0.45, 1.0, 3.2, 0.2, 2.6),
    ]

    VERIFY.mkdir(parents=True, exist_ok=True)
    results = []
    for name, drop, com_weight, posture_weight, max_blend, policy_weight, descend_s, hold_s, return_s in variants:
        out_dir = VERIFY / "attempts" / name
        out_dir.mkdir(parents=True, exist_ok=True)
        target = solve_stance_target(
            model,
            key.qpos.copy(),
            foot_site_ids,
            foot_geom_ids,
            drop,
            com_weight=com_weight,
            posture_weight=posture_weight,
        )
        native = native_eval(
            attempt=name,
            target=target,
            max_blend=max_blend,
            policy_weight=policy_weight,
            descend_s=descend_s,
            hold_s=hold_s,
            return_s=return_s,
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
