"""Train and evaluate the G1 squat recovery env."""

from __future__ import annotations

import argparse
import functools
import json
import os
import pickle
import time
from pathlib import Path

import jax
import jax.numpy as jp
import mujoco
import numpy as np
from brax.training.acme import running_statistics
from brax.training.agents.ppo import networks as ppo_networks
from brax.training.agents.ppo import train as ppo
from mujoco_playground import wrapper
from mujoco_playground.config import locomotion_params

from g1_squat_recovery_env import G1SquatRecovery


EXP_DIR = Path(__file__).resolve().parent
VERIFY = EXP_DIR / "verify"


def ppo_config(timesteps: int):
    params = locomotion_params.brax_ppo_config("G1JoystickFlatTerrain")
    params.num_timesteps = timesteps
    params.num_envs = 512
    params.num_evals = 3
    params.num_minibatches = 8
    params.batch_size = 128
    params.episode_length = 450
    params.network_factory.policy_hidden_layer_sizes = (128, 64)
    params.network_factory.value_hidden_layer_sizes = (128, 64)
    return params


def rollout_smoke(steps: int = 20) -> dict:
    env = G1SquatRecovery(config_overrides={"impl": "jax"})
    reset_fn = jax.jit(env.reset)
    step_fn = jax.jit(env.step)
    state = reset_fn(jax.random.PRNGKey(0))
    zero = jp.zeros(env.action_size)
    heights = []
    dones = []
    rewards = []
    torso_up = []
    for _ in range(steps):
        state = step_fn(state, zero)
        heights.append(float(state.data.qpos[2]))
        dones.append(float(state.done))
        rewards.append(float(state.reward))
        torso_up.append(float(state.metrics["torso_up"]))
    return {
        "action_size": int(env.action_size),
        "obs_state_shape": list(state.obs["state"].shape),
        "obs_privileged_shape": list(state.obs["privileged_state"].shape),
        "rollout_steps": steps,
        "reward_first": rewards[0],
        "reward_last": rewards[-1],
        "height_min": min(heights),
        "height_last": heights[-1],
        "torso_up_min": min(torso_up),
        "done_any": any(v > 0 for v in dones),
    }


