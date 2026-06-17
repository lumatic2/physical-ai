"""Train and evaluate a corridor-curriculum G1 squat policy."""

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

from g1_corridor_curriculum_env import CorridorCurriculumSquat


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
EXP49_P03 = ROOT / "experiments/49-g1-command-conditioned-squat-policy/verify/target-0p03/train/params.pkl"
EXP50_P03 = ROOT / "experiments/50-g1-stance-constrained-curriculum-ppo/verify/target-0p03-slip-0p08/train/params.pkl"

VISIBLE_GATE = {
    "drop_m": 0.08,
    "knee_delta_rad": 0.60,
    "hip_delta_rad": 0.35,
    "foot_contact_ratio": 0.90,
    "foot_slip_m": 0.08,
    "joint_violation_rad": 0.05,
}


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
    for candidate in [EXP50_P03, EXP49_P03, EXP46_PARAMS]:
        if candidate.exists():
            return candidate
    return EXP46_PARAMS


def ppo_config(timesteps: int):
    cfg = EXP28.ppo_config(timesteps)
    cfg.learning_rate = 8.0e-6
    cfg.num_evals = 3
    return cfg


def make_env(target_drop: float, support_floor: float, slip_limit: float) -> CorridorCurriculumSquat:
    return CorridorCurriculumSquat(
        target_drop=target_drop,
        support_floor=support_floor,
        slip_limit=slip_limit,
        config_overrides={"impl": "jax"},
    )


def qpos_index(model: mujoco.MjModel, joint_name: str) -> int:
    return int(model.jnt_qposadr[model.joint(joint_name).id])


def layer_shapes(params: Any) -> dict[str, dict[str, list[int]]]:
    return {
        name: {key: list(value.shape) for key, value in layer.items()}
        for name, layer in params[1]["params"].items()
    }


def compatibility(source: Path, target_drop: float, support_floor: float, slip_limit: float) -> dict:
    env = make_env(target_drop, support_floor, slip_limit)
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


def rollout_smoke(target_drop: float, support_floor: float, slip_limit: float, steps: int = 20) -> dict:
    env = make_env(target_drop, support_floor, slip_limit)
    reset_fn = jax.jit(env.reset)
    step_fn = jax.jit(env.step)
    state = reset_fn(jax.random.PRNGKey(0))
    zero = jp.zeros(env.action_size)
    rows = []
    for _ in range(steps):
        state = step_fn(state, zero)
        rows.append({
            "reward": float(state.reward),
            "drop": float(state.metrics["corridor_drop_m"]),
            "knee": float(state.metrics["corridor_knee_delta_rad"]),
            "hip": float(state.metrics["corridor_hip_delta_rad"]),
            "support": float(state.metrics["stance_support_margin"]),
            "slip": float(state.metrics["stance_foot_slip"]),
            "done": float(state.done),
        })
    return {
        "rollout_steps": steps,
        "reward_first": rows[0]["reward"],
        "reward_last": rows[-1]["reward"],
        "drop_max": max(row["drop"] for row in rows),
        "knee_max": max(row["knee"] for row in rows),
        "hip_max": max(row["hip"] for row in rows),
        "support_margin_min": min(row["support"] for row in rows),
        "foot_slip_max": max(row["slip"] for row in rows),
        "done_any": any(row["done"] > 0 for row in rows),
    }


def train(source: Path, target_drop: float, support_floor: float, slip_limit: float, timesteps: int, out_dir: Path, seed: int) -> dict:
    env = make_env(target_drop, support_floor, slip_limit)
    eval_env = make_env(target_drop, support_floor, slip_limit)
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
    train_dir = out_dir / "train"
    train_dir.mkdir(parents=True, exist_ok=True)
    params_path = train_dir / "params.pkl"
    with params_path.open("wb") as f:
        pickle.dump(learned_params, f)
    rewards_path = train_dir / "rewards.txt"
    rewards_path.write_text(
        "\n".join([
            f"# target_drop={target_drop} support_floor={support_floor} slip_limit={slip_limit}",
            f"# timesteps={timesteps} train_min={elapsed/60:.2f} seed={seed} source={source}",
            *[f"{s}\t{r}" for s, r in rewards],
        ]) + "\n",
        encoding="utf-8",
    )
    return {
        "target_drop": target_drop,
        "support_floor": support_floor,
        "slip_limit": slip_limit,
        "timesteps": timesteps,
        "train_min": elapsed / 60,
        "seed": seed,
        "reward_points": rewards,
        "source_params": str(source),
        "params_path": str(params_path.relative_to(EXP_DIR)),
        "rewards_path": str(rewards_path.relative_to(EXP_DIR)),
    }


