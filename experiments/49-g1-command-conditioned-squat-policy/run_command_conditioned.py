"""Train and evaluate a command-conditioned G1 visible squat policy."""

from __future__ import annotations

import argparse
import functools
import importlib.util
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

from g1_command_squat_env import CommandConditionedSquat


if not hasattr(jax, "device_put_replicated"):
    def _device_put_replicated(x, devices):
        count = max(1, len(devices))
        return jax.device_put(jax.tree_util.tree_map(lambda y: jp.stack([y] * count), x))

    jax.device_put_replicated = _device_put_replicated  # type: ignore[attr-defined]


EXP_DIR = Path(__file__).resolve().parent
ROOT = EXP_DIR.parents[1]
VERIFY = EXP_DIR / "verify"
EXP28_PATH = ROOT / "experiments/28-g1-controlled-squat-stage0p74/run_controlled_squat.py"
EXP37_PATH = ROOT / "experiments/37-g1-com-support-squat-guard/run_support_guard.py"
EXP42_PATH = ROOT / "experiments/42-g1-contact-inverse-force-probe/run_force_probe.py"
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


def default_source() -> Path:
    return EXP46_PARAMS if EXP46_PARAMS.exists() else EXP28.default_source()


def ppo_config(timesteps: int):
    cfg = EXP28.ppo_config(timesteps)
    cfg.learning_rate = 1.5e-5
    cfg.num_evals = 3
    return cfg


def layer_shapes(params: Any) -> dict[str, dict[str, list[int]]]:
    return {
        name: {key: list(value.shape) for key, value in layer.items()}
        for name, layer in params[1]["params"].items()
    }


def make_env(target_drop: float) -> CommandConditionedSquat:
    return CommandConditionedSquat(target_drop=target_drop, config_overrides={"impl": "jax"})


def compatibility(source: Path, target_drop: float) -> dict:
    env = make_env(target_drop)
    cfg = ppo_config(1)
    networks = ppo_networks.make_ppo_networks(
        observation_size=env.observation_size,
        action_size=env.action_size,
        **cfg.network_factory,
    )
    target = networks.policy_network.init(jax.random.PRNGKey(0))
    with source.open("rb") as f:
        source_params = pickle.load(f)
    return {
        "source_params": str(source),
        "source_exists": source.exists(),
        "obs_size": env.observation_size,
        "action_size": env.action_size,
        "policy_shape_match": layer_shapes(source_params) == {
            name: {key: list(value.shape) for key, value in layer.items()}
            for name, layer in target["params"].items()
        },
    }


def rollout_smoke(target_drop: float, steps: int = 20) -> dict:
    env = make_env(target_drop)
    reset_fn = jax.jit(env.reset)
    step_fn = jax.jit(env.step)
    state = reset_fn(jax.random.PRNGKey(0))
    zero = jp.zeros(env.action_size)
    rewards = []
    target_fractions = []
    target_heights = []
    command_progress = []
    support_gates = []
    dones = []
    for _ in range(steps):
        state = step_fn(state, zero)
        rewards.append(float(state.reward))
        target_fractions.append(float(state.metrics["command_target_fraction"]))
        target_heights.append(float(state.metrics["command_target_height"]))
        command_progress.append(float(state.metrics["command_progress"]))
        support_gates.append(float(state.metrics["command_support_gate"]))
        dones.append(float(state.done))
    return {
        "rollout_steps": steps,
        "reward_first": rewards[0],
        "reward_last": rewards[-1],
        "target_fraction_last": target_fractions[-1],
        "target_height_min": min(target_heights),
        "command_progress_max": max(command_progress),
        "support_gate_min": min(support_gates),
        "done_any": any(v > 0 for v in dones),
    }


