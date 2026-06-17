"""Phase-conditioned visible-target trajectory probe for G1 squat."""

from __future__ import annotations

import argparse
import importlib.util
import json
from dataclasses import dataclass
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
EXP42_PATH = ROOT / "experiments/42-g1-contact-inverse-force-probe/run_force_probe.py"
EXP45_BEST = ROOT / "experiments/45-g1-stance-stable-manifold/verify/attempts/drop-0p12-com12-posture0p3/result.json"
EXP46_PARAMS = ROOT / "experiments/46-g1-force-torque-residual/verify/stage-0p74/attempts/force-torque-20k/train/params.pkl"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EXP28 = load_module("exp28_controlled_squat", EXP28_PATH)
EXP37 = load_module("exp37_support_guard", EXP37_PATH)
EXP42 = load_module("exp42_force_probe", EXP42_PATH)


@dataclass(frozen=True)
class Variant:
    name: str
    max_gain: float
    target_drop: float
    support_floor: float
    slip_floor: float
    up_z_floor: float
    descend_rate: float
    return_rate: float
    policy_weight: float = 1.0


def default_source() -> Path:
    return EXP46_PARAMS if EXP46_PARAMS.exists() else EXP28.default_source()


def load_visible_delta(default_pose: np.ndarray) -> np.ndarray:
    payload = json.loads(EXP45_BEST.read_text(encoding="utf-8"))
    lower = np.asarray(payload["native"]["target"]["lower_body_target"], dtype=np.float32)
    target = default_pose.copy()
    target[:15] = lower
    return target - default_pose


def safe_inverse_summary(model: mujoco.MjModel, data: mujoco.MjData) -> dict:
    probe = mujoco.MjData(model)
    mujoco.mj_copyData(probe, model, data)
    return EXP42.inverse_summary(model, probe)


def run_variant(variant: Variant, params_path: Path, seconds: float, out_dir: Path) -> dict:
    env = EXP28.ContactAwareSquat(
        stage_height=0.67,
        controller_blend=0.0,
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
    visible_delta = load_visible_delta(default_pose)
    data.ctrl[:] = default_pose
    mujoco.mj_forward(model, data)

    gyro_adr = EXP28.sensor_adr(model, "gyro_pelvis")
    linvel_adr = EXP28.sensor_adr(model, "local_linvel_pelvis")
    imu_site = model.site("imu_in_pelvis").id
    foot_site_ids = np.asarray(env._feet_site_id)
    foot_geom_ids = np.asarray([model.geom("left_foot").id, model.geom("right_foot").id])
    foot_contact_sensor_ids = list(env._feet_floor_found_sensor)
    initial_foot_xy = data.site_xpos[foot_site_ids, :2].copy()
    ctrl_dt = float(env.dt)
    sim_dt = float(model.opt.timestep)
    n_substeps = max(1, round(ctrl_dt / sim_dt))
    total_steps = int(seconds / ctrl_dt)
    phase_clock = np.ones(2, dtype=np.float32) * np.pi
    command = np.zeros(3, dtype=np.float32)
    last_action = np.zeros(env.action_size, dtype=np.float32)
    gravity_down = np.array([0.0, 0.0, -1.0], dtype=np.float32)
    rng = jax.random.PRNGKey(0)

    start_height = float(data.qpos[2])
    min_height = start_height
    final_height = start_height
    fell_at = None
    first_visible_at = None
    first_support_breach_at = None
    phase_name = "descend"
    phase_switches = [{"t": 0.0, "phase": phase_name, "reason": "start"}]
    gain = 0.0
    max_gain_seen = 0.0
    both_feet_contact_count = 0
    max_foot_slip = 0.0
    min_support_margin = float("inf")
    max_joint_violation = 0.0
    max_lr_imbalance = 0.0
    max_inverse_torque = 0.0
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
            np.concatenate([np.cos(phase_clock), np.sin(phase_clock)]),
        ]).astype(np.float32)
        rng, action_rng = jax.random.split(rng)
        action, _ = policy({"state": jp.asarray(obs, dtype=jp.float32)[None]}, action_rng)
        action_np = np.asarray(action[0], dtype=np.float32)

        support = EXP37.support_metrics(model, data, foot_geom_ids)
        min_support_margin = min(min_support_margin, support["support_margin"])
        if support["support_margin"] < 0.0 and first_support_breach_at is None:
            first_support_breach_at = round(t, 3)
        foot_slip = float(np.max(np.linalg.norm(data.site_xpos[foot_site_ids, :2] - initial_foot_xy, axis=1)))
        max_foot_slip = max(max_foot_slip, foot_slip)
        quat = data.qpos[3:7]
        mat = np.empty(9)
        mujoco.mju_quat2Mat(mat, quat)
        up_z = float(mat.reshape(3, 3)[2, 2])
        visible_drop_now = start_height - float(data.qpos[2])
        if visible_drop_now >= 0.08 and first_visible_at is None:
            first_visible_at = round(t, 3)

        return_reason = None
        if visible_drop_now >= variant.target_drop:
            return_reason = "target_drop"
        elif support["support_margin"] <= variant.support_floor:
            return_reason = "support_floor"
        elif foot_slip >= variant.slip_floor:
            return_reason = "slip_floor"
        elif up_z <= variant.up_z_floor:
            return_reason = "upright_floor"

        if phase_name == "descend" and return_reason is None:
            gain = min(variant.max_gain, gain + variant.descend_rate * ctrl_dt)
        elif phase_name == "descend":
            phase_name = "return"
            phase_switches.append({"t": round(t, 3), "phase": phase_name, "reason": return_reason})
        if phase_name == "return":
            gain = max(0.0, gain - variant.return_rate * ctrl_dt)
            if gain <= 1e-6:
                phase_name = "stand"
                phase_switches.append({"t": round(t, 3), "phase": phase_name, "reason": "gain_zero"})
        max_gain_seen = max(max_gain_seen, gain)

        policy_targets = default_pose + variant.policy_weight * action_np * float(env._config.action_scale)
        target = policy_targets + gain * visible_delta
        data.ctrl[:] = np.clip(target, model.actuator_ctrlrange[:, 0], model.actuator_ctrlrange[:, 1])
        for _ in range(n_substeps):
            mujoco.mj_step(model, data)
        last_action = action_np

        height = float(data.qpos[2])
        final_height = height
        min_height = min(min_height, height)
        contacts = [
            float(data.sensordata[model.sensor_adr[sensor_id]]) > 0
            for sensor_id in foot_contact_sensor_ids
        ]
        both_feet = all(contacts)
        both_feet_contact_count += int(both_feet)
        max_joint_violation = max(max_joint_violation, EXP28.joint_limit_violation(model, data))
        wrench = EXP42.contact_wrench_summary(model, data)
        inv = safe_inverse_summary(model, data)
        max_lr_imbalance = max(max_lr_imbalance, wrench["lr_normal_imbalance"])
        max_inverse_torque = max(max_inverse_torque, inv["lower_inverse_linf"])
        if (height < 0.45 or up_z < 0.30) and fell_at is None:
            fell_at = round(t, 3)

        if step % max(1, int(0.2 / ctrl_dt)) == 0:
            samples.append({
                "t": round(t, 3),
                "phase": phase_name,
                "height": height,
                "visible_drop": start_height - height,
                "command_gain": gain,
                "support_margin": support["support_margin"],
                "both_feet_contact": both_feet,
                "foot_slip_distance": foot_slip,
                "lr_normal_imbalance": wrench["lr_normal_imbalance"],
                "inverse_torque": inv["lower_inverse_linf"],
                "up_z": up_z,
            })

    visible_drop = start_height - min_height
    foot_contact_ratio = both_feet_contact_count / max(1, total_steps)
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
        verdict = "PASS_PHASE_TRAJECTORY"
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
        "attempt": variant.name,
        "variant": variant.__dict__,
        "params_path": str(params_path),
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
        "first_support_breach_at": first_support_breach_at,
        "max_joint_limit_violation": max_joint_violation,
        "max_lr_normal_imbalance": max_lr_imbalance,
        "max_lower_inverse_torque": max_inverse_torque,
        "max_observed_command_gain": max_gain_seen,
        "phase_switches": phase_switches,
        "pass_gate": pass_gate,
        "verdict": verdict,
        "samples": samples,
    }
    (out_dir / "native-eval.json").write_text(json.dumps(native, indent=2), encoding="utf-8")
    return native