def build_policy(env: CorridorCurriculumSquat, params_path: Path):
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


def visible_gap(native: dict[str, Any]) -> dict[str, float]:
    return {
        "drop_shortfall_m": max(0.0, VISIBLE_GATE["drop_m"] - native["visible_drop"]),
        "knee_shortfall_rad": max(0.0, VISIBLE_GATE["knee_delta_rad"] - native["max_knee_delta_rad"]),
        "hip_shortfall_rad": max(0.0, VISIBLE_GATE["hip_delta_rad"] - native["max_hip_pitch_delta_rad"]),
        "slip_excess_m": max(0.0, native["foot_slip_distance"] - VISIBLE_GATE["foot_slip_m"]),
    }


def native_eval(target_drop: float, support_floor: float, slip_limit: float, params_path: Path, seconds: float, out_dir: Path) -> dict:
    env = make_env(target_drop, support_floor, slip_limit)
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
    lk = qpos_index(model, "left_knee_joint")
    rk = qpos_index(model, "right_knee_joint")
    lh = qpos_index(model, "left_hip_pitch_joint")
    rh = qpos_index(model, "right_hip_pitch_joint")
    start_qpos = key.qpos.copy()
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
    first_support_breach_at = None
    first_slip_breach_at = None
    both_feet_contact_count = 0
    max_foot_slip = 0.0
    min_support_margin = float("inf")
    max_joint_violation = 0.0
    max_lr_imbalance = 0.0
    max_inverse_torque = 0.0
    max_knee_delta = 0.0
    max_hip_delta = 0.0
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

        data.ctrl[:] = np.clip(default_pose + action_np * float(env._config.action_scale), model.actuator_ctrlrange[:, 0], model.actuator_ctrlrange[:, 1])
        for _ in range(n_substeps):
            mujoco.mj_step(model, data)
        last_action = action_np

        height = float(data.qpos[2])
        final_height = height
        min_height = min(min_height, height)
        visible_drop_now = start_height - height
        if visible_drop_now >= VISIBLE_GATE["drop_m"] and first_visible_at is None:
            first_visible_at = round(t, 3)
        knee_delta = max(abs(float(data.qpos[lk] - start_qpos[lk])), abs(float(data.qpos[rk] - start_qpos[rk])))
        hip_delta = max(abs(float(data.qpos[lh] - start_qpos[lh])), abs(float(data.qpos[rh] - start_qpos[rh])))
        max_knee_delta = max(max_knee_delta, knee_delta)
        max_hip_delta = max(max_hip_delta, hip_delta)
        contacts = [
            float(data.sensordata[model.sensor_adr[sensor_id]]) > 0
            for sensor_id in foot_contact_sensor_ids
        ]
        both_feet = all(contacts)
        both_feet_contact_count += int(both_feet)
        support = EXP37.support_metrics(model, data, foot_geom_ids)
        min_support_margin = min(min_support_margin, support["support_margin"])
        if support["support_margin"] < support_floor and first_support_breach_at is None:
            first_support_breach_at = round(t, 3)
        foot_slip = float(np.max(np.linalg.norm(data.site_xpos[foot_site_ids, :2] - initial_foot_xy, axis=1)))
        max_foot_slip = max(max_foot_slip, foot_slip)
        if foot_slip > slip_limit and first_slip_breach_at is None:
            first_slip_breach_at = round(t, 3)
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
                "knee_delta": knee_delta,
                "hip_delta": hip_delta,
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
    native = {
        "target_drop": target_drop,
        "support_floor": support_floor,
        "slip_limit": slip_limit,
        "params_path": str(params_path),
        "start_height": start_height,
        "min_height": min_height,
        "visible_drop": visible_drop,
        "first_visible_at": first_visible_at,
        "max_knee_delta_rad": max_knee_delta,
        "max_hip_pitch_delta_rad": max_hip_delta,
        "fell_at": fell_at,
        "final_height": final_height,
        "return_to_stand": return_to_stand,
        "foot_contact_ratio": foot_contact_ratio,
        "foot_slip_distance": max_foot_slip,
        "min_support_margin": min_support_margin,
        "first_support_breach_at": first_support_breach_at,
        "first_slip_breach_at": first_slip_breach_at,
        "max_joint_limit_violation": max_joint_violation,
        "max_lr_normal_imbalance": max_lr_imbalance,
        "max_lower_inverse_torque": max_inverse_torque,
        "samples": samples,
    }
    native["pass_visible_gate"] = (
        native["fell_at"] is None
        and native["visible_drop"] >= VISIBLE_GATE["drop_m"]
        and native["max_knee_delta_rad"] >= VISIBLE_GATE["knee_delta_rad"]
        and native["max_hip_pitch_delta_rad"] >= VISIBLE_GATE["hip_delta_rad"]
        and native["return_to_stand"]
        and native["foot_contact_ratio"] >= VISIBLE_GATE["foot_contact_ratio"]
        and native["foot_slip_distance"] <= VISIBLE_GATE["foot_slip_m"]
        and native["max_joint_limit_violation"] <= VISIBLE_GATE["joint_violation_rad"]
    )
    native["recoverable_7cm_gate"] = (
        native["fell_at"] is None
        and native["visible_drop"] >= 0.07
        and native["return_to_stand"]
        and native["foot_contact_ratio"] >= VISIBLE_GATE["foot_contact_ratio"]
        and native["foot_slip_distance"] <= VISIBLE_GATE["foot_slip_m"]
        and native["max_joint_limit_violation"] <= VISIBLE_GATE["joint_violation_rad"]
    )
    native["visible_gap"] = visible_gap(native)
    if native["pass_visible_gate"]:
        native["verdict"] = "PASS_VISIBLE_8CM_GATE"
    elif native["recoverable_7cm_gate"]:
        native["verdict"] = "PASS_RECOVERABLE_7CM_GATE"
    elif native["fell_at"] is not None:
        native["verdict"] = "FAIL_FALL"
    elif native["visible_drop"] < 0.07:
        native["verdict"] = "DEPTH_PENDING_7CM"
    elif not native["return_to_stand"]:
        native["verdict"] = "RETURN_PENDING"
    elif native["foot_contact_ratio"] < VISIBLE_GATE["foot_contact_ratio"]:
        native["verdict"] = "CONTACT_PENDING"
    elif native["foot_slip_distance"] > VISIBLE_GATE["foot_slip_m"]:
        native["verdict"] = "STANCE_SLIP_PENDING"
    else:
        native["verdict"] = "GATE_PENDING"
    (out_dir / "native-eval.json").write_text(json.dumps(native, indent=2), encoding="utf-8")
    return native