def train(source: Path, target_drop: float, timesteps: int, attempt_dir: Path, seed: int) -> dict:
    env = make_env(target_drop)
    eval_env = make_env(target_drop)
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
            f"# target_drop={target_drop}",
            f"# timesteps={timesteps} train_min={elapsed/60:.2f} seed={seed} source={source}",
            *[f"{s}\t{r}" for s, r in rewards],
        ]) + "\n",
        encoding="utf-8",
    )
    return {
        "target_drop": target_drop,
        "timesteps": timesteps,
        "train_min": elapsed / 60,
        "seed": seed,
        "reward_points": rewards,
        "source_params": str(source),
        "params_path": str(params_path.relative_to(EXP_DIR)),
        "rewards_path": str(rewards_path.relative_to(EXP_DIR)),
    }


def build_policy(env: CommandConditionedSquat, params_path: Path):
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


def safe_inverse_summary(model: mujoco.MjModel, data: mujoco.MjData) -> dict:
    probe = mujoco.MjData(model)
    mujoco.mj_copyData(probe, model, data)
    return EXP42.inverse_summary(model, probe)


def native_eval(target_drop: float, params_path: Path, seconds: float, out_dir: Path) -> dict:
    env = make_env(target_drop)
    policy = build_policy(env, params_path)
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
    foot_site_ids = np.asarray(env._feet_site_id)
    foot_geom_ids = np.asarray([model.geom("left_foot").id, model.geom("right_foot").id])
    foot_contact_sensor_ids = list(env._feet_floor_found_sensor)
    initial_foot_xy = data.site_xpos[foot_site_ids, :2].copy()
    ctrl_dt = float(env.dt)
    sim_dt = float(model.opt.timestep)
    n_substeps = max(1, round(ctrl_dt / sim_dt))
    total_steps = int(seconds / ctrl_dt)
    phase = np.ones(2, dtype=np.float32) * np.pi
    last_action = np.zeros(env.action_size, dtype=np.float32)
    gravity_down = np.array([0.0, 0.0, -1.0], dtype=np.float32)
    rng = jax.random.PRNGKey(0)
    start_height = float(data.qpos[2])

    min_height = start_height
    final_height = start_height
    fell_at = None
    first_visible_at = None
    both_feet_contact_count = 0
    max_foot_slip = 0.0
    min_support_margin = float("inf")
    first_support_breach_at = None
    max_joint_violation = 0.0
    max_lr_imbalance = 0.0
    max_inverse_torque = 0.0
    max_action_norm = 0.0
    samples = []

    for step in range(total_steps):
        t = step * ctrl_dt
        command = np.asarray(env._squat_command(jp.asarray(step, dtype=jp.int32)), dtype=np.float32)
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
        max_action_norm = max(max_action_norm, float(np.linalg.norm(action_np)))

        data.ctrl[:] = np.clip(default_pose + action_np * float(env._config.action_scale), model.actuator_ctrlrange[:, 0], model.actuator_ctrlrange[:, 1])
        for _ in range(n_substeps):
            mujoco.mj_step(model, data)
        last_action = action_np

        height = float(data.qpos[2])
        final_height = height
        min_height = min(min_height, height)
        visible_drop_now = start_height - height
        if visible_drop_now >= 0.08 and first_visible_at is None:
            first_visible_at = round(t, 3)
        contacts = [
            float(data.sensordata[model.sensor_adr[sensor_id]]) > 0
            for sensor_id in foot_contact_sensor_ids
        ]
        both_feet = all(contacts)
        both_feet_contact_count += int(both_feet)
        support = EXP37.support_metrics(model, data, foot_geom_ids)
        min_support_margin = min(min_support_margin, support["support_margin"])
        if support["support_margin"] < 0.0 and first_support_breach_at is None:
            first_support_breach_at = round(t, 3)
        foot_slip = float(np.max(np.linalg.norm(data.site_xpos[foot_site_ids, :2] - initial_foot_xy, axis=1)))
        max_foot_slip = max(max_foot_slip, foot_slip)
        max_joint_violation = max(max_joint_violation, EXP28.joint_limit_violation(model, data))
        wrench = EXP42.contact_wrench_summary(model, data)
        inv = safe_inverse_summary(model, data)
        max_lr_imbalance = max(max_lr_imbalance, wrench["lr_normal_imbalance"])
        max_inverse_torque = max(max_inverse_torque, inv["lower_inverse_linf"])
        quat = data.qpos[3:7]
        mat = np.empty(9)
        mujoco.mju_quat2Mat(mat, quat)
        up_z = float(mat.reshape(3, 3)[2, 2])
        if (height < 0.45 or up_z < 0.30) and fell_at is None:
            fell_at = round(t, 3)

        if step % max(1, int(0.2 / ctrl_dt)) == 0:
            samples.append({
                "t": round(t, 3),
                "height": height,
                "visible_drop": visible_drop_now,
                "command": [float(v) for v in command],
                "support_margin": support["support_margin"],
                "both_feet_contact": both_feet,
                "foot_slip_distance": foot_slip,
                "lr_normal_imbalance": wrench["lr_normal_imbalance"],
                "inverse_torque": inv["lower_inverse_linf"],
                "up_z": up_z,
                "action_norm": float(np.linalg.norm(action_np)),
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
        verdict = "PASS_COMMAND_CONDITIONED_VISIBLE_SQUAT"
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
        "target_drop": target_drop,
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
        "max_action_norm": max_action_norm,
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
        "# G1 Command-Conditioned Squat Policy Summary",
        "",
        "| Verdict | Timesteps | Train min | Drop | Fell at | Final h | Contact | Slip | Support min |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        (
            f"| {native['verdict']} | {train_result.get('timesteps', 0)} | "
            f"{train_result.get('train_min', 0.0):.2f} | {native['visible_drop']:.4f}m | "
            f"{fell} | {native['final_height']:.4f}m | {native['foot_contact_ratio']:.2f} | "
            f"{native['foot_slip_distance']:.3f}m | {native['min_support_margin']:.4f}m |"
        ),
        "",
        "M19 closes only when visible depth, no-fall, contact, stance, return, knee/hip pose, and browser replay gates pass together.",
    ]
    (out_dir / "command-conditioned-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=None)
    parser.add_argument("--target-drop", type=float, default=0.08)
    parser.add_argument("--train", action="store_true")
    parser.add_argument("--timesteps", type=int, default=20_000)
    parser.add_argument("--seed", type=int, default=49)
    parser.add_argument("--seconds", type=float, default=6.0)
    args = parser.parse_args()

    source = args.source or default_source()
    out_dir = VERIFY / f"target-{args.target_drop:.2f}".replace(".", "p")
    out_dir.mkdir(parents=True, exist_ok=True)
    result = {
        "planning_gate": {
            "team_validation_mode": "manual-pass",
            "spec_delta": "M19 target command is moved into the policy observation/reward contract while keeping the restored stabilizer network shape.",
            "perspectives": {
                "product": "moves M19 from external target injection toward a learned command-conditioned squat skill",
                "architecture": "reuses existing command observation slots to preserve checkpoint compatibility",
                "security": "no secrets or external credentials",
                "qa": "compatibility, rollout smoke, restored PPO, native gate audit",
                "skeptic": "short PPO may ignore the repurposed command or preserve the standing attractor",
            },
            "dod": [
                "source checkpoint shape remains compatible",
                "command-conditioned reward metrics execute",
                "restored PPO produces params",
                "native visible squat gate is audited",
            ],
        },
        "target_drop": args.target_drop,
        "source_params": str(source),
        "compatibility": compatibility(source, args.target_drop),
        "rollout": rollout_smoke(args.target_drop),
    }
    if not result["compatibility"]["policy_shape_match"]:
        raise SystemExit("source and target policy shapes do not match")
    if args.train:
        result["train"] = train(source, args.target_drop, args.timesteps, out_dir, args.seed)
        params_path = out_dir / "train" / "params.pkl"
    else:
        params_path = source
    result["native"] = native_eval(args.target_drop, params_path, args.seconds, out_dir)
    result["verdict"] = result["native"]["verdict"]
    write_summary(result, out_dir)
    (out_dir / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(result["verdict"], json.dumps(result["native"], indent=2), flush=True)


if __name__ == "__main__":
    main()
