"""Run reset/step smoke and optional short PPO on the G1 squat env."""

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
from brax.training.agents.ppo import networks as ppo_networks
from brax.training.agents.ppo import train as ppo
from mujoco_playground import wrapper
from mujoco_playground.config import locomotion_params

from g1_squat_env import G1Squat


VERIFY = Path(__file__).resolve().parent / "verify"


def rollout_smoke() -> dict:
    env = G1Squat(config_overrides={"impl": "jax"})
    print("compile reset/step...", flush=True)
    reset_fn = jax.jit(env.reset)
    step_fn = jax.jit(env.step)
    state = reset_fn(jax.random.PRNGKey(0))
    zero = jp.zeros(env.action_size)
    rewards = []
    heights = []
    dones = []
    pose_errors = []
    for _ in range(5):
        state = step_fn(state, zero)
        rewards.append(float(state.reward))
        heights.append(float(state.data.qpos[2]))
        dones.append(float(state.done))
        pose_errors.append(float(state.metrics["pose_error"]))
    return {
        "action_size": int(env.action_size),
        "obs_state_shape": list(state.obs["state"].shape),
        "obs_privileged_shape": list(state.obs["privileged_state"].shape),
        "rollout_steps": 5,
        "reward_first": rewards[0],
        "reward_last": rewards[-1],
        "height_min": min(heights),
        "height_last": heights[-1],
        "done_any": any(v > 0 for v in dones),
        "pose_error_last": pose_errors[-1],
    }


def train_smoke(out_dir: Path, timesteps: int) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    env = G1Squat(config_overrides={"impl": "jax"})
    eval_env = G1Squat(config_overrides={"impl": "jax"})
    params = locomotion_params.brax_ppo_config("G1JoystickFlatTerrain")
    params.num_timesteps = timesteps
    params.num_envs = 512
    params.num_evals = 2
    params.num_minibatches = 8
    params.batch_size = 128
    params.episode_length = 300
    params.network_factory.policy_hidden_layer_sizes = (128, 64)
    params.network_factory.value_hidden_layer_sizes = (128, 64)
    network_factory = functools.partial(
        ppo_networks.make_ppo_networks,
        **params.network_factory,
    )
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
        seed=0,
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", action="store_true")
    parser.add_argument("--timesteps", type=int, default=100_000)
    parser.add_argument("--out", type=Path, default=VERIFY)
    args = parser.parse_args()

    VERIFY.mkdir(parents=True, exist_ok=True)
    result = {"rollout": rollout_smoke()}
    if args.train:
        result["train"] = train_smoke(args.out / "train", args.timesteps)
    result["verdict"] = "PASS" if not result["rollout"]["done_any"] else "FAIL"
    (VERIFY / "g1-squat-env-smoke.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(result["verdict"], json.dumps(result["rollout"], indent=2))


if __name__ == "__main__":
    main()
