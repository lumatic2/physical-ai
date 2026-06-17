"""Run stance-anchored native G1 squat attempts.

The experiment keeps the exp34 native policy/env path but changes the controller
from a time-only guarded descent into a descend/return/abort state machine.
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
EXP34_PATH = ROOT / "experiments/34-g1-guarded-descent-controller/run_guarded_descent.py"


def load_exp34():
    spec = importlib.util.spec_from_file_location("exp34_guarded_descent", EXP34_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {EXP34_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EXP34 = load_exp34()
EXP28 = EXP34.EXP28


def slug_float(value: float) -> str:
    return f"{value:.3f}".rstrip("0").rstrip(".").replace(".", "p")


def native_stance_anchor_eval(
    *,
    stage_height: float,
    max_blend: float,
    target_drop: float,
    descent_rate_cap: float,
    slip_abort: float,
    return_blend: float,
    return_rate: float,
    policy_weight: float,
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
    min_height = start_height
    final_height = start_height
    fell_at = None
    mode = "descend"
    mode_counts = {"descend": 0, "return": 0, "abort": 0}
    trigger_reason = None
    trigger_time = None
    current_blend = 0.0
    return_mix = 0.0
    guard_trip_count = 0
    max_observed_blend = 0.0
    max_return_mix = 0.0
    torso_up_min_observed = float("inf")
    max_reference_error = 0.0
    max_height_error = 0.0
    max_joint_violation = 0.0
    max_foot_slip = 0.0
    both_feet_contact_count = 0
    visible_contact_count = 0
    qpos_frames = []
    samples = []

    def descent_schedule(step: int) -> float:
        t = step * ctrl_dt
        return max_blend * min(max(t / 1.8, 0.0), 1.0)

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
        visible_drop = start_height - height
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
        if visible_drop >= 0.08 and both_feet:
            visible_contact_count += 1

        fallen = height < 0.45 or up_z < 0.30
        if fallen and fell_at is None:
            fell_at = round(step * ctrl_dt, 3)

        if mode == "descend":
            if visible_drop >= target_drop:
                mode = "return"
                trigger_reason = "visible_drop"
                trigger_time = round(step * ctrl_dt, 3)
            elif foot_slip > slip_abort:
                mode = "return"
                trigger_reason = "slip_abort"
                trigger_time = round(step * ctrl_dt, 3)
            elif not both_feet:
                mode = "abort"
                trigger_reason = "contact_loss"
                trigger_time = round(step * ctrl_dt, 3)
            elif drop_rate > descent_rate_cap:
                guard_trip_count += 1
                current_blend *= 0.72
            else:
                current_blend = min(descent_schedule(step), current_blend + 0.02)
        elif mode == "return":
            current_blend = max(0.0, current_blend - 0.035)
            return_mix = min(return_blend, return_mix + return_rate)
            if foot_slip > slip_abort * 2.5 or not both_feet:
                mode = "abort"
                if trigger_reason == "visible_drop":
                    trigger_reason = "visible_then_abort"
        else:
            current_blend = 0.0
            return_mix = min(return_blend, return_mix + return_rate)

        mode_counts[mode] += 1
        min_height = min(min_height, height)
        torso_up_min_observed = min(torso_up_min_observed, up_z)
        max_reference_error = max(max_reference_error, reference_error)
        max_height_error = max(max_height_error, height_error)
        max_joint_violation = max(max_joint_violation, EXP28.joint_limit_violation(model, data))
        max_foot_slip = max(max_foot_slip, foot_slip)
        max_observed_blend = max(max_observed_blend, current_blend)
        max_return_mix = max(max_return_mix, return_mix)

        policy_targets = default_pose + policy_weight * action_np * float(env._config.action_scale)
        staged_pose = default_pose.copy()
        staged_pose[:15] = ref_joints[ref_index]
        descend_targets = (1.0 - current_blend) * policy_targets + current_blend * staged_pose
        data.ctrl[:] = (1.0 - return_mix) * descend_targets + return_mix * default_pose
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
                "mode": mode,
                "base_height": height,
                "target_height": float(ref_heights[ref_index]),
                "visible_drop": visible_drop,
                "drop_rate": drop_rate,
                "up_z": up_z,
                "both_feet_contact": both_feet,
                "foot_slip_distance": foot_slip,
                "controller_blend": current_blend,
                "return_mix": return_mix,
            })

    foot_contact_ratio = both_feet_contact_count / max(1, total_steps)
    visible_contact_ratio = visible_contact_count / max(1, total_steps)
    visible_drop_max = start_height - min_height
    return_to_stand = final_height >= 0.74
    stance_ok = max_foot_slip <= 0.15
    pass_gate = (
        fell_at is None
        and visible_drop_max >= 0.08
        and return_to_stand
        and foot_contact_ratio >= 0.90
        and stance_ok
        and max_joint_violation <= 0.05
    )
    if pass_gate:
        verdict = "PASS_STANCE_ANCHORED_VISIBLE_SQUAT"
    elif fell_at is not None:
        verdict = "FAIL_FALL"
    elif visible_drop_max < 0.08:
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
        "stage_height": stage_height,
        "max_blend": max_blend,
        "target_drop": target_drop,
        "descent_rate_cap": descent_rate_cap,
        "slip_abort": slip_abort,
        "return_blend": return_blend,
        "return_rate": return_rate,
        "policy_weight": policy_weight,
        "freeze_phase": freeze_phase,
        "reference_scale": reference_scale,
        "params_path": str(params_path),
        "seconds": seconds,
        "start_height": start_height,
        "min_height": min_height,
        "visible_drop": visible_drop_max,
        "fell_at": fell_at,
        "upright_s": seconds if fell_at is None else fell_at,
        "final_height": final_height,
        "return_to_stand": return_to_stand,
        "torso_up_min_observed": torso_up_min_observed,
        "foot_contact_ratio": foot_contact_ratio,
        "visible_contact_ratio": visible_contact_ratio,
        "foot_slip_distance": max_foot_slip,
        "stance_ok": stance_ok,
        "max_reference_error": max_reference_error,
        "max_height_error": max_height_error,
        "max_joint_limit_violation": max_joint_violation,
        "guard_trip_count": guard_trip_count,
        "max_observed_blend": max_observed_blend,
        "max_return_mix": max_return_mix,
        "trigger_reason": trigger_reason,
        "trigger_time": trigger_time,
        "mode_counts": mode_counts,
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
            "note": "G1 stance-anchored squat replay from exp35.",
            "source_attempt": out_dir.name,
            "qpos": qpos_frames,
        }
        trajectory_out.write_text(json.dumps(trajectory), encoding="utf-8")
        native["trajectory_out"] = str(trajectory_out)
    (out_dir / "stance-anchor-native-eval.json").write_text(json.dumps(native, indent=2), encoding="utf-8")
    return native


def write_summary(results: list[dict]) -> None:
    lines = [
        "# G1 Stance Anchor Summary",
        "",
        "| Attempt | Verdict | Drop | Fell at | Contact | Final height | Slip | Trigger |",
        "|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for result in results:
        native = result["native"]
        fell = "never" if native["fell_at"] is None else f"{native['fell_at']:.2f}s"
        trigger = native["trigger_reason"] or "-"
        lines.append(
            f"| {result['attempt']} | {native['verdict']} | {native['visible_drop']:.4f}m | {fell} | "
            f"{native['foot_contact_ratio']:.2f} | {native['final_height']:.4f}m | "
            f"{native['foot_slip_distance']:.3f}m | {trigger} @ {native['trigger_time']} |"
        )
    lines.extend([
        "",
        "M19 is closed only if visible depth, no-fall, contact, stance, return, and browser replay gates pass together.",
    ])
    (VERIFY / "stance-anchor-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=None)
    parser.add_argument("--stage-height", type=float, default=0.67)
    parser.add_argument("--seconds", type=float, default=6.0)
    parser.add_argument("--max-blend", type=float, default=1.0)
    parser.add_argument("--target-drop", type=float, default=0.08)
    parser.add_argument("--descent-rate-cap", type=float, default=0.10)
    parser.add_argument("--slip-abort", type=float, default=0.03)
    parser.add_argument("--return-blend", type=float, default=1.0)
    parser.add_argument("--return-rate", type=float, default=0.08)
    parser.add_argument("--policy-weight", type=float, default=1.0)
    parser.add_argument("--reference-scale", type=float, default=1.0)
    parser.add_argument("--freeze-phase", action="store_true")
    parser.add_argument("--attempt", default=None)
    parser.add_argument("--trajectory-out", type=Path, default=None)
    parser.add_argument("--sweep", action="store_true")
    args = parser.parse_args()

    source = args.source or EXP28.default_source()
    variants = [
        ("early-visible-return", 1.0, 0.080, 0.10, 0.030, 1.0, 0.08, 1.0),
        ("preemptive-return", 0.95, 0.070, 0.08, 0.025, 1.0, 0.10, 1.0),
        ("stance-tight", 0.90, 0.075, 0.07, 0.020, 1.0, 0.12, 1.0),
    ] if args.sweep else [
        (
            args.attempt or (
                f"blend-{slug_float(args.max_blend)}-drop-{slug_float(args.target_drop)}-"
                f"slip-{slug_float(args.slip_abort)}"
            ),
            args.max_blend,
            args.target_drop,
            args.descent_rate_cap,
            args.slip_abort,
            args.return_blend,
            args.return_rate,
            args.policy_weight,
        )
    ]

    VERIFY.mkdir(parents=True, exist_ok=True)
    results = []
    for name, max_blend, target_drop, rate_cap, slip_abort, return_blend, return_rate, policy_weight in variants:
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
        result["native"] = native_stance_anchor_eval(
            stage_height=args.stage_height,
            max_blend=max_blend,
            target_drop=target_drop,
            descent_rate_cap=rate_cap,
            slip_abort=slip_abort,
            return_blend=return_blend,
            return_rate=return_rate,
            policy_weight=policy_weight,
            freeze_phase=args.freeze_phase,
            reference_scale=args.reference_scale,
            params_path=source,
            seconds=args.seconds,
            out_dir=attempt_dir,
            trajectory_out=trajectory_out,
        )
        (attempt_dir / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        results.append(result)

    write_summary(results)
    print(json.dumps({"attempts": [{"attempt": r["attempt"], **r["native"]} for r in results]}, indent=2), flush=True)


if __name__ == "__main__":
    main()