def write_summary(result: dict, out_dir: Path) -> None:
    native = result["native"]
    train_result = result.get("train", {})
    fell = "never" if native["fell_at"] is None else f"{native['fell_at']:.2f}s"
    gap = native["visible_gap"]
    lines = [
        "# G1 Corridor Curriculum Training Summary",
        "",
        "| Verdict | Timesteps | Train min | Drop | Knee | Hip | Fell at | Final h | Contact | Slip | Support min |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        (
            f"| {native['verdict']} | {train_result.get('timesteps', 0)} | "
            f"{train_result.get('train_min', 0.0):.2f} | {native['visible_drop']:.4f}m | "
            f"{native['max_knee_delta_rad']:.3f} | {native['max_hip_pitch_delta_rad']:.3f} | "
            f"{fell} | {native['final_height']:.4f}m | {native['foot_contact_ratio']:.2f} | "
            f"{native['foot_slip_distance']:.3f}m | {native['min_support_margin']:.4f}m |"
        ),
        "",
        f"Visible gate gap: drop {gap['drop_shortfall_m']:.4f}m, knee {gap['knee_shortfall_rad']:.4f}rad, hip {gap['hip_shortfall_rad']:.4f}rad, slip excess {gap['slip_excess_m']:.4f}m.",
        "",
        "M19 closes only when this native gate and browser replay pass together.",
    ]
    (out_dir / "corridor-curriculum-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=None)
    parser.add_argument("--target-drop", type=float, default=0.078)
    parser.add_argument("--support-floor", type=float, default=-0.005)
    parser.add_argument("--slip-limit", type=float, default=0.08)
    parser.add_argument("--train", action="store_true")
    parser.add_argument("--timesteps", type=int, default=20_000)
    parser.add_argument("--seed", type=int, default=80)
    parser.add_argument("--seconds", type=float, default=6.0)
    args = parser.parse_args()

    source = args.source or default_source()
    out_dir = VERIFY / f"target-{args.target_drop:.3f}-slip-{args.slip_limit:.2f}".replace(".", "p")
    out_dir.mkdir(parents=True, exist_ok=True)
    result = {
        "planning_gate": {
            "team_validation_mode": "manual-pass",
            "spec_delta": "M19 curriculum training now targets the 7.7cm corridor with explicit drop/knee/hip/support/terminal rewards.",
            "perspectives": {
                "product": "tests whether the remaining visible-squat gap can be learned instead of hand-selected",
                "architecture": "small subclass of exp50 env; policy observation and checkpoint shape stay compatible",
                "security": "no secrets or external credentials",
                "qa": "compatibility, rollout smoke, restored PPO, native exp29 visible gate audit",
                "skeptic": "rewarding the full 8cm pose may destabilize the policy or regress to shallow stand",
            },
            "dod": [
                "corridor reward metrics execute",
                "restored PPO produces params",
                "native exp29 visible gate is audited with knee and hip metrics",
            ],
        },
        "web_sources": [
            {
                "url": "https://arxiv.org/html/2502.13013v1",
                "accessed": "2026-06-18",
                "use": "G1-class loco-manipulation work reports squatting to specified heights with height tracking and curriculum terms.",
            },
            {
                "url": "https://www.roboticsproceedings.org/rss21/p070.pdf",
                "accessed": "2026-06-18",
                "use": "RSS paper version of the G1 height-tracking/squat-to-height result.",
            },
            {
                "url": "https://arxiv.org/html/2502.12152v1",
                "accessed": "2026-06-18",
                "use": "G1 getting-up work supports staged curriculum/refinement for difficult humanoid transitions.",
            },
            {
                "url": "https://arxiv.org/abs/2505.20619",
                "accessed": "2026-06-18",
                "use": "Recent Unitree G1 curriculum work motivates multi-phase humanoid training instead of fixed controller search.",
            },
        ],
        "visible_gate": VISIBLE_GATE,
        "target_drop": args.target_drop,
        "support_floor": args.support_floor,
        "slip_limit": args.slip_limit,
        "source_params": str(source),
        "compatibility": compatibility(source, args.target_drop, args.support_floor, args.slip_limit),
        "rollout": rollout_smoke(args.target_drop, args.support_floor, args.slip_limit),
    }
    if not result["compatibility"]["policy_shape_match"]:
        raise SystemExit("source and target policy shapes do not match")
    if args.train:
        result["train"] = train(source, args.target_drop, args.support_floor, args.slip_limit, args.timesteps, out_dir, args.seed)
        params_path = out_dir / "train" / "params.pkl"
    else:
        params_path = source
    result["native"] = native_eval(args.target_drop, args.support_floor, args.slip_limit, params_path, args.seconds, out_dir)
    result["verdict"] = result["native"]["verdict"]
    write_summary(result, out_dir)
    (out_dir / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(result["verdict"], json.dumps(result["native"], indent=2), flush=True)


if __name__ == "__main__":
    main()
