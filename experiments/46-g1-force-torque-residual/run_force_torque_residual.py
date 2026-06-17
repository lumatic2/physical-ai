"""Train and evaluate force/torque-aware G1 squat residual attempts."""

from __future__ import annotations

import argparse
import functools
import importlib.util
import json
import pickle
import re
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

from g1_force_torque_env import EXP28, ForceTorqueAwareSquat


if not hasattr(jax, "device_put_replicated"):
    # Brax in the local runtime still calls this removed JAX helper.
    # It expects a leading device axis that its _unpmap helper later squeezes.
    def _device_put_replicated(x, devices):
        count = max(1, len(devices))
        return jax.device_put(jax.tree_util.tree_map(lambda y: jp.stack([y] * count), x))

    jax.device_put_replicated = _device_put_replicated  # type: ignore[attr-defined]


EXP_DIR = Path(__file__).resolve().parent
ROOT = EXP_DIR.parents[1]
VERIFY = EXP_DIR / "verify"
EXP42_PATH = ROOT / "experiments/42-g1-contact-inverse-force-probe/run_force_probe.py"


def load_exp42():
    spec = importlib.util.spec_from_file_location("exp42_force_probe", EXP42_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {EXP42_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EXP42 = load_exp42()
EXP37 = EXP42.EXP37


def ppo_config(timesteps: int):
    cfg = EXP28.ppo_config(timesteps)
    cfg.learning_rate = 1.5e-5
    cfg.num_evals = 3
    return cfg


def stage_slug(stage_height: float) -> str:
    return f"stage-{stage_height:.2f}".replace(".", "p")


def default_source() -> Path:
    exp38 = ROOT / "experiments/38-g1-support-aware-depth-finetune/verify/stage-0p74/train/params.pkl"
    return exp38 if exp38.exists() else EXP28.default_source()


def safe_inverse_summary(model: mujoco.MjModel, data: mujoco.MjData) -> dict:
    probe = mujoco.MjData(model)
    mujoco.mj_copyData(probe, model, data)
    return EXP42.inverse_summary(model, probe)


def build_policy(env: ForceTorqueAwareSquat, params_path: Path):
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


def layer_shapes(params: Any) -> dict[str, dict[str, list[int]]]:
    return {
        name: {key: list(value.shape) for key, value in layer.items()}
        for name, layer in params[1]["params"].items()
    }


def compatibility(source: Path, stage_height: float, controller_blend: float, reference_scale: float | None) -> dict:
    env = ForceTorqueAwareSquat(
        stage_height=stage_height,
        controller_blend=controller_blend,
        freeze_phase=True,
        blend_schedule="squat",
        reference_scale=reference_scale,
        config_overrides={"impl": "jax"},
    )
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


def rollout_smoke(stage_height: float, controller_blend: float, reference_scale: float | None, steps: int = 20) -> dict:
    env = ForceTorqueAwareSquat(
        stage_height=stage_height,
        controller_blend=controller_blend,
        freeze_phase=True,
        blend_schedule="squat",
        reference_scale=reference_scale,
        config_overrides={"impl": "jax"},
    )
    reset_fn = jax.jit(env.reset)
    step_fn = jax.jit(env.step)
    state = reset_fn(jax.random.PRNGKey(0))
    zero = jp.zeros(env.action_size)
    rewards = []
    balances = []
    torque_rewards = []
    force_gates = []
    dones = []
    for _ in range(steps):
        state = step_fn(state, zero)
        rewards.append(float(state.reward))
        balances.append(float(state.metrics["contact_force_balance"]))
        torque_rewards.append(float(state.metrics["lower_torque_limit"]))
        force_gates.append(float(state.metrics["depth_force_gate"]))
        dones.append(float(state.done))
    return {
        "rollout_steps": steps,
        "reward_first": rewards[0],
        "reward_last": rewards[-1],
        "contact_force_balance_min": min(balances),
        "lower_torque_limit_min": min(torque_rewards),
        "depth_force_gate_max": max(force_gates),
        "done_any": any(v > 0 for v in dones),
    }


def train(
    source: Path,
    stage_height: float,
    controller_blend: float,
    reference_scale: float | None,
    timesteps: int,
    attempt_dir: Path,
    seed: int,
) -> dict:
    env = ForceTorqueAwareSquat(
        stage_height=stage_height,
        controller_blend=controller_blend,
        freeze_phase=True,
        blend_schedule="squat",
        reference_scale=reference_scale,
        config_overrides={"impl": "jax"},
    )
    eval_env = ForceTorqueAwareSquat(
        stage_height=stage_height,
        controller_blend=controller_blend,
        freeze_phase=True,
        blend_schedule="squat",
        reference_scale=reference_scale,
        config_overrides={"impl": "jax"},
    )
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
            f"# controller_blend={controller_blend}",
            f"# reference_scale={reference_scale}",
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


def native_eval(
    stage_height: float,
    controller_blend: float,
    reference_scale: float | None,
    params_path: Path,
    seconds: float,
    out_dir: Path,
) -> dict:
    env = ForceTorqueAwareSquat(
        stage_height=stage_height,
        controller_blend=controller_blend,
        freeze_phase=True,
        blend_schedule="squat",
        reference_scale=reference_scale,
        config_overrides={"impl": "jax"},
    )
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

    gyro_adr = EXP28.sensor_adr(model, "gyro_pelvis")
    linvel_adr = EXP28.sensor_adr(model, "local_linvel_pelvis")
    imu_site = model.site("imu_in_pelvis").id
    ctrl_dt = float(env.dt)
    sim_dt = float(model.opt.timestep)
    n_substeps = max(1, round(ctrl_dt / sim_dt))
    total_steps = int(seconds / ctrl_dt)
    phase = np.ones(2, dtype=np.float32) * np.pi
    last_action = np.zeros(env.action_size, dtype=np.float32)
    command = np.zeros(3, dtype=np.float32)
    gravity_down = np.array([0.0, 0.0, -1.0], dtype=np.float32)
    rng = jax.random.PRNGKey(0)
    foot_site_ids = np.asarray(env._feet_site_id)
    foot_geom_ids = np.asarray([model.geom("left_foot").id, model.geom("right_foot").id])
    initial_foot_xy = data.site_xpos[foot_site_ids, :2].copy()
    foot_contact_sensor_ids = list(env._feet_floor_found_sensor)
    start_height = float(data.qpos[2])

    fell_at = None
    first_visible_at = None
    min_height = start_height
    final_height = start_height
    both_feet_contact_count = 0
    max_foot_slip = 0.0
    max_joint_violation = 0.0
    min_support_margin = float("inf")
    max_normal_force = 0.0
    max_lr_imbalance = 0.0
    max_inverse_torque = 0.0
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
        effective_blend = env._effective_controller_blend(jp.asarray(step, dtype=jp.int32))
        effective_blend = float(effective_blend)
        policy_targets = default_pose + action_np * float(env._config.action_scale)
        staged_pose = default_pose.copy()
        staged_pose[:15] = ref_joints[ref_index]
        data.ctrl[:] = (1.0 - effective_blend) * policy_targets + effective_blend * staged_pose
        for _ in range(n_substeps):
            mujoco.mj_step(model, data)
        last_action = action_np

        height = float(data.qpos[2])
        final_height = height
        min_height = min(min_height, height)
        visible_drop_now = start_height - height
        if visible_drop_now >= 0.08 and first_visible_at is None:
            first_visible_at = round(step * ctrl_dt, 3)
        contacts = [
            float(data.sensordata[model.sensor_adr[sensor_id]]) > 0
            for sensor_id in foot_contact_sensor_ids
        ]
        both_feet = all(contacts)
        both_feet_contact_count += int(both_feet)
        support = EXP37.support_metrics(model, data, foot_geom_ids)
        min_support_margin = min(min_support_margin, support["support_margin"])
        foot_slip = float(np.max(np.linalg.norm(data.site_xpos[foot_site_ids, :2] - initial_foot_xy, axis=1)))
        max_foot_slip = max(max_foot_slip, foot_slip)
        max_joint_violation = max(max_joint_violation, EXP28.joint_limit_violation(model, data))
        wrench = EXP42.contact_wrench_summary(model, data)
        inv = safe_inverse_summary(model, data)
        max_normal_force = max(max_normal_force, wrench["total_foot_normal"])
        max_lr_imbalance = max(max_lr_imbalance, wrench["lr_normal_imbalance"])
        max_inverse_torque = max(max_inverse_torque, inv["lower_inverse_linf"])
        quat = data.qpos[3:7]
        mat = np.empty(9)
        mujoco.mju_quat2Mat(mat, quat)
        up_z = float(mat.reshape(3, 3)[2, 2])
        if (height < 0.45 or up_z < 0.30) and fell_at is None:
            fell_at = round(step * ctrl_dt, 3)
        if step % max(1, int(0.2 / ctrl_dt)) == 0:
            samples.append({
                "t": round(step * ctrl_dt, 3),
                "height": height,
                "visible_drop": visible_drop_now,
                "target_height": float(ref_heights[ref_index]),
                "support_margin": support["support_margin"],
                "both_feet_contact": both_feet,
                "foot_slip_distance": foot_slip,
                "effective_controller_blend": effective_blend,
                "lr_normal_imbalance": wrench["lr_normal_imbalance"],
                "inverse_torque": inv["lower_inverse_linf"],
                "up_z": up_z,
            })

    foot_contact_ratio = both_feet_contact_count / max(1, total_steps)
    visible_drop = start_height - min_height
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
        verdict = "PASS_FORCE_TORQUE_VISIBLE_SQUAT"
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
        "max_joint_limit_violation": max_joint_violation,
        "max_total_foot_normal_force": max_normal_force,
        "max_lr_normal_imbalance": max_lr_imbalance,
        "max_lower_inverse_torque": max_inverse_torque,
        "pass_gate": pass_gate,
        "verdict": verdict,
        "samples": samples,
    }
    (out_dir / "native-eval.json").write_text(json.dumps(native, indent=2), encoding="utf-8")
    return native


def next_attempt_dir(stage_dir: Path, attempt_name: str | None) -> Path:
    attempts = stage_dir / "attempts"
    attempts.mkdir(parents=True, exist_ok=True)
    if attempt_name:
        return attempts / attempt_name
    existing = []
    for path in attempts.glob("attempt-*"):
        match = re.fullmatch(r"attempt-(\d+)", path.name)
        if match:
            existing.append(int(match.group(1)))
    return attempts / f"attempt-{(max(existing) + 1 if existing else 1):03d}"


def write_summary(stage_dir: Path, result: dict) -> None:
    native = result["native"]
    train = result.get("train", {})
    lines = [
        "# G1 Force/Torque Residual Summary",
        "",
        "| Attempt | Timesteps | Verdict | Drop | Fell at | Contact | Slip | Support min | LR imbalance | Inv torque |",
        "|---|---:|---|---:|---:|---:|---:|---:|---:|---:|",
        (
            f"| {result['attempt']} | {train.get('timesteps', 0)} | {native['verdict']} | "
            f"{native['visible_drop']:.4f}m | {native['fell_at'] if native['fell_at'] is not None else 'never'} | "
            f"{native['foot_contact_ratio']:.2f} | {native['foot_slip_distance']:.3f}m | "
            f"{native['min_support_margin']:.4f}m | {native['max_lr_normal_imbalance']:.2f} | "
            f"{native['max_lower_inverse_torque']:.1f} |"
        ),
        "",
        "M19 closes only when visible depth, no-fall, contact, stance, return, and browser replay gates pass together.",
    ]
    (stage_dir / "force-torque-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=None)
    parser.add_argument("--stage-height", type=float, default=0.74)
    parser.add_argument("--seconds", type=float, default=6.0)
    parser.add_argument("--controller-blend", type=float, default=0.18)
    parser.add_argument("--reference-scale", type=float, default=0.75)
    parser.add_argument("--train", action="store_true")
    parser.add_argument("--timesteps", type=int, default=20_000)
    parser.add_argument("--seed", type=int, default=46)
    parser.add_argument("--attempt", default=None)
    args = parser.parse_args()

    source = args.source or default_source()
    stage_dir = VERIFY / stage_slug(args.stage_height)
    attempt_dir = next_attempt_dir(stage_dir, args.attempt)
    attempt_dir.mkdir(parents=True, exist_ok=True)
    result = {
        "planning_gate": {
            "team_validation_mode": "manual-pass",
            "spec_delta": "M19 force/torque-aware residual reward probe",
            "perspectives": {
                "product": "push M19 from controller target search into policy learning",
                "architecture": "repo-local subclass; upstream MuJoCo Playground untouched",
                "security": "no secrets or external credentials",
                "qa": "compatibility, rollout smoke, restored PPO, native gate audit",
                "skeptic": "may still stay in standing attractor or fall at visible depth",
            },
            "dod": [
                "force/torque reward metrics execute in JAX rollout",
                "restored PPO produces params",
                "native visible squat gate evaluated with contact/inverse diagnostics",
            ],
        },
        "attempt": attempt_dir.name,
        "stage_height": args.stage_height,
        "controller_blend": args.controller_blend,
        "reference_scale": args.reference_scale,
        "source_params": str(source),
        "compatibility": compatibility(source, args.stage_height, args.controller_blend, args.reference_scale),
        "rollout": rollout_smoke(args.stage_height, args.controller_blend, args.reference_scale),
    }
    if not result["compatibility"]["policy_shape_match"]:
        raise SystemExit("source and target policy shapes do not match")
    if args.train:
        result["train"] = train(
            source,
            args.stage_height,
            args.controller_blend,
            args.reference_scale,
            args.timesteps,
            attempt_dir,
            args.seed,
        )
        params_path = attempt_dir / "train" / "params.pkl"
    else:
        params_path = source
    result["native"] = native_eval(
        args.stage_height,
        args.controller_blend,
        args.reference_scale,
        params_path,
        args.seconds,
        attempt_dir,
    )
    result["verdict"] = result["native"]["verdict"]
    (attempt_dir / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    write_summary(stage_dir, result)
    print(result["verdict"], json.dumps(result["native"], indent=2), flush=True)


if __name__ == "__main__":
    main()
