"""Evaluate contact-aware action wrappers around the exp103 G1 squat policy."""

from __future__ import annotations

import argparse
import importlib.util
import json
import pickle
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import jax
import jax.numpy as jp
import mujoco
import numpy as np
from brax.training.acme import running_statistics
from brax.training.agents.ppo import networks as ppo_networks


EXP_DIR = Path(__file__).resolve().parent
ROOT = EXP_DIR.parents[1]
VERIFY = EXP_DIR / "verify"
EXP80 = ROOT / "experiments/80-g1-corridor-curriculum-training"
EXP80_RUNNER = EXP80 / "run_corridor_curriculum.py"
EXP103 = ROOT / "experiments/103-g1-explicit-reference-command-tracker"
EXP103_PARAMS = EXP103 / "verify/target-0p090-slip-0p08/train/params.pkl"

if str(EXP80) not in sys.path:
    sys.path.insert(0, str(EXP80))
if str(EXP103) not in sys.path:
    sys.path.insert(0, str(EXP103))

from g1_explicit_reference_command_env import ExplicitReferenceCommandSquat  # noqa: E402


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EXP80_MODULE = load_module("exp80_corridor_runner", EXP80_RUNNER)
VISIBLE_GATE = EXP80_MODULE.VISIBLE_GATE


@dataclass(frozen=True)
class WrapperVariant:
    name: str
    support_floor: float = -0.005
    slip_start: float = 0.04
    min_scale: float = 0.10
    ankle_scale: float = 1.0
    return_on_breach: bool = False
    contact_scale: float = 1.0
    early_guard_s: float = 0.0


VARIANTS = [
    WrapperVariant("direct-exp103", min_scale=1.0),
    WrapperVariant("support-slip-scale", slip_start=0.025, min_scale=0.20, contact_scale=0.60),
    WrapperVariant("ankle-damped-support-slip", slip_start=0.025, min_scale=0.20, ankle_scale=0.25, contact_scale=0.60),
    WrapperVariant("early-conservative-scale", slip_start=0.015, min_scale=0.05, ankle_scale=0.20, contact_scale=0.35, early_guard_s=1.0),
    WrapperVariant("return-on-contact-breach", slip_start=0.025, min_scale=0.00, ankle_scale=0.20, contact_scale=0.35, return_on_breach=True),
]


def make_env(target_drop: float, support_floor: float, slip_limit: float) -> ExplicitReferenceCommandSquat:
    return ExplicitReferenceCommandSquat(
        reference_drop=target_drop,
        target_knee_delta=0.64,
        target_hip_delta=0.38,
        support_floor=support_floor,
        slip_limit=slip_limit,
        descend_s=3.0,
        hold_s=0.25,
        return_s=1.6,
        config_overrides={"impl": "jax"},
    )


def ppo_config(timesteps: int):
    cfg = EXP80_MODULE.ppo_config(timesteps)
    cfg.learning_rate = 4.0e-6
    cfg.num_evals = 3
    return cfg


def qpos_index(model: mujoco.MjModel, joint_name: str) -> int:
    return int(model.jnt_qposadr[model.joint(joint_name).id])


def build_policy(env: ExplicitReferenceCommandSquat, params_path: Path):
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


def visible_gap(native: dict[str, Any]) -> dict[str, float]:
    return {
        "drop_shortfall_m": max(0.0, VISIBLE_GATE["drop_m"] - native["visible_drop"]),
        "knee_shortfall_rad": max(0.0, VISIBLE_GATE["knee_delta_rad"] - native["max_knee_delta_rad"]),
        "hip_shortfall_rad": max(0.0, VISIBLE_GATE["hip_delta_rad"] - native["max_hip_pitch_delta_rad"]),
        "contact_shortfall": max(0.0, VISIBLE_GATE["foot_contact_ratio"] - native["foot_contact_ratio"]),
        "slip_excess_m": max(0.0, native["foot_slip_distance"] - VISIBLE_GATE["foot_slip_m"]),
    }


def wrapper_scale(variant: WrapperVariant, support_margin: float, foot_slip: float, both_feet: bool, t: float) -> tuple[float, bool]:
    scale = 1.0
    if foot_slip > variant.slip_start:
        slip_span = max(1e-6, VISIBLE_GATE["foot_slip_m"] - variant.slip_start)
        slip_scale = 1.0 - min(1.0, (foot_slip - variant.slip_start) / slip_span)
        scale = min(scale, max(variant.min_scale, slip_scale))
    if support_margin < variant.support_floor:
        scale = min(scale, variant.min_scale)
    if not both_feet:
        scale = min(scale, variant.contact_scale)
    if variant.early_guard_s > 0.0 and t < variant.early_guard_s:
        scale = min(scale, 0.55)
    breached = (
        support_margin < variant.support_floor
        or foot_slip > VISIBLE_GATE["foot_slip_m"]
        or not both_feet
    )
    return scale, breached


