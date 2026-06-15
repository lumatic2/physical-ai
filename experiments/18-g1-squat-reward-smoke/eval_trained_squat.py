"""Evaluate the short-trained G1 squat params in native MuJoCo.

This is a diagnostic gate, not a claim that the squat skill is solved. It
reuses the Brax inference params from smoke_squat_env.py, runs a closed-loop
native MuJoCo rollout, and records fall/height/pose/energy metrics.
"""

from __future__ import annotations

import argparse
import json
import pickle
from pathlib import Path

import jax
import jax.numpy as jp
import mujoco
import numpy as np
from brax.training.acme import running_statistics
from brax.training.agents.ppo import networks as ppo_networks
from mujoco_playground.config import locomotion_params

from g1_squat_env import G1Squat


EXP_DIR = Path(__file__).resolve().parent
VERIFY = EXP_DIR / "verify"
DEFAULT_PARAMS = VERIFY / "train" / "params.pkl"
DEFAULT_OUT = VERIFY / "g1-squat-trained-native-eval.json"


def sensor_adr(model: mujoco.MjModel, name: str) -> int:
    sensor = model.sensor(name)
    return int(sensor.adr[0])


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
        squat[offset + 0] = -0.40
        squat[offset + 3] = 0.82
        squat[offset + 4] = -0.42
    squat[14] = 0.10

    descend = np.clip(step / 75.0, 0.0, 1.0)
    ascend = np.clip((step - 125.0) / 125.0, 0.0, 1.0)
    alpha = descend * (1.0 - ascend)
    pose = default_pose * (1.0 - alpha) + squat * alpha
    height = 0.755 * (1.0 - alpha) + 0.62 * alpha
    return pose.astype(np.float32), float(height)


def build_policy(env: G1Squat, params_path: Path):
    with params_path.open("rb") as f:
        params = pickle.load(f)
    normalizer_params, policy_params = params[0], params[1]

    ppo_params = locomotion_params.brax_ppo_config("G1JoystickFlatTerrain")
    ppo_params.network_factory.policy_hidden_layer_sizes = (128, 64)
    ppo_params.network_factory.value_hidden_layer_sizes = (128, 64)
    networks = ppo_networks.make_ppo_networks(
        observation_size=env.observation_size,
        action_size=env.action_size,
        preprocess_observations_fn=running_statistics.normalize,
        **ppo_params.network_factory,
    )
    make_inference_fn = ppo_networks.make_inference_fn(networks)
    return make_inference_fn((normalizer_params, policy_params), deterministic=True)


def run_eval(params_path: Path, seconds: float, out_path: Path) -> dict:
    env = G1Squat(config_overrides={"impl": "jax"})
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
    action_scale = float(env._config.action_scale)
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
    action_l2_sum = 0.0
    samples = []

    for step in range(total_steps):
        gyro = data.sensordata[gyro_adr : gyro_adr + 3]
        linvel = data.sensordata[linvel_adr : linvel_adr + 3]
        gravity = data.site_xmat[imu_site].reshape(3, 3).T @ gravity_down
        joint_angles = data.qpos[7:] - default_pose
        joint_vel = data.qvel[6:]
        phase_obs = np.concatenate([np.cos(phase), np.sin(phase)])
        obs = np.concatenate(
            [linvel, gyro, gravity, command, joint_angles, joint_vel, last_action, phase_obs]
        ).astype(np.float32)
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
        fallen = height < 0.45 or up_z < 0.35
        if fallen and fell_at is None:
            fell_at = step * ctrl_dt

        min_height = min(min_height, height)
        max_pose_error = max(max_pose_error, pose_error)
        max_height_error = max(max_height_error, height_error)
        max_joint_violation = max(max_joint_violation, joint_limit_violation(model, data))
        action_l2_sum += float(np.sum(np.square(action_np)) * ctrl_dt)

        data.ctrl[:] = default_pose + action_np * action_scale
        for _ in range(n_substeps):
            mujoco.mj_step(model, data)
        energy_proxy += float(np.sum(np.square(data.ctrl)) * ctrl_dt)
        phase = np.fmod(phase + phase_dt + np.pi, 2 * np.pi) - np.pi
        last_action = action_np

        if step % max(1, int(0.2 / ctrl_dt)) == 0:
            samples.append(
                {
                    "t": round(step * ctrl_dt, 3),
                    "base_height": height,
                    "target_height": target_height,
                    "pose_error": pose_error,
                    "height_error": height_error,
                    "up_z": up_z,
                    "joint_limit_violation": max_joint_violation,
                    "action_l2": float(np.sum(np.square(action_np))),
                }
            )

    result = {
        "source": "experiments/18-g1-squat-reward-smoke/verify/train/params.pkl",
        "engine": "native mujoco.MjData closed-loop with Brax JAX inference params",
        "seconds": seconds,
        "ctrl_dt": ctrl_dt,
        "sim_dt": sim_dt,
        "n_substeps": n_substeps,
        "steps": total_steps,
        "fell_at": fell_at,
        "upright_s": seconds if fell_at is None else fell_at,
        "min_height": min_height,
        "final_height": float(data.qpos[2]),
        "max_pose_error": max_pose_error,
        "max_height_error": max_height_error,
        "max_joint_limit_violation": max_joint_violation,
        "energy_proxy": energy_proxy,
        "action_l2_sum": action_l2_sum,
        "verdict": "PASS_DIAGNOSTIC" if fell_at is None else "FAIL_DIAGNOSTIC",
        "samples": samples,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--params", type=Path, default=DEFAULT_PARAMS)
    parser.add_argument("--seconds", type=float, default=6.0)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    result = run_eval(args.params, args.seconds, args.out)
    print(
        result["verdict"],
        f"upright_s={result['upright_s']:.2f}",
        f"min_height={result['min_height']:.3f}",
        f"max_pose_error={result['max_pose_error']:.4f}",
        f"energy={result['energy_proxy']:.2f}",
        flush=True,
    )


if __name__ == "__main__":
    main()
