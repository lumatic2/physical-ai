"""Run guarded native G1 squat descent attempts.

This keeps the exp28 policy/env path and changes only the native reference-blend
state machine so M19 can test controller design before more reward tuning.
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
EXP28_PATH = ROOT / "experiments/28-g1-controlled-squat-stage0p74/run_controlled_squat.py"


def load_exp28():
    spec = importlib.util.spec_from_file_location("exp28_controlled_squat", EXP28_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {EXP28_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EXP28 = load_exp28()


def attempt_slug(name: str | None, max_blend: float, descent_rate_cap: float) -> str:
    if name:
        return name
    blend = f"{max_blend:.2f}".replace(".", "p")
    rate = f"{descent_rate_cap:.3f}".replace(".", "p")
    return f"maxblend-{blend}-rate-{rate}"


def native_guarded_eval(
    *,
    stage_height: float,
    max_blend: float,
    descent_rate_cap: float,
    torso_up_min: float,
    foot_slip_max: float,
    freeze_phase: bool,
    reference_scale: float | None,
    params_path: Path,
    seconds: float,
    out_dir: Path,
    trajectory_out: Path | None,
) -> dict:
    env = EXP28.ContactAwareSquat(
        stage_height=stage_height,
        controller_blend=max_blend,
        freeze_phase=freeze_phase,
        blend_schedule="squat",
        reference_scale=reference_scale,
        config_overrides={"impl": "jax"},
    )
    policy = EXP28.build_policy(env, params_path)
    ref_joints = np.asarray(env._ref_joints, dtype=np.float32)
    ref_heights = np.asarray(env._ref_heights, dtype=np.float32)
    model = env.mj_model
    data = mujoco.MjData(model)
    key = model.keyframe("knees_bent")
    data.qpos[:] = key.qpos
    default_pose = key.qpos[7:].astype(np.float32).copy()
    data.ctrl[:] = default_pose
    mujoco.mj_forward(model, data)

    gyro_adr = EXP28.sensor_adr(model, "gyro_pelvis")
    linvel_adr = EXP28.sensor_adr(model, "local_linvel_pelvis")
    imu_site = model.site("imu_in_pelvis").id
    ctrl_dt = float(env.dt)
    sim_dt = float(model.opt.timestep)
    n_substeps = max(1, round(ctrl_dt / sim_dt))
    total_steps = int(seconds / ctrl_dt)
    phase = np.ones(2, dtype=np.float32) * np.pi if freeze_phase else np.array([0.0, np.pi], dtype=np.float32)
    phase_dt = float(2 * np.pi * ctrl_dt * 1.375)
    last_action = np.zeros(env.action_size, dtype=np.float32)
    command = np.zeros(3, dtype=np.float32)
    gravity_down = np.array([0.0, 0.0, -1.0], dtype=np.float32)
    rng = jax.random.PRNGKey(0)
    foot_site_ids = np.asarray(env._feet_site_id)
    initial_foot_xy = data.site_xpos[foot_site_ids, :2].copy()
    foot_contact_sensor_ids = list(env._feet_floor_found_sensor)

    start_height = float(data.qpos[2])
    last_height = start_height
    fell_at = None
    min_height = start_height
    final_height = start_height
    torso_up_min_observed = float("inf")
    max_reference_error = 0.0
    max_height_error = 0.0
    max_joint_violation = 0.0
    max_foot_slip = 0.0
    both_feet_contact_count = 0
    hold_count = 0
    guard_trip_count = 0
    max_observed_blend = 0.0
    current_blend = 0.0
    samples = []
    qpos_frames = []

    def schedule(step: int) -> float:
        t = step * ctrl_dt
        if t < 1.8:
            return max_blend * min(max(t / 1.8, 0.0), 1.0)
        if t < 3.5:
            return max_blend
        if t < 4.7:
            return max_blend * min(max(1.0 - (t - 3.5) / 1.2, 0.0), 1.0)
        return 0.0

    for step in range(total_steps):
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

        ref_index = min(step, len(ref_heights) - 1)
        height = float(data.qpos[2])
        final_height = height
        drop_rate = max(0.0, (last_height - height) / ctrl_dt)
        reference_error = float(np.mean(np.square(data.qpos[7:22] - ref_joints[ref_index])))
        height_error = float((height - float(ref_heights[ref_index])) ** 2)
        quat = data.qpos[3:7]
        mat = np.empty(9)
        mujoco.mju_quat2Mat(mat, quat)
        up_z = float(mat.reshape(3, 3)[2, 2])
        contacts = [
            float(data.sensordata[model.sensor_adr[sensor_id]]) > 0
            for sensor_id in foot_contact_sensor_ids
        ]
        both_feet = all(contacts)
        both_feet_contact_count += int(both_feet)
        foot_slip = float(np.max(np.linalg.norm(data.site_xpos[foot_site_ids, :2] - initial_foot_xy, axis=1)))
        fallen = height < 0.45 or up_z < 0.30
        if fallen and fell_at is None:
            fell_at = round(step * ctrl_dt, 3)
        if height <= stage_height + 0.005 and both_feet:
            hold_count += 1

        desired_blend = schedule(step)
        guard_reasons = []
        if drop_rate > descent_rate_cap:
            guard_reasons.append("descent_rate")
        if up_z < torso_up_min:
            guard_reasons.append("torso_up")
        if foot_slip > foot_slip_max:
            guard_reasons.append("foot_slip")
        if not both_feet:
            guard_reasons.append("foot_contact")

        if guard_reasons:
            guard_trip_count += 1
            current_blend = max(0.0, min(current_blend, desired_blend) * 0.72)
        else:
            current_blend = min(desired_blend, current_blend + 0.018)

        min_height = min(min_height, height)
        torso_up_min_observed = min(torso_up_min_observed, up_z)
        max_reference_error = max(max_reference_error, reference_error)
        max_height_error = max(max_height_error, height_error)
        max_joint_violation = max(max_joint_violation, EXP28.joint_limit_violation(model, data))
        max_foot_slip = max(max_foot_slip, foot_slip)
        max_observed_blend = max(max_observed_blend, current_blend)

        policy_targets = default_pose + action_np * float(env._config.action_scale)
        staged_pose = default_pose.copy()
        staged_pose[:15] = ref_joints[ref_index]
        data.ctrl[:] = (1.0 - current_blend) * policy_targets + current_blend * staged_pose
        for _ in range(n_substeps):
            mujoco.mj_step(model, data)
        if trajectory_out is not None:
            qpos_frames.append([float(v) for v in data.qpos[: model.nq]])
        if freeze_phase:
            phase = np.ones(2, dtype=np.float32) * np.pi
        else:
            phase = np.fmod(phase + phase_dt + np.pi, 2 * np.pi) - np.pi
        last_action = action_np
        last_height = height

        if step % max(1, int(0.2 / ctrl_dt)) == 0:
            samples.append({
                "t": round(step * ctrl_dt, 3),
                "base_height": height,
                "target_height": float(ref_heights[ref_index]),
                "visible_drop": start_height - height,
                "drop_rate": drop_rate,
                "reference_error": reference_error,
                "height_error": height_error,
                "up_z": up_z,
                "both_feet_contact": both_feet,
                "foot_slip_distance": foot_slip,
                "guarded_blend": current_blend,
                "guard_reasons": guard_reasons,
            })

    hold_duration = hold_count * ctrl_dt
    foot_contact_ratio = both_feet_contact_count / max(1, total_steps)
    visible_drop = start_height - min_height
    return_to_stand = final_height >= 0.74
    pass_gate = (
        fell_at is None
        and visible_drop >= 0.08
        and hold_duration >= 0.30
        and return_to_stand
        and foot_contact_ratio >= 0.90
        and max_joint_violation <= 0.05
    )
    if pass_gate:
        verdict = "PASS_GUARDED_VISIBLE_SQUAT"
    elif fell_at is not None:
        verdict = "FAIL_FALL"
    elif visible_drop < 0.08:
        verdict = "DEPTH_PENDING"
    elif not return_to_stand:
        verdict = "RETURN_PENDING"
    elif foot_contact_ratio < 0.90:
        verdict = "CONTACT_GATE_PENDING"
    else:
        verdict = "GATE_PENDING"

    native = {
        "stage_height": stage_height,
        "max_blend": max_blend,
        "descent_rate_cap": descent_rate_cap,
        "torso_up_min": torso_up_min,
        "foot_slip_max": foot_slip_max,
        "freeze_phase": freeze_phase,
        "reference_scale": reference_scale,
        "params_path": str(params_path),
        "seconds": seconds,
        "start_height": start_height,
        "min_height": min_height,
        "visible_drop": visible_drop,
        "fell_at": fell_at,
        "upright_s": seconds if fell_at is None else fell_at,
        "hold_duration_at_or_below_stage": hold_duration,
        "final_height": final_height,
        "return_to_stand": return_to_stand,
        "torso_up_min_observed": torso_up_min_observed,
        "foot_contact_ratio": foot_contact_ratio,
        "foot_slip_distance": max_foot_slip,
        "max_reference_error": max_reference_error,
        "max_height_error": max_height_error,
        "max_joint_limit_violation": max_joint_violation,
        "guard_trip_count": guard_trip_count,
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
            "note": "G1 guarded descent squat replay from exp34.",
            "source_attempt": out_dir.name,
            "qpos": qpos_frames,
        }
        trajectory_out.write_text(json.dumps(trajectory), encoding="utf-8")
        native["trajectory_out"] = str(trajectory_out)
    (out_dir / "guarded-native-eval.json").write_text(json.dumps(native, indent=2), encoding="utf-8")
    return native


def write_summary(attempts: list[dict]) -> None:
    lines = [
        "# G1 Guarded Descent Summary",
        "",
        "| Attempt | Verdict | Drop | Fell at | Contact | Final height | Guard trips | Max blend |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for result in attempts:
        native = result["native"]
        fell = "never" if native["fell_at"] is None else f"{native['fell_at']:.2f}s"
        lines.append(
            f"| {result['attempt']} | {native['verdict']} | {native['visible_drop']:.4f}m | {fell} | "
            f"{native['foot_contact_ratio']:.2f} | {native['final_height']:.4f}m | "
            f"{native['guard_trip_count']} | {native['max_observed_blend']:.2f} |"
        )
    lines.extend([
        "",
        "M19 is closed only if a run passes visible depth, no-fall, contact, return, and browser replay gates.",
    ])
    (VERIFY / "guarded-descent-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=None)
    parser.add_argument("--stage-height", type=float, default=0.67)
    parser.add_argument("--seconds", type=float, default=6.0)
    parser.add_argument("--max-blend", type=float, default=0.85)
    parser.add_argument("--descent-rate-cap", type=float, default=0.055)
    parser.add_argument("--torso-up-min", type=float, default=0.55)
    parser.add_argument("--foot-slip-max", type=float, default=0.08)
    parser.add_argument("--reference-scale", type=float, default=1.0)
    parser.add_argument("--freeze-phase", action="store_true")
    parser.add_argument("--attempt", default=None)
    parser.add_argument("--trajectory-out", type=Path, default=None)
    parser.add_argument("--sweep", action="store_true")
    args = parser.parse_args()

    source = args.source or EXP28.default_source()
    variants = [
        ("conservative", 0.65, 0.035),
        ("medium", 0.85, 0.055),
        ("assertive", 1.0, 0.075),
    ] if args.sweep else [
        (attempt_slug(args.attempt, args.max_blend, args.descent_rate_cap), args.max_blend, args.descent_rate_cap)
    ]

    VERIFY.mkdir(parents=True, exist_ok=True)
    attempts = []
    for name, max_blend, rate_cap in variants:
        attempt_dir = VERIFY / "attempts" / name
        attempt_dir.mkdir(parents=True, exist_ok=True)
        trajectory_out = args.trajectory_out
        if args.sweep and trajectory_out is not None:
            trajectory_out = trajectory_out.with_name(f"{trajectory_out.stem}-{name}{trajectory_out.suffix}")
        result = {
            "attempt": name,
            "source_params": str(source),
            "compatibility": EXP28.compatibility(
                source,
                args.stage_height,
                max_blend,
                args.freeze_phase,
                "squat",
                args.reference_scale,
            ),
        }
        if not result["compatibility"]["policy_shape_match"]:
            raise SystemExit("source and target policy shapes do not match")
        result["native"] = native_guarded_eval(
            stage_height=args.stage_height,
            max_blend=max_blend,
            descent_rate_cap=rate_cap,
            torso_up_min=args.torso_up_min,
            foot_slip_max=args.foot_slip_max,
            freeze_phase=args.freeze_phase,
            reference_scale=args.reference_scale,
            params_path=source,
            seconds=args.seconds,
            out_dir=attempt_dir,
            trajectory_out=trajectory_out,
        )
        (attempt_dir / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        attempts.append(result)

    write_summary(attempts)
    print(json.dumps({"attempts": [{ "attempt": r["attempt"], **r["native"] } for r in attempts]}, indent=2), flush=True)


if __name__ == "__main__":
    main()