def apply_wrapper(
    raw_action: np.ndarray,
    default_pose: np.ndarray,
    model: mujoco.MjModel,
    variant: WrapperVariant,
    scale: float,
    breached: bool,
) -> np.ndarray:
    action = raw_action.copy()
    if variant.ankle_scale != 1.0:
        action[[4, 5, 10, 11]] *= variant.ankle_scale
    target = default_pose + action * float(0.5)
    if variant.return_on_breach and breached:
        target = default_pose + scale * (target - default_pose)
    else:
        target = default_pose + scale * (target - default_pose)
    return np.clip(target, model.actuator_ctrlrange[:, 0], model.actuator_ctrlrange[:, 1])


def native_eval(params_path: Path, variant: WrapperVariant, target_drop: float, support_floor: float, slip_limit: float, seconds: float, out_dir: Path) -> dict:
    env = make_env(target_drop, support_floor, slip_limit)
    policy = build_policy(env, params_path)
    model = env.mj_model
    data = mujoco.MjData(model)
    key = model.keyframe("knees_bent")
    data.qpos[:] = key.qpos
    default_pose = key.qpos[7:].astype(np.float32).copy()
    data.ctrl[:] = default_pose
    mujoco.mj_forward(model, data)

    gyro_adr = EXP80_MODULE.EXP28.sensor_adr(model, "gyro_pelvis")
    linvel_adr = EXP80_MODULE.EXP28.sensor_adr(model, "local_linvel_pelvis")
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
    min_wrapper_scale = 1.0
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

        contacts = [
            float(data.sensordata[model.sensor_adr[sensor_id]]) > 0
            for sensor_id in foot_contact_sensor_ids
        ]
        both_feet = all(contacts)
        support = EXP80_MODULE.EXP37.support_metrics(model, data, foot_geom_ids)
        foot_slip = float(np.max(np.linalg.norm(data.site_xpos[foot_site_ids, :2] - initial_foot_xy, axis=1)))
        scale, breached = wrapper_scale(variant, support["support_margin"], foot_slip, both_feet, t)
        min_wrapper_scale = min(min_wrapper_scale, scale)
        data.ctrl[:] = apply_wrapper(action_np, default_pose, model, variant, scale, breached)
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
        contacts_after = [
            float(data.sensordata[model.sensor_adr[sensor_id]]) > 0
            for sensor_id in foot_contact_sensor_ids
        ]
        both_feet_after = all(contacts_after)
        both_feet_contact_count += int(both_feet_after)
        support_after = EXP80_MODULE.EXP37.support_metrics(model, data, foot_geom_ids)
        min_support_margin = min(min_support_margin, support_after["support_margin"])
        if support_after["support_margin"] < support_floor and first_support_breach_at is None:
            first_support_breach_at = round(t, 3)
        foot_slip_after = float(np.max(np.linalg.norm(data.site_xpos[foot_site_ids, :2] - initial_foot_xy, axis=1)))
        max_foot_slip = max(max_foot_slip, foot_slip_after)
        if foot_slip_after > slip_limit and first_slip_breach_at is None:
            first_slip_breach_at = round(t, 3)
        max_joint_violation = max(max_joint_violation, EXP80_MODULE.EXP28.joint_limit_violation(model, data))
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
                "support_margin": support_after["support_margin"],
                "both_feet_contact": both_feet_after,
                "foot_slip_distance": foot_slip_after,
                "up_z": up_z,
                "action_norm": float(np.linalg.norm(action_np)),
                "wrapper_scale": scale,
            })

    native = {
        "variant": variant.__dict__,
        "params_path": str(params_path),
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
        "min_wrapper_scale": min_wrapper_scale,
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
    (out_dir / f"{variant.name}.json").write_text(json.dumps(native, indent=2), encoding="utf-8")
    return native


def write_summary(result: dict, out_dir: Path) -> None:
    rows = [
        "| Variant | Verdict | Drop | Knee | Hip | Contact | Slip | Return | Fall | Min scale |",
        "|---|---|---:|---:|---:|---:|---:|---|---|---:|",
    ]
    for item in result["variants"]:
        fall = "never" if item["fell_at"] is None else f"{item['fell_at']:.2f}s"
        rows.append(
            f"| {item['variant']['name']} | {item['verdict']} | {item['visible_drop']:.4f}m | "
            f"{item['max_knee_delta_rad']:.3f} | {item['max_hip_pitch_delta_rad']:.3f} | "
            f"{item['foot_contact_ratio']:.2f} | {item['foot_slip_distance']:.3f}m | "
            f"{item['return_to_stand']} | {fall} | {item['min_wrapper_scale']:.2f} |"
        )
    lines = [
        "# G1 Contact-Aware Reference Action Wrapper Summary",
        "",
        *rows,
        "",
        f"Best variant by score: `{result['best']['variant']['name']}` -> `{result['best']['verdict']}`.",
        f"Overall verdict: `{result['verdict']}`.",
    ]
    (out_dir / "contact-aware-wrapper-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def update_readme(result: dict) -> None:
    best = result["best"]
    rows = []
    for item in result["variants"]:
        fall = "never" if item["fell_at"] is None else f"{item['fell_at']:.2f}s"
        rows.append(
            f"| {item['variant']['name']} | {item['verdict']} | {item['visible_drop']:.4f}m | "
            f"{item['max_knee_delta_rad']:.3f} | {item['max_hip_pitch_delta_rad']:.3f} | "
            f"{item['foot_contact_ratio']:.2f} | {item['foot_slip_distance']:.3f}m | "
            f"{item['return_to_stand']} | {fall} |"
        )
    readme = f"""# 104-g1-contact-aware-reference-action-wrapper — G1 접촉 인지 reference action wrapper

> `experiments/104-g1-contact-aware-reference-action-wrapper/README.md` — exp103 explicit-reference 정책을 재학습 없이 native action wrapper로 감싸 접촉/슬립 병목을 분리한다.

## 1. 가설 (Hypothesis)

G1은 관절 범위와 무릎 토크 스펙상 보이는 squat pose 자체는 가능한 편이지만, exp103 실패는 pose command 부족보다 stance contact/slip 제약을 정책 입력과 제어 입력 사이에서 즉시 보정하지 못한 것이 원인일 수 있다.

## 2. 방법 (Method)

### 셋업
- 모델: local MuJoCo G1 + exp103 explicit-reference command PPO checkpoint.
- 데이터: `experiments/103-g1-explicit-reference-command-tracker/verify/target-0p090-slip-0p08/train/params.pkl`.
- 하네스 구성: exp80 native visible gate evaluator를 재사용하고, policy action을 `ctrl`로 넣기 직전에 support margin, both-feet contact, foot slip으로 scale/damp/return wrapper를 적용했다.

### 웹 근거
- Unitree 공식 G1 page는 knee range `0~165°`, hip pitch `±154°`, knee torque `90/120 N.m`를 제시한다. 접근일: 2026-06-18. https://www.unitree.com/g1/
- Disney Research의 humanoid motion tracking paper는 humanoid reference imitation의 핵심 난점을 joint torque만이 아니라 contact force와 friction constraint로 설명한다. 접근일: 2026-06-18. https://la.disneyresearch.com/publication/human-motion-tracking-control-with-strict-contact-force-constraints-for-floating-base-humanoid-robots/
- 최근 heavy-limb humanoid WBC paper는 Unitree G1류 humanoid에서 limb mass/base coupling이 balance를 흔들고, reference motion/contact force를 같이 계획해야 한다고 정리한다. 접근일: 2026-06-18. https://arxiv.org/html/2506.14278v1
- Squat-specific humanoid paper도 squat을 whole-body coordination + WBC/MPC 문제로 다룬다. 접근일: 2026-06-18. https://pmc.ncbi.nlm.nih.gov/articles/PMC11769464/

### 시나리오
- `direct-exp103`: exp103 checkpoint를 그대로 재평가한다.
- `support-slip-scale`: slip/support/contact breach가 보이면 residual action을 줄인다.
- `ankle-damped-support-slip`: 발목 residual을 같이 줄여 foot slip을 낮춘다.
- `early-conservative-scale`: early descent부터 conservative scale을 건다.
- `return-on-contact-breach`: contact/slip breach 시 default standing pose 쪽으로 돌린다.

### 측정 metric
- exp29 visible gate: pelvis drop >= 8cm, knee delta >= 0.60rad, hip delta >= 0.35rad.
- stability gate: no fall, final stand return, both-feet contact ratio >= 0.90, foot slip <= 0.08m, joint violation <= 0.05rad.

## 3. 결과 (Results)

### 데이터
| Run | Verdict | Drop | Knee | Hip | Contact | Slip | Return | Fall |
|-----|---------|---:|---:|---:|---:|---:|---|---|
{chr(10).join(rows)}

Best variant: `{best['variant']['name']}` -> `{best['verdict']}`.

### 박제 위치
- `verify/result.json`
- `verify/contact-aware-wrapper-summary.md`
- `verify/direct-exp103.json`
- `verify/support-slip-scale.json`
- `verify/ankle-damped-support-slip.json`
- `verify/early-conservative-scale.json`
- `verify/return-on-contact-breach.json`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- G1 squat feasibility 자체는 관절/토크 스펙상 부정되지 않는다. 문제는 현재 local policy/control stack이 contact force/friction constraint를 만족시키며 reference pose를 추적하지 못하는 것이다.
- Contact-aware action wrapper는 exp103의 3m급 slip 폭주를 줄일 수 있는지 보는 빠른 sanity gate지만, wrapper만으로 exp29 전체 gate를 닫지 못하면 다음은 wrapper search가 아니라 future-reference tracker 또는 WBC/contact-force planner를 policy loop에 넣어야 한다.
- 이번 best 결과는 drop `{best['visible_drop']:.4f}m`, knee `{best['max_knee_delta_rad']:.3f}rad`, hip `{best['max_hip_pitch_delta_rad']:.3f}rad`, contact `{best['foot_contact_ratio']:.2f}`, slip `{best['foot_slip_distance']:.3f}m`이다.

### 가설은 통과했나?
- [ ] PASS
- [x] FAIL — action wrapper만으로 native exp29 visible gate를 닫지 못했다.

### 정의에 반영
- M19는 계속 open이다. native gate가 실패했으므로 browser replay는 시도하지 않는다.

### 다음 실험 후보
- Future-reference observation을 넣은 tracker env로 exp103을 확장하거나, contact force/friction constraints를 명시적으로 푸는 WBC/MPC planner를 policy action 앞단에 둔다.
"""
    (EXP_DIR / "README.md").write_text(readme, encoding="utf-8")


def score(item: dict[str, Any]) -> tuple[float, float, float, float, float]:
    gap = item["visible_gap"]
    return (
        1.0 if item["fell_at"] is None else 0.0,
        -gap["slip_excess_m"],
        -gap["contact_shortfall"],
        item["visible_drop"],
        item["max_knee_delta_rad"] + item["max_hip_pitch_delta_rad"],
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--params", type=Path, default=EXP103_PARAMS)
    parser.add_argument("--target-drop", type=float, default=0.090)
    parser.add_argument("--support-floor", type=float, default=-0.005)
    parser.add_argument("--slip-limit", type=float, default=0.08)
    parser.add_argument("--seconds", type=float, default=6.0)
    args = parser.parse_args()

    if not args.params.exists():
        raise SystemExit(f"missing params: {args.params}")
    VERIFY.mkdir(parents=True, exist_ok=True)
    variants = [
        native_eval(args.params, variant, args.target_drop, args.support_floor, args.slip_limit, args.seconds, VERIFY)
        for variant in VARIANTS
    ]
    best = max(variants, key=score)
    result = {
        "planning_gate": {
            "team_validation_mode": "manual-pass",
            "spec_delta": "M19 checks whether a contact-aware control-side wrapper can rescue exp103 before larger tracker redesign.",
            "perspectives": {
                "product": "answers whether the current G1 can squat in this stack before spending time on a larger tracker",
                "architecture": "keeps exp103 policy frozen and isolates the controller/action-wrapper layer",
                "security": "local MuJoCo/JAX evaluation only; no credentials",
                "qa": "native exp29 visible gate per wrapper; browser replay only if native passes",
                "skeptic": "post-policy action scaling may reduce depth faster than it restores contact/friction feasibility",
            },
            "dod": [
                "official/research web feasibility sources recorded",
                "all wrapper variants write raw native JSON",
                "best native rollout audited against exp29 visible gate",
            ],
        },
        "web_sources": [
            {"url": "https://www.unitree.com/g1/", "accessed": "2026-06-18"},
            {"url": "https://la.disneyresearch.com/publication/human-motion-tracking-control-with-strict-contact-force-constraints-for-floating-base-humanoid-robots/", "accessed": "2026-06-18"},
            {"url": "https://arxiv.org/html/2506.14278v1", "accessed": "2026-06-18"},
            {"url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC11769464/", "accessed": "2026-06-18"},
        ],
        "visible_gate": VISIBLE_GATE,
        "params": str(args.params),
        "variants": variants,
        "best": best,
        "verdict": "PASS_VISIBLE_8CM_GATE" if best["pass_visible_gate"] else best["verdict"],
        "browser_replay_attempted": bool(best["pass_visible_gate"]),
    }
    write_summary(result, VERIFY)
    (VERIFY / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    update_readme(result)
    print(result["verdict"], json.dumps({"best": best, "browser_replay_attempted": result["browser_replay_attempted"]}, indent=2), flush=True)


if __name__ == "__main__":
    main()
