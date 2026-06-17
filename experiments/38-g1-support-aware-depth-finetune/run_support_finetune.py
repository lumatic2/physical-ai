"""Run support-aware staged G1 squat finetune smoke."""

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

from g1_support_depth_env import G1SupportAwareDepth


if not hasattr(jax, "device_put_replicated"):
    # Brax in the current local runtime still calls the removed JAX helper.
    # It expects a leading device axis that its _unpmap helper later squeezes.
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


def stage_slug(stage_height: float) -> str:
    return f"stage-{stage_height:.2f}".replace(".", "p")


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


def compatibility(source: Path, stage_height: float) -> dict:
    env = G1SupportAwareDepth(stage_height=stage_height, config_overrides={"impl": "jax"})
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
    source_shapes = layer_shapes(source_params)
    return {
        "stage_height": stage_height,
        "source_params": str(source),
        "source_exists": source.exists(),
        "obs_size": env.observation_size,
        "action_size": env.action_size,
        "policy_shape_match": source_shapes == target_shapes,
    }


def rollout_smoke(stage_height: float, steps: int = 20) -> dict:
    env = G1SupportAwareDepth(stage_height=stage_height, config_overrides={"impl": "jax"})
    reset_fn = jax.jit(env.reset)
    step_fn = jax.jit(env.step)
    state = reset_fn(jax.random.PRNGKey(0))
    zero = jp.zeros(env.action_size)
    heights = []
    support_margins = []
    vertical_velocities = []
    rewards = []
    dones = []
    for _ in range(steps):
        state = step_fn(state, zero)
        heights.append(float(state.data.qpos[2]))
        support_margins.append(float(state.metrics["support_margin"]))
        vertical_velocities.append(float(state.metrics["vertical_velocity"]))
        rewards.append(float(state.reward))
        dones.append(float(state.done))
    return {
        "stage_height": stage_height,
        "rollout_steps": steps,
        "height_min": min(heights),
        "support_margin_min": min(support_margins),
        "vertical_velocity_min": min(vertical_velocities),
        "reward_first": rewards[0],
        "reward_last": rewards[-1],
        "done_any": any(v > 0 for v in dones),
    }


