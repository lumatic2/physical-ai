"""Run reference-base action target G1 squat finetune."""

from __future__ import annotations

import argparse
import functools
import json
import pickle
import time
from pathlib import Path
from typing import Any

import jax
import jax.numpy as jp
import mujoco
import numpy as np
from brax.training.acme import running_statistics
from brax.training.agents.ppo import networks as ppo_networks
from brax.training.agents.ppo import train as ppo
from mujoco_playground import wrapper
from mujoco_playground.config import locomotion_params

from g1_reference_base_env import G1ReferenceBaseDepth


if not hasattr(jax, "device_put_replicated"):
    def _device_put_replicated(x, devices):
        count = max(1, len(devices))
        return jax.device_put(jax.tree_util.tree_map(lambda y: jp.stack([y] * count), x))

    jax.device_put_replicated = _device_put_replicated  # type: ignore[attr-defined]


EXP_DIR = Path(__file__).resolve().parent
ROOT = EXP_DIR.parents[1]
VERIFY = EXP_DIR / "verify"
EXP22_SOURCE = ROOT / "experiments/22-g1-squat-depth-finetune/verify/train/params.pkl"
EXP21_SOURCE = ROOT / "experiments/21-g1-stabilizer-init-probe/verify/train/params.pkl"


def default_source() -> Path:
    return EXP22_SOURCE if EXP22_SOURCE.exists() else EXP21_SOURCE


def attempt_slug(stage_height: float, reference_gain: float, residual_scale: float) -> str:
    return (
        f"stage-{stage_height:.2f}-gain-{reference_gain:.2f}-resid-{residual_scale:.2f}"
        .replace(".", "p")
    )


def ppo_config(timesteps: int):
    params = locomotion_params.brax_ppo_config("G1JoystickFlatTerrain")
    params.num_timesteps = timesteps
    params.num_envs = 512
    params.num_evals = 3
    params.num_minibatches = 8
    params.batch_size = 128
    params.episode_length = 300
    params.learning_rate = 2e-5
    params.network_factory.policy_hidden_layer_sizes = (512, 256, 128)
    params.network_factory.value_hidden_layer_sizes = (512, 256, 128)
    return params


def layer_shapes(params: Any) -> dict[str, dict[str, list[int]]]:
    return {
        name: {key: list(value.shape) for key, value in layer.items()}
        for name, layer in params[1]["params"].items()
    }


def make_env(stage_height: float, reference_gain: float, ramp_s: float, residual_scale: float, impl: str):
    return G1ReferenceBaseDepth(
        stage_height=stage_height,
        reference_gain=reference_gain,
        ramp_s=ramp_s,
        residual_scale=residual_scale,
        config_overrides={"impl": impl},
    )


def compatibility(source: Path, stage_height: float, reference_gain: float, ramp_s: float, residual_scale: float) -> dict:
    env = make_env(stage_height, reference_gain, ramp_s, residual_scale, "jax")
    cfg = ppo_config(1)
    networks = ppo_networks.make_ppo_networks(
        observation_size=env.observation_size,
        action_size=env.action_size,
        **cfg.network_factory,
    )
    target = networks.policy_network.init(jax.random.PRNGKey(0))
    with source.open("rb") as f:
        source_params = pickle.load(f)
    target_shapes = {
        name: {key: list(value.shape) for key, value in layer.items()}
        for name, layer in target["params"].items()
    }
    return {
        "stage_height": stage_height,
        "reference_gain": reference_gain,
        "ramp_s": ramp_s,
        "residual_scale": residual_scale,
        "source_params": str(source),
        "source_exists": source.exists(),
        "obs_size": env.observation_size,
        "action_size": env.action_size,
        "policy_shape_match": layer_shapes(source_params) == target_shapes,
    }