def write_summary(results: list[dict]) -> None:
    lines = [
        "# G1 Phase Trajectory Summary",
        "",
        "| Attempt | Verdict | Drop | Fell at | Final h | Contact | Slip | Support min | Max gain | Switches |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for native in results:
        fell = "never" if native["fell_at"] is None else f"{native['fell_at']:.2f}s"
        switches = ", ".join(f"{s['t']}:{s['phase']}:{s['reason']}" for s in native["phase_switches"][1:])
        lines.append(
            f"| {native['attempt']} | {native['verdict']} | {native['visible_drop']:.4f}m | "
            f"{fell} | {native['final_height']:.4f}m | {native['foot_contact_ratio']:.2f} | "
            f"{native['foot_slip_distance']:.3f}m | {native['min_support_margin']:.4f}m | "
            f"{native['max_observed_command_gain']:.2f} | {switches or '-'} |"
        )
    lines.extend([
        "",
        "M19 remains open unless visible depth, no-fall, contact, stance, return, knee/hip pose, and browser replay gates pass together.",
    ])
    (VERIFY / "phase-trajectory-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=None)
    parser.add_argument("--seconds", type=float, default=6.0)
    parser.add_argument("--sweep", action="store_true")
    args = parser.parse_args()
    source = args.source or default_source()
    variants = [
        Variant("stop-0p03-support0p030", 0.45, 0.03, 0.030, 0.12, 0.96, 0.16, 0.70),
        Variant("stop-0p05-support0p030", 0.55, 0.05, 0.030, 0.12, 0.96, 0.18, 0.85),
        Variant("stop-0p08-support0p030", 0.70, 0.08, 0.030, 0.12, 0.96, 0.20, 1.00),
        Variant("guard-0p08-support0p045", 0.70, 0.08, 0.045, 0.10, 0.98, 0.20, 1.15),
        Variant("fast-return-0p08", 0.80, 0.08, 0.025, 0.12, 0.95, 0.24, 1.60),
        Variant("low-policy-fast-return", 0.90, 0.08, 0.025, 0.12, 0.95, 0.24, 1.60, 0.70),
    ] if args.sweep else [
        Variant("guard-0p08-support0p045", 0.70, 0.08, 0.045, 0.10, 0.98, 0.20, 1.15),
    ]
    VERIFY.mkdir(parents=True, exist_ok=True)
    results = []
    for variant in variants:
        out_dir = VERIFY / "attempts" / variant.name
        out_dir.mkdir(parents=True, exist_ok=True)
        native = run_variant(variant, source, args.seconds, out_dir)
        (out_dir / "result.json").write_text(json.dumps({"native": native}, indent=2), encoding="utf-8")
        results.append(native)
    write_summary(results)
    print(json.dumps({"attempts": results}, indent=2), flush=True)


if __name__ == "__main__":
    main()
