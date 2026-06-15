"""Fine-tune G1 squat reference tracking from an existing G1 walking policy."""

from __future__ import annotations

import argparse
import functools
import importlib.util
import json
import pickle
import sys
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


EXP_DIR = Path(__file__).resolve().parent
ROOT = EXP_DIR.parents[1]
VERIFY = EXP_DIR / "verify"
DEFAULT_SOURCE = Path("/home/yusun/playground-go1/runs/g1flat/params.pkl")
EXP20_RUNNER = ROOT / "experiments/20-g1-squat-reference-tracking/run_reference.py"
EXP20_ENV = ROOT / "experiments/20-g1-squat-reference-tracking/g1_squat_reference_env.py"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    parent = str(path.parent)
    if parent not in sys.path:
        sys.path.insert(0, parent)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def layer_shapes(params: Any) -> dict[str, dict[str, list[int]]]:
    policy_params = params[1]["params"]
    return {
        name: {key: list(value.shape) for key, value in layer.items()}
        for name, layer in policy_params.items()
    }


def ppo_config(timesteps: int):
    params = locomotion_params.brax_ppo_config("G1JoystickFlatTerrain")
    params.num_timesteps = timesteps
    params.num_envs = 512
    params.num_evals = 3
    params.num_minibatches = 8
    params.batch_size = 128
    params.episode_length = 300
    # Must match the existing G1 walking policy checkpoint.
    params.network_factory.policy_hidden_layer_sizes = (512, 256, 128)
    params.network_factory.value_hidden_layer_sizes = (512, 256, 128)
    return params


def compatibility(source_params_path: Path) -> dict:
    env_mod = load_module("exp20_env_for_compat", EXP20_ENV)
    env = env_mod.G1SquatReference(config_overrides={"impl": "jax"})
    params = ppo_config(1)
    network_factory = functools.partial(ppo_networks.make_ppo_networks, **params.network_factory)
    networks = network_factory(observation_size=env.observation_size, action_size=env.action_size)
    rng = jax.random.PRNGKey(0)
    dummy_params = networks.policy_network.init(rng)
    with source_params_path.open("rb") as f:
        source_params = pickle.load(f)
    source_shapes = layer_shapes(source_params)
    target_shapes = {
        name: {key: list(value.shape) for key, value in layer.items()}
        for name, layer in dummy_params["params"].items()
    }
    return {
        "source_params": str(source_params_path),
        "source_exists": source_params_path.exists(),
        "obs_size": env.observation_size,
        "action_size": env.action_size,
        "network": {
            "policy_hidden_layer_sizes": list(params.network_factory.policy_hidden_layer_sizes),
            "value_hidden_layer_sizes": list(params.network_factory.value_hidden_layer_sizes),
        },
        "source_policy_shapes": source_shapes,
        "target_policy_shapes": target_shapes,
        "policy_shape_match": source_shapes == target_shapes,
    }