def rollout_smoke(stage_height: float, reference_gain: float, ramp_s: float, residual_scale: float, steps: int = 20) -> dict:
    env = make_env(stage_height, reference_gain, ramp_s, residual_scale, "jax")
    reset_fn = jax.jit(env.reset)
    step_fn = jax.jit(env.step)
    state = reset_fn(jax.random.PRNGKey(0))
    zero = jp.zeros(env.action_size)
    heights = []
    rewards = []
    support_margins = []
    reference_blends = []
    dones = []
    for _ in range(steps):
        state = step_fn(state, zero)
        heights.append(float(state.data.qpos[2]))
        rewards.append(float(state.reward))
        support_margins.append(float(state.metrics["support_margin"]))
        reference_blends.append(float(state.metrics["reference_blend"]))
        dones.append(float(state.done))
    return {
        "rollout_steps": steps,
        "reward_first": rewards[0],
        "reward_last": rewards[-1],
        "height_min": min(heights),
        "support_margin_min": min(support_margins),
        "reference_blend_last": reference_blends[-1],
        "done_any": any(v > 0 for v in dones),
    }


def train(
    source: Path,
    stage_height: float,
    reference_gain: float,
    ramp_s: float,
    residual_scale: float,
    timesteps: int,
    attempt_dir: Path,
    seed: int,
) -> dict:
    env = make_env(stage_height, reference_gain, ramp_s, residual_scale, "jax")
    eval_env = make_env(stage_height, reference_gain, ramp_s, residual_scale, "jax")
    cfg = ppo_config(timesteps)
    with source.open("rb") as f:
        source_params = pickle.load(f)
    network_factory = functools.partial(ppo_networks.make_ppo_networks, **cfg.network_factory)
    train_params = dict(cfg)
    train_params.pop("network_factory", None)
    num_eval_envs = train_params.pop("num_eval_envs", 128)
    rewards: list[tuple[int, float]] = []

    def progress(step, metrics):
        reward = metrics.get("eval/episode_reward")
        if reward is not None:
            rewards.append((int(step), float(reward)))
            print(f"{step}: reward={reward:.3f}", flush=True)

    start = time.monotonic()
    _, learned_params, _ = ppo.train(
        environment=env,
        eval_env=eval_env,
        **train_params,
        network_factory=network_factory,
        seed=seed,
        wrap_env_fn=wrapper.wrap_for_brax_training,
        num_eval_envs=num_eval_envs,
        progress_fn=progress,
        restore_params=source_params,
        restore_value_fn=True,
    )
    elapsed = time.monotonic() - start
    out_dir = attempt_dir / "train"
    out_dir.mkdir(parents=True, exist_ok=True)
    params_path = out_dir / "params.pkl"
    with params_path.open("wb") as f:
        pickle.dump(learned_params, f)
    rewards_path = out_dir / "rewards.txt"
    rewards_path.write_text(
        "\n".join([
            f"# stage_height={stage_height}",
            f"# reference_gain={reference_gain}",
            f"# ramp_s={ramp_s}",
            f"# residual_scale={residual_scale}",
            f"# timesteps={timesteps} train_min={elapsed/60:.2f} seed={seed} source={source}",
            *[f"{s}\t{r}" for s, r in rewards],
        ]) + "\n",
        encoding="utf-8",
    )
    return {
        "timesteps": timesteps,
        "train_min": elapsed / 60,
        "seed": seed,
        "reward_points": rewards,
        "source_params": str(source),
        "params_path": str(params_path.relative_to(EXP_DIR)),
        "rewards_path": str(rewards_path.relative_to(EXP_DIR)),
    }


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


def support_metrics(model: mujoco.MjModel, data: mujoco.MjData) -> dict:
    foot_geom_ids = [model.geom("left_foot").id, model.geom("right_foot").id]
    corners = []
    for geom_id in foot_geom_ids:
        half_x, half_y = model.geom_size[geom_id, 0], model.geom_size[geom_id, 1]
        geom_pos = data.geom_xpos[geom_id]
        geom_mat = data.geom_xmat[geom_id].reshape(3, 3)
        for sx in (-half_x, half_x):
            for sy in (-half_y, half_y):
                corners.append((geom_pos + geom_mat @ np.array([sx, sy, 0.0]))[:2])
    support = np.asarray(corners)
    min_xy = support.min(axis=0)
    max_xy = support.max(axis=0)
    com_xy = data.subtree_com[0, :2]
    margins = np.array([
        com_xy[0] - min_xy[0],
        max_xy[0] - com_xy[0],
        com_xy[1] - min_xy[1],
        max_xy[1] - com_xy[1],
    ])
    return {"support_margin": float(np.min(margins))}


