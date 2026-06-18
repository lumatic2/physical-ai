"""Train/evaluate a contact-aware future-reference tracker for G1 visible squat."""

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


EXP_DIR = Path(__file__).resolve().parent
ROOT = EXP_DIR.parents[1]
VERIFY = EXP_DIR / "verify"
EXP80_RUNNER = ROOT / "experiments/80-g1-corridor-curriculum-training/run_corridor_curriculum.py"
EXP105_PARAMS = ROOT / "experiments/105-g1-future-reference-observation-tracker/verify/train/params.pkl"
EXP103_PARAMS = ROOT / "experiments/103-g1-explicit-reference-command-tracker/verify/target-0p090-slip-0p08/train/params.pkl"

if str(EXP_DIR) not in sys.path:
    sys.path.insert(0, str(EXP_DIR))

from g1_contact_aware_reference_env import ContactAwareReferenceSquat  # noqa: E402


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EXP80 = load_module("exp80_corridor_runner", EXP80_RUNNER)
VISIBLE_GATE = EXP80.VISIBLE_GATE


def default_source() -> Path:
    return EXP105_PARAMS if EXP105_PARAMS.exists() else EXP103_PARAMS


def make_env(
    target_drop: float,
    support_floor: float,
    slip_limit: float,
    lookahead_s: float,
    anticipatory_action_mix: float,
    contact_action_scale: float,
) -> ContactAwareReferenceSquat:
    return ContactAwareReferenceSquat(
        reference_drop=target_drop,
        target_knee_delta=0.64,
        target_hip_delta=0.38,
        support_floor=support_floor,
        slip_limit=slip_limit,
        descend_s=3.0,
        hold_s=0.35,
        return_s=1.8,
        lookahead_s=lookahead_s,
        anticipatory_action_mix=anticipatory_action_mix,
        contact_action_scale=contact_action_scale,
        config_overrides={"impl": "jax"},
    )


def ppo_config(timesteps: int):
    cfg = EXP80.ppo_config(timesteps)
    cfg.learning_rate = 3.0e-6
    cfg.num_evals = 3
    return cfg


def layer_shapes(params: Any) -> dict[str, dict[str, list[int]]]:
    return {
        name: {key: list(value.shape) for key, value in layer.items()}
        for name, layer in params[1]["params"].items()
    }


def compatibility(source: Path, env: ContactAwareReferenceSquat) -> dict[str, Any]:
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


def rollout_smoke(env: ContactAwareReferenceSquat, steps: int = 20) -> dict[str, Any]:
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
            "future_fraction": float(state.metrics["future_reference_fraction"]),
            "contact_health": float(state.metrics["contact_health"]),
            "done": float(state.done),
        })
    return {
        "rollout_steps": steps,
        "reward_first": rows[0]["reward"],
        "reward_last": rows[-1]["reward"],
        "future_fraction_last": rows[-1]["future_fraction"],
        "contact_health_min": min(row["contact_health"] for row in rows),
        "support_margin_min": min(row["support"] for row in rows),
        "foot_slip_max": max(row["slip"] for row in rows),
        "done_any": any(row["done"] > 0 for row in rows),
    }