def train_restored(source_params_path: Path, timesteps: int) -> dict:
    env_mod = load_module("exp20_env_for_train", EXP20_ENV)
    env = env_mod.G1SquatReference(config_overrides={"impl": "jax"})
    eval_env = env_mod.G1SquatReference(config_overrides={"impl": "jax"})
    params = ppo_config(timesteps)
    with source_params_path.open("rb") as f:
        source_params = pickle.load(f)
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
        seed=3,
        wrap_env_fn=wrapper.wrap_for_brax_training,
        num_eval_envs=num_eval_envs,
        progress_fn=progress,
        restore_params=source_params,
        restore_value_fn=True,
    )
    del make_inference_fn
    elapsed = time.monotonic() - start
    out_dir = VERIFY / "train"
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "params.pkl").open("wb") as f:
        pickle.dump(learned_params, f)
    (out_dir / "rewards.txt").write_text(
        "\n".join([f"# timesteps={timesteps} train_min={elapsed/60:.2f} source={source_params_path}"] + [f"{s}\t{r}" for s, r in rewards]) + "\n",
        encoding="utf-8",
    )
    return {
        "timesteps": timesteps,
        "train_min": elapsed / 60,
        "reward_points": rewards,
        "source_params": str(source_params_path),
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


def load_native_reference() -> tuple[np.ndarray, np.ndarray]:
    compiled = json.loads((ROOT / "experiments/17-motion-to-policy-loop/verify/g1_squat_reference.compiled.json").read_text(encoding="utf-8"))
    samples = compiled["trajectory"]["samples"]
    joints = np.asarray([sample["joint_targets"] for sample in samples], dtype=np.float32)
    heights = np.asarray([sample["base_height"] for sample in samples], dtype=np.float32)
    return joints, heights


def build_policy(env: Any, params_path: Path):
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


def native_eval(seconds: float) -> dict:
    env_mod = load_module("exp20_env_for_native_eval", EXP20_ENV)
    env = env_mod.G1SquatReference(config_overrides={"impl": "jax"})
    policy = build_policy(env, VERIFY / "train" / "params.pkl")
    ref_joints, ref_heights = load_native_reference()
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
    max_reference_error = 0.0
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

        ref_index = min(step, len(ref_heights) - 1)
        reference_error = float(np.mean(np.square(data.qpos[7:22] - ref_joints[ref_index])))
        height = float(data.qpos[2])
        height_error = float((height - float(ref_heights[ref_index])) ** 2)
        quat = data.qpos[3:7]
        mat = np.empty(9)
        mujoco.mju_quat2Mat(mat, quat)
        up_z = float(mat.reshape(3, 3)[2, 2])
        fallen = height < 0.50 or up_z < 0.35
        if fallen and fell_at is None:
            fell_at = step * ctrl_dt

        min_height = min(min_height, height)
        max_reference_error = max(max_reference_error, reference_error)
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
                "target_height": float(ref_heights[ref_index]),
                "reference_error": reference_error,
                "height_error": height_error,
                "up_z": up_z,
                "joint_limit_violation": max_joint_violation,
                "action_l2": float(np.sum(np.square(action_np))),
            })

    upright_s = seconds if fell_at is None else fell_at
    return {
        "baseline_exp18_to_exp20_upright_s": 1.24,
        "engine": "native mujoco.MjData closed-loop with restored G1 walking init params",
        "seconds": seconds,
        "ctrl_dt": ctrl_dt,
        "sim_dt": sim_dt,
        "n_substeps": n_substeps,
        "fell_at": fell_at,
        "upright_s": upright_s,
        "improved_vs_baseline": upright_s > 1.24,
        "min_height": min_height,
        "final_height": float(data.qpos[2]),
        "max_reference_error": max_reference_error,
        "max_height_error": max_height_error,
        "max_joint_limit_violation": max_joint_violation,
        "energy_proxy": energy_proxy,
        "verdict": "PASS_DIAGNOSTIC" if fell_at is None else ("IMPROVED_FAIL_DIAGNOSTIC" if upright_s > 1.24 else "FAIL_DIAGNOSTIC"),
        "samples": samples,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--train", action="store_true")
    parser.add_argument("--timesteps", type=int, default=200_000)
    parser.add_argument("--seconds", type=float, default=6.0)
    args = parser.parse_args()

    VERIFY.mkdir(parents=True, exist_ok=True)
    result = {"compatibility": compatibility(args.source)}
    if args.train:
        if not result["compatibility"]["policy_shape_match"]:
            raise SystemExit("source and target policy shapes do not match")
        result["train"] = train_restored(args.source, args.timesteps)
        result["native"] = native_eval(args.seconds)
    result["verdict"] = result.get("native", result["compatibility"]).get("verdict", "PASS" if result["compatibility"]["policy_shape_match"] else "FAIL")
    (VERIFY / "g1-stabilizer-init-probe.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(result["verdict"], json.dumps(result.get("native", result["compatibility"]), indent=2), flush=True)


if __name__ == "__main__":
    main()