def build_policy(env: G1ReferenceBaseDepth, params_path: Path):
    with params_path.open("rb") as f:
        params = pickle.load(f)
    normalizer_params, policy_params = params[0], params[1]
    cfg = ppo_config(1)
    networks = ppo_networks.make_ppo_networks(
        observation_size=env.observation_size,
        action_size=env.action_size,
        preprocess_observations_fn=running_statistics.normalize,
        **cfg.network_factory,
    )
    return ppo_networks.make_inference_fn(networks)((normalizer_params, policy_params), deterministic=True)


def native_eval(
    stage_height: float,
    reference_gain: float,
    ramp_s: float,
    residual_scale: float,
    params_path: Path,
    seconds: float,
    out_dir: Path,
) -> dict:
    env = make_env(stage_height, reference_gain, ramp_s, residual_scale, "jax")
    policy = build_policy(env, params_path)
    ref_joints = np.asarray(env._ref_joints, dtype=np.float32)
    ref_heights = np.asarray(env._ref_heights, dtype=np.float32)
    model = env.mj_model
    data = mujoco.MjData(model)
    key = model.keyframe("knees_bent")
    data.qpos[:] = key.qpos
    default_pose = key.qpos[7:].astype(np.float32).copy()
    data.ctrl[:] = default_pose
    mujoco.mj_forward(model, data)

    gyro_adr = sensor_adr(model, "gyro_pelvis")
    linvel_adr = sensor_adr(model, "local_linvel_pelvis")
    imu_site = model.site("imu_in_pelvis").id
    ctrl_dt = float(env.dt)
    sim_dt = float(model.opt.timestep)
    n_substeps = max(1, round(ctrl_dt / sim_dt))
    total_steps = int(seconds / ctrl_dt)
    phase = np.array([0.0, np.pi], dtype=np.float32)
    phase_dt = float(2 * np.pi * ctrl_dt * 1.375)
    last_action = np.zeros(env.action_size, dtype=np.float32)
    command = np.zeros(3, dtype=np.float32)
    gravity_down = np.array([0.0, 0.0, -1.0], dtype=np.float32)
    rng = jax.random.PRNGKey(0)
    foot_site_ids = np.asarray(env._feet_site_id)
    initial_foot_xy = data.site_xpos[foot_site_ids, :2].copy()
    foot_contact_sensor_ids = list(env._feet_floor_found_sensor)

    start_height = float(data.qpos[2])
    fell_at = None
    first_visible_at = None
    min_height = start_height
    final_height = start_height
    min_support_margin = float("inf")
    max_downward_velocity = 0.0
    last_height = start_height
    both_feet_contact_count = 0
    hold_count = 0
    max_foot_slip = 0.0
    max_joint_violation = 0.0
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

        ref_index = min(step, len(ref_heights) - 1)
        reference_pose = default_pose.copy()
        reference_pose[:15] = ref_joints[ref_index]
        blend = reference_gain * min(max(t / max(ramp_s, ctrl_dt), 0.0), 1.0)
        moving_pose = default_pose + blend * (reference_pose - default_pose)

        height = float(data.qpos[2])
        final_height = height
        min_height = min(min_height, height)
        visible_drop = start_height - height
        if visible_drop >= 0.08 and first_visible_at is None:
            first_visible_at = round(t, 3)
        vertical_velocity = (height - last_height) / ctrl_dt if step > 0 else 0.0
        max_downward_velocity = min(max_downward_velocity, vertical_velocity)
        support = support_metrics(model, data)
        min_support_margin = min(min_support_margin, support["support_margin"])
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
        max_joint_violation = max(max_joint_violation, joint_limit_violation(model, data))

        target = moving_pose + residual_scale * action_np * float(env._config.action_scale)
        data.ctrl[:] = np.clip(target, model.actuator_ctrlrange[:, 0], model.actuator_ctrlrange[:, 1])
        for _ in range(n_substeps):
            mujoco.mj_step(model, data)
        phase = np.fmod(phase + phase_dt + np.pi, 2 * np.pi) - np.pi
        last_action = action_np
        last_height = height

        if step % max(1, int(0.2 / ctrl_dt)) == 0:
            samples.append({
                "t": round(t, 3),
                "base_height": height,
                "visible_drop": visible_drop,
                "target_height": float(ref_heights[ref_index]),
                "reference_blend": blend,
                "up_z": up_z,
                "both_feet_contact": both_feet,
                "foot_slip_distance": foot_slip,
                "support_margin": support["support_margin"],
                "vertical_velocity": vertical_velocity,
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
        verdict = "PASS_REFERENCE_BASE_VISIBLE_SQUAT"
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
        "max_downward_velocity": max_downward_velocity,
        "max_joint_limit_violation": max_joint_violation,
        "pass_gate": pass_gate,
        "verdict": verdict,
        "samples": samples,
    }
    (out_dir / "native-eval.json").write_text(json.dumps(native, indent=2), encoding="utf-8")
    return native


def write_summary(result: dict, out_dir: Path) -> None:
    native = result["native"]
    train_result = result.get("train", {})
    fell = "never" if native["fell_at"] is None else f"{native['fell_at']:.2f}s"
    lines = [
        "# G1 Reference-Base Finetune Summary",
        "",
        "| Verdict | Timesteps | Train min | Drop | Fell at | Contact | Final height | Support min | Slip |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        (
            f"| {native['verdict']} | {train_result.get('timesteps', 0)} | "
            f"{train_result.get('train_min', 0.0):.2f} | {native['visible_drop']:.4f}m | "
            f"{fell} | {native['foot_contact_ratio']:.2f} | {native['final_height']:.4f}m | "
            f"{native['min_support_margin']:.4f}m | {native['foot_slip_distance']:.3f}m |"
        ),
        "",
        "M19 closes only when visible depth, no-fall, contact, stance, return, and browser replay gates pass together.",
    ]
    (out_dir / "reference-base-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=None)
    parser.add_argument("--stage-height", type=float, default=0.74)
    parser.add_argument("--reference-gain", type=float, default=0.35)
    parser.add_argument("--ramp-s", type=float, default=3.0)
    parser.add_argument("--residual-scale", type=float, default=1.0)
    parser.add_argument("--train", action="store_true")
    parser.add_argument("--timesteps", type=int, default=20_000)
    parser.add_argument("--seed", type=int, default=10)
    parser.add_argument("--seconds", type=float, default=6.0)
    args = parser.parse_args()

    source = args.source or default_source()
    out_dir = VERIFY / attempt_slug(args.stage_height, args.reference_gain, args.residual_scale)
    out_dir.mkdir(parents=True, exist_ok=True)
    result = {
        "compatibility": compatibility(source, args.stage_height, args.reference_gain, args.ramp_s, args.residual_scale),
        "rollout": rollout_smoke(args.stage_height, args.reference_gain, args.ramp_s, args.residual_scale),
    }
    if not result["compatibility"]["policy_shape_match"]:
        raise SystemExit("source and target policy shapes do not match")
    if args.train:
        result["train"] = train(
            source,
            args.stage_height,
            args.reference_gain,
            args.ramp_s,
            args.residual_scale,
            args.timesteps,
            out_dir,
            args.seed,
        )
        params_path = out_dir / "train" / "params.pkl"
    else:
        params_path = source
    result["native"] = native_eval(
        args.stage_height,
        args.reference_gain,
        args.ramp_s,
        args.residual_scale,
        params_path,
        args.seconds,
        out_dir,
    )
    result["verdict"] = result["native"]["verdict"]
    write_summary(result, out_dir)
    (out_dir / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(result["verdict"], json.dumps(result["native"], indent=2), flush=True)


if __name__ == "__main__":
    main()