def train(source: Path, env: ContactAwareReferenceSquat, timesteps: int, out_dir: Path, seed: int) -> dict[str, Any]:
    eval_env = make_env(
        env._reference_drop,
        env._support_floor,
        env._slip_limit,
        env._lookahead_steps * env.dt,
        env._anticipatory_action_mix,
        env._contact_action_scale,
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
    train_dir = out_dir / "train"
    train_dir.mkdir(parents=True, exist_ok=True)
    params_path = train_dir / "params.pkl"
    with params_path.open("wb") as f:
        pickle.dump(learned_params, f)
    rewards_path = train_dir / "rewards.txt"
    rewards_path.write_text(
        "\n".join([
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


def build_policy(env: ContactAwareReferenceSquat, params_path: Path):
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


def qpos_index(model: mujoco.MjModel, joint_name: str) -> int:
    return int(model.jnt_qposadr[model.joint(joint_name).id])


def visible_gap(native: dict[str, Any]) -> dict[str, float]:
    return {
        "drop_shortfall_m": max(0.0, VISIBLE_GATE["drop_m"] - native["visible_drop"]),
        "knee_shortfall_rad": max(0.0, VISIBLE_GATE["knee_delta_rad"] - native["max_knee_delta_rad"]),
        "hip_shortfall_rad": max(0.0, VISIBLE_GATE["hip_delta_rad"] - native["max_hip_pitch_delta_rad"]),
        "contact_shortfall": max(0.0, VISIBLE_GATE["foot_contact_ratio"] - native["foot_contact_ratio"]),
        "slip_excess_m": max(0.0, native["foot_slip_distance"] - VISIBLE_GATE["foot_slip_m"]),
    }


def native_eval(env: ContactAwareReferenceSquat, params_path: Path, seconds: float, out_dir: Path) -> dict[str, Any]:
    policy = build_policy(env, params_path)
    model = env.mj_model
    data = mujoco.MjData(model)
    key = model.keyframe("knees_bent")
    data.qpos[:] = key.qpos
    default_pose = key.qpos[7:].astype(np.float32).copy()
    data.ctrl[:] = default_pose
    mujoco.mj_forward(model, data)

    gyro_adr = EXP80.EXP28.sensor_adr(model, "gyro_pelvis")
    linvel_adr = EXP80.EXP28.sensor_adr(model, "local_linvel_pelvis")
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
        support = EXP80.EXP37.support_metrics(model, data, foot_geom_ids)
        min_support_margin = min(min_support_margin, support["support_margin"])
        if support["support_margin"] < env._support_floor and first_support_breach_at is None:
            first_support_breach_at = round(t, 3)
        foot_slip = float(np.max(np.linalg.norm(data.site_xpos[foot_site_ids, :2] - initial_foot_xy, axis=1)))
        max_foot_slip = max(max_foot_slip, foot_slip)
        if foot_slip > env._slip_limit and first_slip_breach_at is None:
            first_slip_breach_at = round(t, 3)
        max_joint_violation = max(max_joint_violation, EXP80.EXP28.joint_limit_violation(model, data))
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
                "up_z": up_z,
                "action_norm": float(np.linalg.norm(action_np)),
            })

    native = {
        "start_height": start_height,
        "min_height": min_height,
        "visible_drop": start_height - min_height,
        "first_visible_at": first_visible_at,
        "max_knee_delta_rad": max_knee_delta,
        "max_hip_pitch_delta_rad": max_hip_delta,
        "fell_at": fell_at,
        "final_height": final_height,
        "return_to_stand": final_height >= 0.74,
        "foot_contact_ratio": both_feet_contact_count / max(1, total_steps),
        "foot_slip_distance": max_foot_slip,
        "min_support_margin": min_support_margin,
        "first_support_breach_at": first_support_breach_at,
        "first_slip_breach_at": first_slip_breach_at,
        "max_joint_limit_violation": max_joint_violation,
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
    native["visible_gap"] = visible_gap(native)
    if native["pass_visible_gate"]:
        native["verdict"] = "PASS_VISIBLE_8CM_GATE"
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


def write_summary(result: dict[str, Any], out_dir: Path) -> None:
    native = result["native"]
    train_result = result.get("train", {})
    fell = "never" if native["fell_at"] is None else f"{native['fell_at']:.2f}s"
    lines = [
        "# G1 Contact-Aware Reference Retrain Summary",
        "",
        "| Verdict | Timesteps | Train min | Drop | Knee | Hip | Fell at | Final h | Contact | Slip | Support min |",
        "|---|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|",
        (
            f"| {native['verdict']} | {train_result.get('timesteps', 0)} | "
            f"{train_result.get('train_min', 0.0):.2f} | {native['visible_drop']:.4f}m | "
            f"{native['max_knee_delta_rad']:.3f} | {native['max_hip_pitch_delta_rad']:.3f} | "
            f"{fell} | {native['final_height']:.4f}m | {native['foot_contact_ratio']:.2f} | "
            f"{native['foot_slip_distance']:.3f}m | {native['min_support_margin']:.4f}m |"
        ),
        "",
        f"Visible gap: {json.dumps(native['visible_gap'], ensure_ascii=False)}",
        "Browser replay is attempted only after native visible gate passes.",
    ]
    (out_dir / "contact-aware-reference-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_readme(result: dict[str, Any]) -> None:
    native = result["native"]
    train_result = result.get("train", {})
    fell = "never" if native["fell_at"] is None else f"{native['fell_at']:.2f}s"
    readme = f"""# 111-g1-contact-aware-reference-retrain — G1 contact-aware reference retrain

> `experiments/111-g1-contact-aware-reference-retrain/README.md` — exp105 future-reference tracker를 contact/slip/support-aware reward로 restored PPO 재학습해 M19 native visible gate를 다시 평가한다.

## 1. 가설 (Hypothesis)

Exp103/105는 reference tracking signal을 넣으면 knee/hip pose에는 접근하지만 both-foot contact와 slip이 무너졌다. 최근 humanoid motion tracking work처럼 reference tracker를 유지하되 contact/support/slip reward와 contact-aware action prior를 강화하면, shallow retreat나 foot slip 없이 exp29 visible gate에 가까워질 수 있다.

## 2. 방법 (Method)

### 셋업
- 모델: local MuJoCo G1 + `ContactAwareReferenceSquat`.
- 초기 checkpoint: `{result['source_params']}`.
- 학습: restored PPO `{train_result.get('timesteps', 0)}` steps, lookahead `{result['lookahead_s']:.2f}s`, contact action scale `{result['contact_action_scale']:.2f}`.
- 판정: native exp29 visible gate가 통과할 때만 browser replay를 시도한다.

### 웹 근거
- UniTracker는 Unitree G1에서 whole-body motion tracker를 sim/real로 검증한다. 접근일: 2026-06-18. https://arxiv.org/html/2507.07356v3
- Whole-body humanoid locomotion work는 reference motion tracker + closed-loop fine-tuning이 reward shaping 단독보다 유리하다고 설명한다. 접근일: 2026-06-18. https://arxiv.org/html/2604.17335v1
- Strict contact-force tracking은 floating-base humanoid에서 contact force/friction constraints가 motion tracking의 핵심 제약임을 보인다. 접근일: 2026-06-18. https://la.disneyresearch.com/wp-content/uploads/PROJECT_Humanoids-mocap_IEEE-RAS-ICHR-2013_PAPER1.pdf
- Squat motion literature frames squatting as CoM/ZMP/foot-force constrained whole-body coordination. 접근일: 2026-06-18. https://pmc.ncbi.nlm.nih.gov/articles/PMC11769464/

## 3. 결과 (Results)

### 데이터
| Run | Verdict | Timesteps | Drop | Knee | Hip | Contact | Slip | Final h | Fall |
|-----|---------|---:|---:|---:|---:|---:|---:|---:|---|
| contact-aware-reference | {native['verdict']} | {train_result.get('timesteps', 0)} | {native['visible_drop']:.4f}m | {native['max_knee_delta_rad']:.3f}rad | {native['max_hip_pitch_delta_rad']:.3f}rad | {native['foot_contact_ratio']:.2f} | {native['foot_slip_distance']:.3f}m | {native['final_height']:.4f}m | {fell} |

Verdict: `{result['verdict']}`.

### 박제 위치
- `verify/result.json`
- `verify/native-eval.json`
- `verify/contact-aware-reference-summary.md`
- `verify/train/params.pkl`
- `verify/train/rewards.txt`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- Contact-aware reference retrain이 exp103/105의 foot slip/contact failure를 줄이는지 native gate로 직접 확인했다.
- 결과는 drop `{native['visible_drop']:.4f}m`, knee `{native['max_knee_delta_rad']:.3f}rad`, hip `{native['max_hip_pitch_delta_rad']:.3f}rad`, contact `{native['foot_contact_ratio']:.2f}`, slip `{native['foot_slip_distance']:.3f}m`이다.
- native gate가 PASS하지 않으면 다음은 reward 재가중이 아니라 WBC/MPC-in-loop tracker 또는 더 긴 motion-tracking training이다.

### 가설은 통과했나?
- [{'x' if native['pass_visible_gate'] else ' '}] PASS — native exp29 visible gate를 통과했다.
- [{' ' if native['pass_visible_gate'] else 'x'}] FAIL — contact-aware reference retrain만으로 native exp29 visible gate를 닫지 못했다.

### 정의에 반영
- M19는 native+browser replay가 둘 다 통과해야만 닫힌다.
"""
    (EXP_DIR / "README.md").write_text(readme, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=None)
    parser.add_argument("--timesteps", type=int, default=20_000)
    parser.add_argument("--target-drop", type=float, default=0.090)
    parser.add_argument("--support-floor", type=float, default=0.000)
    parser.add_argument("--slip-limit", type=float, default=0.055)
    parser.add_argument("--lookahead-s", type=float, default=0.55)
    parser.add_argument("--anticipatory-action-mix", type=float, default=0.35)
    parser.add_argument("--contact-action-scale", type=float, default=0.55)
    parser.add_argument("--seconds", type=float, default=6.0)
    parser.add_argument("--seed", type=int, default=111)
    parser.add_argument("--no-train", action="store_true")
    args = parser.parse_args()

    source = args.source or default_source()
    out_dir = VERIFY
    out_dir.mkdir(parents=True, exist_ok=True)
    env = make_env(
        args.target_drop,
        args.support_floor,
        args.slip_limit,
        args.lookahead_s,
        args.anticipatory_action_mix,
        args.contact_action_scale,
    )
    result = {
        "planning_gate": {
            "team_validation_mode": "manual-pass",
            "spec_delta": "M19 moves to a contact-aware reference-motion retrain after qfrc wrapper and dynamic ID-QP smoke failures.",
            "perspectives": {
                "product": "tests whether reference tracker retraining can produce a native-visible squat candidate",
                "architecture": "keeps exp105 network shape and adds contact/slip/support/action-smoothness rewards in the env",
                "security": "local MuJoCo/JAX run only; no credentials",
                "qa": "compatibility smoke, rollout smoke, restored PPO train, native exp29 visible gate",
                "skeptic": "short retrain may retreat to shallow motion; a true WBC/MPC-in-loop controller may still be needed",
            },
            "dod": [
                "contact-aware env initializes with source checkpoint shape compatibility",
                "restored PPO emits params and rewards",
                "native exp29 visible gate is audited and browser replay flag is explicit",
            ],
        },
        "web_sources": [
            {"url": "https://arxiv.org/html/2507.07356v3", "accessed": "2026-06-18"},
            {"url": "https://arxiv.org/html/2604.17335v1", "accessed": "2026-06-18"},
            {"url": "https://la.disneyresearch.com/wp-content/uploads/PROJECT_Humanoids-mocap_IEEE-RAS-ICHR-2013_PAPER1.pdf", "accessed": "2026-06-18"},
            {"url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC11769464/", "accessed": "2026-06-18"},
        ],
        "visible_gate": VISIBLE_GATE,
        "target_drop": args.target_drop,
        "support_floor": args.support_floor,
        "slip_limit": args.slip_limit,
        "lookahead_s": args.lookahead_s,
        "anticipatory_action_mix": args.anticipatory_action_mix,
        "contact_action_scale": args.contact_action_scale,
        "source_params": str(source),
        "compatibility": compatibility(source, env),
        "rollout": rollout_smoke(env),
    }
    if not result["compatibility"]["policy_shape_match"]:
        raise SystemExit("source and target policy shapes do not match")
    if args.no_train:
        params_path = source
    else:
        result["train"] = train(source, env, args.timesteps, out_dir, args.seed)
        params_path = out_dir / "train" / "params.pkl"
    result["native"] = native_eval(env, params_path, args.seconds, out_dir)
    result["verdict"] = result["native"]["verdict"]
    result["browser_replay_attempted"] = bool(result["native"]["pass_visible_gate"])
    write_summary(result, out_dir)
    (out_dir / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    write_readme(result)
    print(result["verdict"], json.dumps({
        "drop": result["native"]["visible_drop"],
        "knee": result["native"]["max_knee_delta_rad"],
        "hip": result["native"]["max_hip_pitch_delta_rad"],
        "contact": result["native"]["foot_contact_ratio"],
        "slip": result["native"]["foot_slip_distance"],
        "fall": result["native"]["fell_at"],
        "browser_replay_attempted": result["browser_replay_attempted"],
    }, indent=2), flush=True)


if __name__ == "__main__":
    main()
