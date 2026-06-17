"""Probe reference-offset action targets for G1 squat.

This does not train a new policy. It reinterprets the same stabilizer policy
action either around the default pose or around the staged squat reference pose
to test whether action-target architecture gives the policy depth leverage.
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
EXP37_PATH = ROOT / "experiments/37-g1-com-support-squat-guard/run_support_guard.py"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EXP28 = load_module("exp28_controlled_squat", EXP28_PATH)
EXP37 = load_module("exp37_support_guard", EXP37_PATH)


def native_reference_offset_eval(
    *,
    attempt: str,
    mode: str,
    stage_height: float,
    reference_gain: float,
    ramp_s: float,
    residual_scale: float,
    seconds: float,
    params_path: Path,
    out_dir: Path,
) -> dict:
    env = EXP28.ContactAwareSquat(
        stage_height=stage_height,
        controller_blend=0.0,
        freeze_phase=True,
        blend_schedule="squat",
        reference_scale=1.0,
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
    phase = np.ones(2, dtype=np.float32) * np.pi
    command = np.zeros(3, dtype=np.float32)
    last_action = np.zeros(env.action_size, dtype=np.float32)
    gravity_down = np.array([0.0, 0.0, -1.0], dtype=np.float32)
    rng = jax.random.PRNGKey(0)
    foot_site_ids = np.asarray(env._feet_site_id)
    initial_foot_xy = data.site_xpos[foot_site_ids, :2].copy()
    foot_contact_sensor_ids = list(env._feet_floor_found_sensor)
    foot_geom_ids = np.asarray([model.geom("left_foot").id, model.geom("right_foot").id])

    start_height = float(data.qpos[2])
    min_height = start_height
    final_height = start_height
    fell_at = None
    first_visible_at = None
    first_support_breach_at = None
    both_feet_contact_count = 0
    hold_count = 0
    max_foot_slip = 0.0
    min_support_margin = float("inf")
    max_downward_velocity = 0.0
    max_joint_violation = 0.0
    max_reference_error = 0.0
    max_height_error = 0.0
    samples = []
    qpos_frames = []
    last_height = start_height

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

        ref_index = min(step, len(ref_heights) - 1)
        reference_pose = default_pose.copy()
        reference_pose[:15] = ref_joints[ref_index]
        height = float(data.qpos[2])
        final_height = height
        min_height = min(min_height, height)
        visible_drop = start_height - height
        if visible_drop >= 0.08 and first_visible_at is None:
            first_visible_at = round(t, 3)
        vertical_velocity = (height - last_height) / ctrl_dt if step > 0 else 0.0
        max_downward_velocity = min(max_downward_velocity, vertical_velocity)
        support = EXP37.support_metrics(model, data, foot_geom_ids)
        min_support_margin = min(min_support_margin, support["support_margin"])
        if support["support_margin"] < 0.0 and first_support_breach_at is None:
            first_support_breach_at = round(t, 3)
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
        if height <= stage_height + 0.005 and both_feet:
            hold_count += 1
        foot_slip = float(np.max(np.linalg.norm(data.site_xpos[foot_site_ids, :2] - initial_foot_xy, axis=1)))
        max_foot_slip = max(max_foot_slip, foot_slip)
        if (height < 0.45 or up_z < 0.30) and fell_at is None:
            fell_at = round(t, 3)
        reference_error = float(np.mean(np.square(data.qpos[7:22] - ref_joints[ref_index])))
        height_error = float((height - float(ref_heights[ref_index])) ** 2)
        max_reference_error = max(max_reference_error, reference_error)
        max_height_error = max(max_height_error, height_error)
        max_joint_violation = max(max_joint_violation, EXP28.joint_limit_violation(model, data))

        if mode == "default-offset":
            target = default_pose + action_np * float(env._config.action_scale)
        elif mode == "reference-offset":
            target = reference_pose + residual_scale * action_np * float(env._config.action_scale)
        elif mode == "reference-ramp":
            blend = reference_gain * min(max(t / max(ramp_s, ctrl_dt), 0.0), 1.0)
            moving_pose = default_pose + blend * (reference_pose - default_pose)
            target = moving_pose + residual_scale * action_np * float(env._config.action_scale)
        elif mode == "reference-only":
            target = reference_pose
        else:
            raise ValueError(f"unknown mode: {mode}")
        data.ctrl[:] = np.clip(target, model.actuator_ctrlrange[:, 0], model.actuator_ctrlrange[:, 1])
        for _ in range(n_substeps):
            mujoco.mj_step(model, data)
        qpos_frames.append([float(v) for v in data.qpos[: model.nq]])
        last_action = action_np
        last_height = height

        if step % max(1, int(0.2 / ctrl_dt)) == 0:
            samples.append({
                "t": round(t, 3),
                "base_height": height,
                "visible_drop": visible_drop,
                "target_height": float(ref_heights[ref_index]),
                "up_z": up_z,
                "both_feet_contact": both_feet,
                "foot_slip_distance": foot_slip,
                "support_margin": support["support_margin"],
                "vertical_velocity": vertical_velocity,
                "reference_error": reference_error,
                "height_error": height_error,
            })

    visible_drop = start_height - min_height
    hold_duration = hold_count * ctrl_dt
    foot_contact_ratio = both_feet_contact_count / max(1, total_steps)
    return_to_stand = final_height >= 0.74
    pass_gate = (
        fell_at is None
        and visible_drop >= 0.08
        and hold_duration >= 0.5
        and return_to_stand
        and foot_contact_ratio >= 0.90
        and max_foot_slip <= 0.15
        and max_joint_violation <= 0.05
    )
    if pass_gate:
        verdict = "PASS_REFERENCE_OFFSET_VISIBLE_SQUAT"
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
        "mode": mode,
        "stage_height": stage_height,
        "reference_gain": reference_gain,
        "ramp_s": ramp_s,
        "residual_scale": residual_scale,
        "params_path": str(params_path),
        "seconds": seconds,
        "start_height": start_height,
        "min_height": min_height,
        "visible_drop": visible_drop,
        "first_visible_at": first_visible_at,
        "fell_at": fell_at,
        "upright_s": seconds if fell_at is None else fell_at,
        "hold_duration_at_or_below_stage": hold_duration,
        "final_height": final_height,
        "return_to_stand": return_to_stand,
        "foot_contact_ratio": foot_contact_ratio,
        "foot_slip_distance": max_foot_slip,
        "min_support_margin": min_support_margin,
        "first_support_breach_at": first_support_breach_at,
        "max_downward_velocity": max_downward_velocity,
        "max_reference_error": max_reference_error,
        "max_height_error": max_height_error,
        "max_joint_limit_violation": max_joint_violation,
        "pass_gate": pass_gate,
        "verdict": verdict,
        "samples": samples,
    }
    (out_dir / "native-eval.json").write_text(json.dumps(native, indent=2), encoding="utf-8")
    return native


def write_summary(results: list[dict]) -> None:
    lines = [
        "# G1 Reference-Offset Action Probe Summary",
        "",
        "| Attempt | Verdict | Drop | Fell at | Contact | Final height | Support min | Slip |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for native in results:
        fell = "never" if native["fell_at"] is None else f"{native['fell_at']:.2f}s"
        lines.append(
            f"| {native['attempt']} | {native['verdict']} | {native['visible_drop']:.4f}m | "
            f"{fell} | {native['foot_contact_ratio']:.2f} | {native['final_height']:.4f}m | "
            f"{native['min_support_margin']:.4f}m | {native['foot_slip_distance']:.3f}m |"
        )
    lines.extend([
        "",
        "M19 closes only when visible depth, no-fall, contact, stance, return, and browser replay gates pass together.",
    ])
    (VERIFY / "reference-offset-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=None)
    parser.add_argument("--seconds", type=float, default=6.0)
    parser.add_argument("--sweep", action="store_true")
    args = parser.parse_args()

    source = args.source or EXP28.default_source()
    variants = [
        ("default-stage-0p74", "default-offset", 0.74, 1.0, 0.0, 1.0),
        ("ramp-stage-0p74-gain-0p25", "reference-ramp", 0.74, 0.25, 3.0, 1.0),
        ("ramp-stage-0p74-gain-0p50", "reference-ramp", 0.74, 0.50, 3.0, 1.0),
        ("ramp-stage-0p67-gain-0p50", "reference-ramp", 0.67, 0.50, 3.0, 1.0),
        ("ref-stage-0p74-resid-0p25", "reference-offset", 0.74, 1.0, 0.0, 0.25),
        ("ref-stage-0p67-reference-only", "reference-only", 0.67, 1.0, 0.0, 0.0),
    ] if args.sweep else [
        ("ramp-stage-0p74-gain-0p25", "reference-ramp", 0.74, 0.25, 3.0, 1.0),
    ]

    VERIFY.mkdir(parents=True, exist_ok=True)
    results = []
    for name, mode, stage_height, reference_gain, ramp_s, residual_scale in variants:
        out_dir = VERIFY / "attempts" / name
        out_dir.mkdir(parents=True, exist_ok=True)
        native = native_reference_offset_eval(
            attempt=name,
            mode=mode,
            stage_height=stage_height,
            reference_gain=reference_gain,
            ramp_s=ramp_s,
            residual_scale=residual_scale,
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