def train(out_dir: Path, timesteps: int) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    env = G1SquatRecovery(config_overrides={"impl": "jax"})
    eval_env = G1SquatRecovery(config_overrides={"impl": "jax"})
    params = ppo_config(timesteps)
    network_factory = functools.partial(ppo_networks.make_ppo_networks, **params.network_factory)
    train_params = dict(params)
    train_params.pop("network_factory", None)
    num_eval_envs = train_params.pop("num_eval_envs", 128)
    rewards: list[tuple[int, float]] = []

    def progress(step, metrics):
        reward = metrics.get("eval/episode_reward")
        if reward is not None:
            rewards.append((int(step), float(reward)))
            print(f"{step}: reward={reward:.3f}", flush=True)

    start = time.monotonic()
    make_inference_fn, learned_params, _ = ppo.train(
        environment=env,
        eval_env=eval_env,
        **train_params,
        network_factory=network_factory,
        seed=1,
        wrap_env_fn=wrapper.wrap_for_brax_training,
        num_eval_envs=num_eval_envs,
        progress_fn=progress,
    )
    del make_inference_fn
    elapsed = time.monotonic() - start
    with (out_dir / "params.pkl").open("wb") as f:
        pickle.dump(learned_params, f)
    (out_dir / "rewards.txt").write_text(
        "\n".join([f"# timesteps={timesteps} train_min={elapsed/60:.2f}"] + [f"{s}\t{r}" for s, r in rewards]) + "\n",
        encoding="utf-8",
    )
    return {
        "timesteps": timesteps,
        "train_min": elapsed / 60,
        "reward_points": rewards,
        "params_path": "verify/train/params.pkl",
        "rewards_path": "verify/train/rewards.txt",
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


def target_pose_and_height(default_pose: np.ndarray, step: int) -> tuple[np.ndarray, float]:
    squat = default_pose.copy()
    for offset in (0, 6):
        squat[offset + 0] = -0.28
        squat[offset + 3] = 0.55
        squat[offset + 4] = -0.28
    squat[14] = 0.06
    alpha = np.clip((step - 50.0) / 150.0, 0.0, 1.0) * (1.0 - np.clip((step - 300.0) / 150.0, 0.0, 1.0))
    return (default_pose * (1.0 - alpha) + squat * alpha).astype(np.float32), float(0.755 * (1.0 - alpha) + 0.68 * alpha)


def build_policy(env: G1SquatRecovery, params_path: Path):
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


def native_eval(params_path: Path, seconds: float) -> dict:
    env = G1SquatRecovery(config_overrides={"impl": "jax"})
    policy = build_policy(env, params_path)
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

    fell_at = None
    min_height = float("inf")
    max_pose_error = 0.0
    max_height_error = 0.0
    max_joint_violation = 0.0
    energy_proxy = 0.0
    samples = []

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

        target_pose, target_height = target_pose_and_height(default_pose, step)
        pose_error = float(np.mean(np.square(data.qpos[7:] - target_pose)))
        height = float(data.qpos[2])
        height_error = float((height - target_height) ** 2)
        quat = data.qpos[3:7]
        mat = np.empty(9)
        mujoco.mju_quat2Mat(mat, quat)
        up_z = float(mat.reshape(3, 3)[2, 2])
        fallen = height < 0.50 or up_z < 0.35
        if fallen and fell_at is None:
            fell_at = step * ctrl_dt

        min_height = min(min_height, height)
        max_pose_error = max(max_pose_error, pose_error)
        max_height_error = max(max_height_error, height_error)
        max_joint_violation = max(max_joint_violation, joint_limit_violation(model, data))
        data.ctrl[:] = default_pose + action_np * float(env._config.action_scale)
        for _ in range(n_substeps):
            mujoco.mj_step(model, data)
        energy_proxy += float(np.sum(np.square(data.ctrl)) * ctrl_dt)
        phase = np.fmod(phase + phase_dt + np.pi, 2 * np.pi) - np.pi
        last_action = action_np

        if step % max(1, int(0.2 / ctrl_dt)) == 0:
            samples.append({
                "t": round(step * ctrl_dt, 3),
                "base_height": height,
                "target_height": target_height,
                "pose_error": pose_error,
                "height_error": height_error,
                "up_z": up_z,
                "joint_limit_violation": max_joint_violation,
                "action_l2": float(np.sum(np.square(action_np))),
            })

    upright_s = seconds if fell_at is None else fell_at
    return {
        "baseline_exp18_upright_s": 1.24,
        "engine": "native mujoco.MjData closed-loop with Brax JAX inference params",
        "seconds": seconds,
        "ctrl_dt": ctrl_dt,
        "sim_dt": sim_dt,
        "n_substeps": n_substeps,
        "fell_at": fell_at,
        "upright_s": upright_s,
        "improved_vs_exp18": upright_s > 1.24,
        "min_height": min_height,
        "final_height": float(data.qpos[2]),
        "max_pose_error": max_pose_error,
        "max_height_error": max_height_error,
        "max_joint_limit_violation": max_joint_violation,
        "energy_proxy": energy_proxy,
        "verdict": "PASS_DIAGNOSTIC" if fell_at is None else ("IMPROVED_FAIL_DIAGNOSTIC" if upright_s > 1.24 else "FAIL_DIAGNOSTIC"),
        "samples": samples,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", action="store_true")
    parser.add_argument("--timesteps", type=int, default=300_000)
    parser.add_argument("--seconds", type=float, default=6.0)
    args = parser.parse_args()

    VERIFY.mkdir(parents=True, exist_ok=True)
    result = {"rollout": rollout_smoke()}
    if args.train:
        result["train"] = train(VERIFY / "train", args.timesteps)
        result["native"] = native_eval(VERIFY / "train" / "params.pkl", args.seconds)
    result["verdict"] = result.get("native", result["rollout"]).get("verdict", "PASS")
    (VERIFY / "g1-squat-recovery-longrun.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(result["verdict"], json.dumps(result.get("native", result["rollout"]), indent=2), flush=True)


if __name__ == "__main__":
    main()
