"""Probe foot-fixed IK targets for a visible G1 squat.

This experiment separates target geometry from learning: first solve a static
lower-body target that keeps both feet fixed while lowering the pelvis, then
test whether a native policy/PD blend can descend, hold, and return.
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
from scipy.optimize import least_squares


EXP_DIR = Path(__file__).resolve().parent
ROOT = EXP_DIR.parents[1]
VERIFY = EXP_DIR / "verify"
EXP28_PATH = ROOT / "experiments/28-g1-controlled-squat-stage0p74/run_controlled_squat.py"


def load_exp28():
    spec = importlib.util.spec_from_file_location("exp28_controlled_squat", EXP28_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {EXP28_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EXP28 = load_exp28()


def slug_float(value: float) -> str:
    return f"{value:.3f}".rstrip("0").rstrip(".").replace(".", "p")


def solve_foot_fixed_target(model: mujoco.MjModel, start_qpos: np.ndarray, foot_site_ids: np.ndarray, drop: float) -> dict:
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
        foot_error = (data.site_xpos[foot_site_ids] - target_feet).reshape(-1)
        reg = x - default_lower
        knee_sym = np.array([x[3] - x[9]], dtype=np.float64)
        roll_sym = np.array([x[1] + x[7], x[5] + x[11]], dtype=np.float64)
        waist_reg = x[12:15] - default_lower[12:15]
        return np.concatenate([
            35.0 * foot_error,
            0.45 * reg,
            1.2 * knee_sym,
            0.8 * roll_sym,
            2.0 * waist_reg,
        ])

    result = least_squares(
        residual,
        default_lower,
        bounds=(lower_bounds, upper_bounds),
        max_nfev=600,
        xtol=1e-7,
        ftol=1e-7,
        gtol=1e-7,
    )
    data.qpos[:] = start_qpos
    data.qpos[2] = target_height
    data.qpos[7:22] = result.x
    mujoco.mj_forward(model, data)
    foot_errors = np.linalg.norm(data.site_xpos[foot_site_ids] - target_feet, axis=1)
    return {
        "drop": drop,
        "start_height": start_height,
        "target_height": target_height,
        "success": bool(result.success),
        "cost": float(result.cost),
        "nfev": int(result.nfev),
        "rms_foot_error": float(np.sqrt(np.mean(np.square(foot_errors)))),
        "max_foot_error": float(np.max(foot_errors)),
        "lower_body_target": [float(v) for v in result.x],
    }


def blend_profile(t: float, descend_s: float, hold_s: float, return_s: float, max_blend: float) -> float:
    if t < descend_s:
        return max_blend * min(max(t / descend_s, 0.0), 1.0)
    if t < descend_s + hold_s:
        return max_blend
    if t < descend_s + hold_s + return_s:
        return max_blend * (1.0 - min(max((t - descend_s - hold_s) / return_s, 0.0), 1.0))
    return 0.0


def native_ik_eval(
    *,
    drop: float,
    max_blend: float,
    policy_weight: float,
    descend_s: float,
    hold_s: float,
    return_s: float,
    seconds: float,
    params_path: Path,
    out_dir: Path,
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
    ik = solve_foot_fixed_target(model, key.qpos.copy(), foot_site_ids, drop)
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
    max_foot_slip = 0.0
    both_feet_contact_count = 0
    max_joint_violation = 0.0
    torso_up_min_observed = float("inf")
    max_observed_blend = 0.0
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

        height = float(data.qpos[2])
        final_height = height
        min_height = min(min_height, height)
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

        current_blend = blend_profile(t, descend_s, hold_s, return_s, max_blend)
        max_observed_blend = max(max_observed_blend, current_blend)
        policy_targets = default_pose + policy_weight * action_np * float(env._config.action_scale)
        data.ctrl[:] = (1.0 - current_blend) * policy_targets + current_blend * ik_target
        for _ in range(n_substeps):
            mujoco.mj_step(model, data)
        if trajectory_out is not None:
            qpos_frames.append([float(v) for v in data.qpos[: model.nq]])
        last_action = action_np

        if step % max(1, int(0.2 / ctrl_dt)) == 0:
            samples.append({
                "t": round(t, 3),
                "base_height": height,
                "visible_drop": start_height - height,
                "up_z": up_z,
                "both_feet_contact": both_feet,
                "foot_slip_distance": foot_slip,
                "controller_blend": current_blend,
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
        verdict = "PASS_IK_VISIBLE_SQUAT_NATIVE"
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
        "drop": drop,
        "max_blend": max_blend,
        "policy_weight": policy_weight,
        "descend_s": descend_s,
        "hold_s": hold_s,
        "return_s": return_s,
        "seconds": seconds,
        "params_path": str(params_path),
        "ik": ik,
        "start_height": start_height,
        "min_height": min_height,
        "visible_drop": visible_drop,
        "fell_at": fell_at,
        "upright_s": seconds if fell_at is None else fell_at,
        "final_height": final_height,
        "return_to_stand": return_to_stand,
        "torso_up_min_observed": torso_up_min_observed,
        "foot_contact_ratio": foot_contact_ratio,
        "foot_slip_distance": max_foot_slip,
        "stance_ok": stance_ok,
        "max_joint_limit_violation": max_joint_violation,
        "max_observed_blend": max_observed_blend,
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
            "note": "G1 foot-fixed IK squat replay from exp36.",
            "source_attempt": out_dir.name,
            "qpos": qpos_frames,
        }
        trajectory_out.write_text(json.dumps(trajectory), encoding="utf-8")
        native["trajectory_out"] = str(trajectory_out)
    (out_dir / "ik-native-eval.json").write_text(json.dumps(native, indent=2), encoding="utf-8")
    return native


def write_summary(results: list[dict]) -> None:
    lines = [
        "# G1 WBC/IK Squat Prototype Summary",
        "",
        "| Attempt | Verdict | IK max foot err | Drop | Fell at | Contact | Final height | Slip |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for result in results:
        native = result["native"]
        fell = "never" if native["fell_at"] is None else f"{native['fell_at']:.2f}s"
        lines.append(
            f"| {result['attempt']} | {native['verdict']} | {native['ik']['max_foot_error']:.4f}m | "
            f"{native['visible_drop']:.4f}m | {fell} | {native['foot_contact_ratio']:.2f} | "
            f"{native['final_height']:.4f}m | {native['foot_slip_distance']:.3f}m |"
        )
    lines.extend([
        "",
        "M19 is closed only if visible depth, no-fall, stance/contact, return, and browser replay gates pass together.",
    ])
    (VERIFY / "ik-squat-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=None)
    parser.add_argument("--drop", type=float, default=0.08)
    parser.add_argument("--max-blend", type=float, default=0.75)
    parser.add_argument("--policy-weight", type=float, default=1.0)
    parser.add_argument("--descend-s", type=float, default=2.0)
    parser.add_argument("--hold-s", type=float, default=0.7)
    parser.add_argument("--return-s", type=float, default=1.8)
    parser.add_argument("--seconds", type=float, default=6.0)
    parser.add_argument("--attempt", default=None)
    parser.add_argument("--trajectory-out", type=Path, default=None)
    parser.add_argument("--sweep", action="store_true")
    args = parser.parse_args()

    source = args.source or EXP28.default_source()
    variants = [
        ("ik-drop-0p08-blend-0p25", 0.08, 0.25, 1.0, 3.0, 0.2, 2.4),
        ("ik-drop-0p08-blend-0p35", 0.08, 0.35, 1.0, 3.0, 0.2, 2.4),
        ("ik-drop-0p06-blend-0p55", 0.06, 0.55, 1.0, 2.4, 0.4, 2.2),
        ("ik-drop-0p08-blend-0p55", 0.08, 0.55, 1.0, 2.8, 0.4, 2.4),
        ("ik-drop-0p08-blend-0p75", 0.08, 0.75, 1.0, 2.8, 0.4, 2.4),
        ("ik-drop-0p08-no-policy", 0.08, 0.55, 0.0, 2.8, 0.4, 2.4),
    ] if args.sweep else [
        (
            args.attempt or f"ik-drop-{slug_float(args.drop)}-blend-{slug_float(args.max_blend)}",
            args.drop,
            args.max_blend,
            args.policy_weight,
            args.descend_s,
            args.hold_s,
            args.return_s,
        )
    ]

    VERIFY.mkdir(parents=True, exist_ok=True)
    results = []
    for name, drop, max_blend, policy_weight, descend_s, hold_s, return_s in variants:
        attempt_dir = VERIFY / "attempts" / name
        attempt_dir.mkdir(parents=True, exist_ok=True)
        trajectory_out = args.trajectory_out
        if args.sweep and trajectory_out is not None:
            trajectory_out = trajectory_out.with_name(f"{trajectory_out.stem}-{name}{trajectory_out.suffix}")
        result = {
            "attempt": name,
            "source_params": str(source),
            "native": native_ik_eval(
                drop=drop,
                max_blend=max_blend,
                policy_weight=policy_weight,
                descend_s=descend_s,
                hold_s=hold_s,
                return_s=return_s,
                seconds=args.seconds,
                params_path=source,
                out_dir=attempt_dir,
                trajectory_out=trajectory_out,
            ),
        }
        (attempt_dir / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        results.append(result)

    write_summary(results)
    print(json.dumps({"attempts": [{"attempt": r["attempt"], **r["native"]} for r in results]}, indent=2), flush=True)


if __name__ == "__main__":
    main()