def train(source: Path, stage_height: float, timesteps: int, stage_dir: Path) -> dict:
    env = G1SupportAwareDepth(stage_height=stage_height, config_overrides={"impl": "jax"})
    eval_env = G1SupportAwareDepth(stage_height=stage_height, config_overrides={"impl": "jax"})
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
        seed=6,
        wrap_env_fn=wrapper.wrap_for_brax_training,
        num_eval_envs=num_eval_envs,
        progress_fn=progress,
        restore_params=source_params,
        restore_value_fn=True,
    )
    elapsed = time.monotonic() - start
    out_dir = stage_dir / "train"
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "params.pkl").open("wb") as f:
        pickle.dump(learned_params, f)
    (out_dir / "rewards.txt").write_text(
        "\n".join([
            f"# stage_height={stage_height}",
            f"# timesteps={timesteps} train_min={elapsed/60:.2f} source={source}",
            *[f"{s}\t{r}" for s, r in rewards],
        ]) + "\n",
        encoding="utf-8",
    )
    return {
        "stage_height": stage_height,
        "timesteps": timesteps,
        "train_min": elapsed / 60,
        "reward_points": rewards,
        "source_params": str(source),
        "params_path": str((out_dir / "params.pkl").relative_to(EXP_DIR)),
        "rewards_path": str((out_dir / "rewards.txt").relative_to(EXP_DIR)),
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
    return {
        "support_margin": float(np.min(margins)),
        "inside_support": bool(np.min(margins) >= 0.0),
    }


def build_policy(env: G1SupportAwareDepth, params_path: Path):
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


def native_eval(stage_height: float, params_path: Path, seconds: float, stage_dir: Path) -> dict:
    env = G1SupportAwareDepth(stage_height=stage_height, config_overrides={"impl": "jax"})
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
    min_height = float("inf")
    final_height = None
    min_support_margin = float("inf")
    max_downward_velocity = 0.0
    last_height = start_height
    both_feet_contact_count = 0
    hold_count = 0
    max_foot_slip = 0.0
    max_joint_violation = 0.0
    max_reference_error = 0.0
    max_height_error = 0.0
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
        height = float(data.qpos[2])
        final_height = height
        vertical_velocity = (height - last_height) / ctrl_dt if step > 0 else 0.0
        max_downward_velocity = min(max_downward_velocity, vertical_velocity)
        support = support_metrics(model, data)
        min_support_margin = min(min_support_margin, support["support_margin"])
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
        if height <= stage_height + 0.005 and both_feet:
            hold_count += 1
        foot_slip = float(np.max(np.linalg.norm(data.site_xpos[foot_site_ids, :2] - initial_foot_xy, axis=1)))
        max_foot_slip = max(max_foot_slip, foot_slip)
        if (height < 0.45 or up_z < 0.30) and fell_at is None:
            fell_at = step * ctrl_dt
        min_height = min(min_height, height)
        max_reference_error = max(max_reference_error, reference_error)
        max_height_error = max(max_height_error, height_error)
        max_joint_violation = max(max_joint_violation, joint_limit_violation(model, data))

        data.ctrl[:] = default_pose + action_np * float(env._config.action_scale)
        for _ in range(n_substeps):
            mujoco.mj_step(model, data)
        phase = np.fmod(phase + phase_dt + np.pi, 2 * np.pi) - np.pi
        last_action = action_np
        last_height = height

        if step % max(1, int(0.2 / ctrl_dt)) == 0:
            samples.append({
                "t": round(step * ctrl_dt, 3),
                "base_height": height,
                "visible_drop": start_height - height,
                "target_height": float(ref_heights[ref_index]),
                "support_margin": support["support_margin"],
                "vertical_velocity": vertical_velocity,
                "both_feet_contact": both_feet,
                "foot_slip_distance": foot_slip,
                "up_z": up_z,
            })

    visible_drop = start_height - min_height
    hold_duration = hold_count * ctrl_dt
    foot_contact_ratio = both_feet_contact_count / max(1, total_steps)
    return_to_stand = final_height is not None and final_height >= 0.74
    stage_passed = (
        fell_at is None
        and visible_drop >= 0.08
        and hold_duration >= 0.5
        and return_to_stand
        and foot_contact_ratio >= 0.90
        and max_foot_slip <= 0.15
    )
    native = {
        "stage_height": stage_height,
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
        "foot_contact_ratio": foot_contact_ratio,
        "foot_slip_distance": max_foot_slip,
        "min_support_margin": min_support_margin,
        "max_downward_velocity": max_downward_velocity,
        "max_reference_error": max_reference_error,
        "max_height_error": max_height_error,
        "max_joint_limit_violation": max_joint_violation,
        "stage_passed": stage_passed,
        "verdict": "PASS_STAGE_VISIBLE" if stage_passed else ("DEPTH_PENDING" if fell_at is None else "FAIL_FALL"),
        "samples": samples,
    }
    (stage_dir / "native-eval.json").write_text(json.dumps(native, indent=2), encoding="utf-8")
    return native


def write_summary(result: dict, stage_dir: Path) -> None:
    native = result["native"]
    train = result.get("train", {})
    lines = [
        "# G1 Support-Aware Depth Finetune Summary",
        "",
        "| Verdict | Timesteps | Train min | Drop | Fell at | Contact | Support min | Slip |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    fell = "never" if native["fell_at"] is None else f"{native['fell_at']:.2f}s"
    lines.append(
        f"| {native['verdict']} | {train.get('timesteps', 0)} | {train.get('train_min', 0.0):.2f} | "
        f"{native['visible_drop']:.4f}m | {fell} | {native['foot_contact_ratio']:.2f} | "
        f"{native['min_support_margin']:.4f}m | {native['foot_slip_distance']:.3f}m |"
    )
    lines.append("")
    lines.append("M19 remains open unless native and browser visible squat gates both pass.")
    (stage_dir / "support-aware-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=None)
    parser.add_argument("--stage-height", type=float, default=0.74)
    parser.add_argument("--train", action="store_true")
    parser.add_argument("--timesteps", type=int, default=50_000)
    parser.add_argument("--seconds", type=float, default=6.0)
    args = parser.parse_args()

    source = args.source or default_source()
    stage_dir = VERIFY / stage_slug(args.stage_height)
    stage_dir.mkdir(parents=True, exist_ok=True)
    result = {
        "compatibility": compatibility(source, args.stage_height),
        "rollout": rollout_smoke(args.stage_height),
    }
    if args.train:
        if not result["compatibility"]["policy_shape_match"]:
            raise SystemExit("source and target policy shapes do not match")
        result["train"] = train(source, args.stage_height, args.timesteps, stage_dir)
        params_path = stage_dir / "train" / "params.pkl"
    else:
        params_path = source
    result["native"] = native_eval(args.stage_height, params_path, args.seconds, stage_dir)
    result["verdict"] = result["native"]["verdict"]
    write_summary(result, stage_dir)
    out_path = stage_dir / "g1-support-aware-depth-finetune.json"
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(result["verdict"], json.dumps(result["native"], indent=2), flush=True)


if __name__ == "__main__":
    main()
