"""Probe contact-preserving controller blends for G1 squat stage 0.74."""

from __future__ import annotations

import argparse
import importlib.util
import json
import pickle
import re
import sys
from pathlib import Path
from typing import Any

import jax
import jax.numpy as jp
import mujoco
import numpy as np
from brax.training.acme import running_statistics
from brax.training.agents.ppo import networks as ppo_networks
from mujoco_playground.config import locomotion_params


EXP_DIR = Path(__file__).resolve().parent
ROOT = EXP_DIR.parents[1]
VERIFY = EXP_DIR / "verify"
EXP25_DIR = ROOT / "experiments/25-g1-squat-depth-curriculum"
EXP22_SOURCE = ROOT / "experiments/22-g1-squat-depth-finetune/verify/train/params.pkl"
EXP21_SOURCE = ROOT / "experiments/21-g1-stabilizer-init-probe/verify/train/params.pkl"

sys.path.insert(0, str(EXP25_DIR))


def load_exp25_env():
    module_path = EXP25_DIR / "g1_squat_curriculum_env.py"
    spec = importlib.util.spec_from_file_location("exp25_g1_squat_curriculum_env", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.G1SquatCurriculum


G1SquatCurriculum = load_exp25_env()


def default_source() -> Path:
    return EXP22_SOURCE if EXP22_SOURCE.exists() else EXP21_SOURCE


def ppo_config():
    params = locomotion_params.brax_ppo_config("G1JoystickFlatTerrain")
    params.network_factory.policy_hidden_layer_sizes = (512, 256, 128)
    params.network_factory.value_hidden_layer_sizes = (512, 256, 128)
    return params


def build_policy(env: Any, params_path: Path):
    with params_path.open("rb") as f:
        params = pickle.load(f)
    normalizer_params, policy_params = params[0], params[1]
    cfg = ppo_config()
    networks = ppo_networks.make_ppo_networks(
        observation_size=env.observation_size,
        action_size=env.action_size,
        preprocess_observations_fn=running_statistics.normalize,
        **cfg.network_factory,
    )
    return ppo_networks.make_inference_fn(networks)((normalizer_params, policy_params), deterministic=True)


def parse_float_token(token: str) -> float:
    return float(token.replace("p", "."))


def parse_variant(name: str) -> dict[str, float | str]:
    if name == "policy_only":
        return {"kind": "policy", "blend": 0.0, "floor": 0.0}
    blend_match = re.fullmatch(r"blend_(0p\d+)", name)
    if blend_match:
        return {"kind": "blend", "blend": parse_float_token(blend_match.group(1)), "floor": 0.0}
    guard_match = re.fullmatch(r"guard_(0p\d+)_floor_(0p\d+)", name)
    if guard_match:
        return {
            "kind": "guard",
            "blend": parse_float_token(guard_match.group(1)),
            "floor": parse_float_token(guard_match.group(2)),
        }
    raise ValueError(f"unknown variant {name}")


def sensor_adr(model: mujoco.MjModel, name: str) -> int:
    return int(model.sensor(name).adr[0])


def joint_limit_violation(model: mujoco.MjModel, data: mujoco.MjData) -> float:
    worst = 0.0
    for jid in range(model.njnt):
        if model.jnt_type[jid] == mujoco.mjtJoint.mjJNT_FREE:
            continue
        qadr = model.jnt_qposadr[jid]
        lo, hi = model.jnt_range[jid]
        q = data.qpos[qadr]
        if q < lo:
            worst = max(worst, float(lo - q))
        elif q > hi:
            worst = max(worst, float(q - hi))
    return worst


def torso_up_z(data: mujoco.MjData) -> float:
    mat = np.empty(9)
    mujoco.mju_quat2Mat(mat, data.qpos[3:7])
    return float(mat.reshape(3, 3)[2, 2])


def clip_ctrl(model: mujoco.MjModel, ctrl: np.ndarray) -> np.ndarray:
    if model.actuator_ctrllimited.size and np.any(model.actuator_ctrllimited):
        lo = model.actuator_ctrlrange[:, 0]
        hi = model.actuator_ctrlrange[:, 1]
        return np.clip(ctrl, lo, hi)
    return ctrl


def make_obs(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    default_pose: np.ndarray,
    last_action: np.ndarray,
    phase: np.ndarray,
    command: np.ndarray,
    gyro_adr: int,
    linvel_adr: int,
    imu_site: int,
) -> np.ndarray:
    gravity_down = np.array([0.0, 0.0, -1.0], dtype=np.float32)
    gyro = data.sensordata[gyro_adr : gyro_adr + 3]
    linvel = data.sensordata[linvel_adr : linvel_adr + 3]
    gravity = data.site_xmat[imu_site].reshape(3, 3).T @ gravity_down
    return np.concatenate(
        [
            linvel,
            gyro,
            gravity,
            command,
            data.qpos[7:] - default_pose,
            data.qvel[6:],
            last_action,
            np.concatenate([np.cos(phase), np.sin(phase)]),
        ]
    ).astype(np.float32)


def current_both_feet(model: mujoco.MjModel, data: mujoco.MjData, sensor_ids: list[int]) -> bool:
    return all(float(data.sensordata[model.sensor_adr[sensor_id]]) > 0 for sensor_id in sensor_ids)


def effective_blend(spec: dict[str, float | str], both_feet: bool, previous_contact_loss: bool) -> float:
    kind = str(spec["kind"])
    blend = float(spec["blend"])
    floor = float(spec["floor"])
    if kind == "policy":
        return 0.0
    if kind == "blend":
        return blend
    if kind == "guard":
        return blend if both_feet and not previous_contact_loss else floor
    raise ValueError(kind)


def compute_ctrl(
    model: mujoco.MjModel,
    default_pose: np.ndarray,
    policy_action: np.ndarray,
    action_scale: float,
    ref_joints: np.ndarray,
    ref_index: int,
    blend: float,
) -> np.ndarray:
    policy_ctrl = default_pose + policy_action * action_scale
    staged_pose = default_pose.copy()
    staged_pose[:15] = ref_joints[ref_index]
    return clip_ctrl(model, (1.0 - blend) * policy_ctrl + blend * staged_pose)


def classify(
    fell_at: float | None,
    min_height: float,
    stage_height: float,
    hold_duration: float,
    return_to_stand: bool,
    foot_contact_ratio: float,
) -> str:
    reached_stage = min_height <= stage_height + 0.005
    if (
        fell_at is None
        and reached_stage
        and hold_duration >= 0.5
        and return_to_stand
        and foot_contact_ratio >= 0.90
    ):
        return "STABLE_STAGE_DEPTH"
    if fell_at is None and reached_stage and hold_duration >= 0.5 and foot_contact_ratio >= 0.90:
        return "STABLE_DEPTH_RETURN_GAP"
    if fell_at is None and reached_stage and hold_duration >= 0.5:
        return "STABLE_DEPTH_CONTACT_GAP"
    if fell_at is None and reached_stage:
        return "STABLE_TOUCH_DEPTH"
    if fell_at is None:
        return "NO_FALL_DEPTH_PENDING"
    if reached_stage:
        return "DEPTH_WITH_FALL"
    return "FAIL_BEFORE_DEPTH"


def run_variant(env: Any, policy: Any, params_path: Path, variant: str, seconds: float, stage_height: float) -> dict:
    spec = parse_variant(variant)
    ref_joints = np.asarray(env._ref_joints, dtype=np.float32)
    ref_heights = np.asarray(env._ref_heights, dtype=np.float32)
    model = env.mj_model
    data = mujoco.MjData(model)
    key = model.keyframe("knees_bent")
    data.qpos[:] = key.qpos
    default_pose = key.qpos[7:].astype(np.float32).copy()
    data.ctrl[:] = default_pose
    mujoco.mj_forward(model, data)

    ctrl_dt = float(env.dt)
    sim_dt = float(model.opt.timestep)
    n_substeps = max(1, round(ctrl_dt / sim_dt))
    total_steps = int(seconds / ctrl_dt)
    gyro_adr = sensor_adr(model, "gyro_pelvis")
    linvel_adr = sensor_adr(model, "local_linvel_pelvis")
    imu_site = model.site("imu_in_pelvis").id
    phase = np.array([0.0, np.pi], dtype=np.float32)
    phase_dt = float(2 * np.pi * ctrl_dt * 1.375)
    command = np.zeros(3, dtype=np.float32)
    last_action = np.zeros(env.action_size, dtype=np.float32)
    rng = jax.random.PRNGKey(0)
    foot_site_ids = np.asarray(env._feet_site_id)
    initial_foot_xy = data.site_xpos[foot_site_ids, :2].copy()
    foot_contact_sensor_ids = list(env._feet_floor_found_sensor)

    fell_at = None
    min_height = float("inf")
    final_height = None
    torso_up_min = float("inf")
    max_reference_error = 0.0
    max_height_error = 0.0
    max_joint_violation = 0.0
    action_delta_sum = 0.0
    effective_blend_sum = 0.0
    both_feet_contact_count = 0
    hold_count = 0
    max_foot_slip = 0.0
    previous_contact_loss = False
    samples = []

    for step in range(total_steps):
        obs = make_obs(model, data, default_pose, last_action, phase, command, gyro_adr, linvel_adr, imu_site)
        rng, action_rng = jax.random.split(rng)
        action, _ = policy({"state": jp.asarray(obs, dtype=jp.float32)[None]}, action_rng)
        action_np = np.asarray(action[0], dtype=np.float32)
        ref_index = min(step, len(ref_heights) - 1)

        height = float(data.qpos[2])
        final_height = height
        up_z = torso_up_z(data)
        both_feet = current_both_feet(model, data, foot_contact_sensor_ids)
        both_feet_contact_count += int(both_feet)
        if height <= stage_height + 0.005 and both_feet:
            hold_count += 1

        reference_error = float(np.mean(np.square(data.qpos[7:22] - ref_joints[ref_index])))
        height_error = float((height - float(ref_heights[ref_index])) ** 2)
        foot_slip = float(np.max(np.linalg.norm(data.site_xpos[foot_site_ids, :2] - initial_foot_xy, axis=1)))
        fallen = height < 0.45 or up_z < 0.30
        if fallen and fell_at is None:
            fell_at = round(step * ctrl_dt, 3)

        min_height = min(min_height, height)
        torso_up_min = min(torso_up_min, up_z)
        max_reference_error = max(max_reference_error, reference_error)
        max_height_error = max(max_height_error, height_error)
        max_joint_violation = max(max_joint_violation, joint_limit_violation(model, data))
        action_delta_sum += float(np.mean(np.square(action_np - last_action)))
        max_foot_slip = max(max_foot_slip, foot_slip)

        blend = effective_blend(spec, both_feet, previous_contact_loss)
        effective_blend_sum += blend
        data.ctrl[:] = compute_ctrl(
            model,
            default_pose,
            action_np,
            float(env._config.action_scale),
            ref_joints,
            ref_index,
            blend,
        )
        for _ in range(n_substeps):
            mujoco.mj_step(model, data)
        previous_contact_loss = not both_feet
        phase = np.fmod(phase + phase_dt + np.pi, 2 * np.pi) - np.pi
        last_action = action_np

        if step % max(1, int(0.2 / ctrl_dt)) == 0:
            samples.append(
                {
                    "t": round(step * ctrl_dt, 3),
                    "base_height": height,
                    "target_height": float(ref_heights[ref_index]),
                    "up_z": up_z,
                    "reference_error": reference_error,
                    "height_error": height_error,
                    "both_feet_contact": both_feet,
                    "foot_slip_distance": foot_slip,
                    "effective_blend": blend,
                }
            )

    hold_duration = hold_count * ctrl_dt
    foot_contact_ratio = both_feet_contact_count / max(1, total_steps)
    return_to_stand = final_height is not None and final_height >= 0.74
    verdict = classify(fell_at, min_height, stage_height, hold_duration, return_to_stand, foot_contact_ratio)
    return {
        "variant": variant,
        "params_path": str(params_path),
        "seconds": seconds,
        "stage_height": stage_height,
        "fell_at": fell_at,
        "upright_s": seconds if fell_at is None else fell_at,
        "min_height": min_height,
        "hold_duration_at_or_below_stage": hold_duration,
        "final_height": final_height,
        "return_to_stand": return_to_stand,
        "torso_up_min": torso_up_min,
        "foot_contact_ratio": foot_contact_ratio,
        "foot_slip_distance": max_foot_slip,
        "max_reference_error": max_reference_error,
        "max_height_error": max_height_error,
        "max_joint_limit_violation": max_joint_violation,
        "mean_action_delta": action_delta_sum / max(1, total_steps),
        "mean_effective_blend": effective_blend_sum / max(1, total_steps),
        "verdict": verdict,
        "samples": samples,
    }


def overall_verdict(variants: list[dict]) -> str:
    if any(v["verdict"] == "STABLE_STAGE_DEPTH" for v in variants):
        return "CONTACT_CONTROLLER_STAGE_PASS"
    if any(v["verdict"] == "STABLE_DEPTH_RETURN_GAP" for v in variants):
        return "CONTACT_CONTROLLER_RETURN_GAP"
    if any(v["verdict"] == "STABLE_DEPTH_CONTACT_GAP" for v in variants):
        return "CONTACT_CONTROLLER_DEPTH_NEEDS_CONTACT"
    if any(v["verdict"] == "STABLE_TOUCH_DEPTH" for v in variants):
        return "CONTACT_CONTROLLER_DEPTH_NEEDS_HOLD"
    if any(v["verdict"] == "DEPTH_WITH_FALL" for v in variants):
        return "CONTACT_CONTROLLER_UNSTABLE_DEPTH"
    if any(v["verdict"] == "NO_FALL_DEPTH_PENDING" for v in variants):
        return "CONTACT_CONTROLLER_TOO_CONSERVATIVE"
    return "CONTACT_CONTROLLER_FAILS_BEFORE_DEPTH"


def write_report(result: dict) -> None:
    lines = [
        "# G1 Squat Contact Controller Probe",
        "",
        f"- Overall verdict: {result['verdict']}",
        f"- Stage height: {result['stage_height']}",
        f"- Source params: `{result['source_params']}`",
        "",
        "| Variant | Verdict | Min height | Fell at | Hold <= stage | Final height | Foot contact | Mean blend |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in result["variants"]:
        fell = "never" if row["fell_at"] is None else row["fell_at"]
        lines.append(
            f"| {row['variant']} | {row['verdict']} | "
            f"{row['min_height']:.4f} | {fell} | "
            f"{row['hold_duration_at_or_below_stage']:.2f}s | "
            f"{row['final_height']:.4f} | {row['foot_contact_ratio']:.2f} | "
            f"{row['mean_effective_blend']:.3f} |"
        )
    lines.extend(
        [
            "",
            "Interpretation:",
            "- `CONTACT_CONTROLLER_STAGE_PASS`: stage 0.74 controller candidate can move to next depth stage.",
            "- `CONTACT_CONTROLLER_DEPTH_NEEDS_CONTACT`: depth/hold remain possible, but contact gate is still open.",
            "- `CONTACT_CONTROLLER_TOO_CONSERVATIVE`: contact is preserved by staying too close to standing.",
            "- `CONTACT_CONTROLLER_UNSTABLE_DEPTH`: depth target is reachable but controller destabilizes the robot.",
            "",
        ]
    )
    (VERIFY / "g1-squat-contact-controller.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=None)
    parser.add_argument("--stage-height", type=float, default=0.74)
    parser.add_argument("--seconds", type=float, default=6.0)
    parser.add_argument(
        "--variants",
        nargs="+",
        default=[
            "policy_only",
            "blend_0p15",
            "blend_0p18",
            "blend_0p20",
            "blend_0p22",
            "blend_0p25",
            "guard_0p20_floor_0p05",
            "guard_0p22_floor_0p08",
            "guard_0p25_floor_0p10",
        ],
    )
    args = parser.parse_args()

    source = args.source or default_source()
    VERIFY.mkdir(parents=True, exist_ok=True)
    env = G1SquatCurriculum(stage_height=args.stage_height, config_overrides={"impl": "jax"})
    policy = build_policy(env, source)
    variant_results = [
        run_variant(env, policy, source, variant, args.seconds, args.stage_height)
        for variant in args.variants
    ]
    result = {
        "planning_gate": {
            "team_validation_mode": "manual-pass",
            "spec_delta": "exp26 contact gap refined into narrow blend and contact guard probe",
            "dod": [
                "narrow blend and contact guard variants evaluated with identical native metrics",
                "verify JSON and markdown report produced",
            ],
        },
        "stage_height": args.stage_height,
        "source_params": str(source),
        "variants": variant_results,
        "verdict": overall_verdict(variant_results),
        "next": "If no variant reaches contact gate, move from controller heuristics to RL fine-tune with explicit stance/contact reward around the 0.18-0.20 blend corridor.",
    }
    (VERIFY / "g1-squat-contact-controller.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    write_report(result)
    print(result["verdict"])


if __name__ == "__main__":
    main()
