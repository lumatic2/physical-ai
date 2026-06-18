"""Longer local-scene tracker training gate for the G1 visible squat."""

from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import sys
import time
from pathlib import Path
from typing import Any


EXP_DIR = Path(__file__).resolve().parent
ROOT = EXP_DIR.parents[1]
VERIFY = EXP_DIR / "verify"
EXP111_RUNNER = ROOT / "experiments/111-g1-contact-aware-reference-retrain/run_contact_aware_reference_retrain.py"


def load_exp111():
    exp111_dir = EXP111_RUNNER.parent
    if str(exp111_dir) not in sys.path:
        sys.path.insert(0, str(exp111_dir))
    spec = importlib.util.spec_from_file_location("exp111_runner", EXP111_RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {EXP111_RUNNER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EXP111 = load_exp111()
VISIBLE_GATE = EXP111.VISIBLE_GATE


WEB_SOURCES = [
    {
        "url": "https://github.com/HybridRobotics/whole_body_tracking",
        "accessed": "2026-06-18",
        "claim": "Whole-body tracking stacks expect retargeted generalized-coordinate reference motions and training data registry, not a one-off joint target wrapper.",
    },
    {
        "url": "https://arxiv.org/html/2507.07356v3",
        "accessed": "2026-06-18",
        "claim": "UniTracker reports Unitree G1 29-DoF tracking of thousands of motions through a unified whole-body motion tracker.",
    },
    {
        "url": "https://arxiv.org/html/2604.17335v1",
        "accessed": "2026-06-18",
        "claim": "Recent G1 whole-body locomotion systems combine motion generation, motion tracking, and fine-tuning rather than direct kinematic playback.",
    },
    {
        "url": "https://nvlabs.github.io/GR00T-WholeBodyControl/references/decoupled_wbc.html",
        "accessed": "2026-06-18",
        "claim": "GR00T whole-body control documents a G1-oriented stack where whole-body control is a reusable system layer.",
    },
    {
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC11769464/",
        "accessed": "2026-06-18",
        "claim": "Humanoid squat control is treated as coordinated CoM, ZMP, foot force, and whole-body control.",
    },
]


def make_env(variant: dict[str, Any]):
    return EXP111.make_env(
        variant["target_drop"],
        variant["support_floor"],
        variant["slip_limit"],
        variant["lookahead_s"],
        variant["anticipatory_action_mix"],
        variant["contact_action_scale"],
    )


def compact_native(native: dict[str, Any]) -> dict[str, Any]:
    return {
        "verdict": native["verdict"],
        "visible_drop": native["visible_drop"],
        "max_knee_delta_rad": native["max_knee_delta_rad"],
        "max_hip_pitch_delta_rad": native["max_hip_pitch_delta_rad"],
        "foot_contact_ratio": native["foot_contact_ratio"],
        "foot_slip_distance": native["foot_slip_distance"],
        "final_height": native["final_height"],
        "fell_at": native["fell_at"],
        "return_to_stand": native["return_to_stand"],
        "pass_visible_gate": native["pass_visible_gate"],
        "visible_gap": native["visible_gap"],
    }


def score(run: dict[str, Any]) -> float:
    native = run.get("native", {})
    if not native:
        return 1e9
    gap = native["visible_gap"]
    return float(
        520.0 * gap["drop_shortfall_m"] / VISIBLE_GATE["drop_m"]
        + 360.0 * gap["knee_shortfall_rad"] / VISIBLE_GATE["knee_delta_rad"]
        + 320.0 * gap["hip_shortfall_rad"] / VISIBLE_GATE["hip_delta_rad"]
        + 210.0 * gap["contact_shortfall"]
        + 260.0 * gap["slip_excess_m"] / max(VISIBLE_GATE["foot_slip_m"], 1e-6)
        + (420.0 if native["fell_at"] is not None else 0.0)
        + (220.0 if not native["return_to_stand"] else 0.0)
    )


def reward_delta(train: dict[str, Any] | None) -> dict[str, Any] | None:
    if not train or not train.get("reward_points"):
        return None
    points = train["reward_points"]
    return {
        "first_step": points[0][0],
        "first_reward": points[0][1],
        "last_step": points[-1][0],
        "last_reward": points[-1][1],
        "delta": points[-1][1] - points[0][1],
    }


def run_variant(variant: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    out_dir = VERIFY / variant["name"]
    params_path = out_dir / "train" / "params.pkl"
    if out_dir.exists() and not (args.reuse_train and params_path.exists()):
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    env = make_env(variant)
    source = Path(variant.get("source") or EXP111.default_source())
    run: dict[str, Any] = {
        "name": variant["name"],
        "variant": variant,
        "source_params": str(source),
        "compatibility": EXP111.compatibility(source, env),
        "rollout_smoke": EXP111.rollout_smoke(env, steps=args.rollout_steps),
    }
    if not run["compatibility"]["policy_shape_match"]:
        run["verdict"] = "INCOMPATIBLE_SOURCE_SHAPE"
        return run

    if variant["train"]:
        if args.reuse_train and params_path.exists():
            run["train"] = {
                "timesteps": variant["timesteps"],
                "seed": variant["seed"],
                "source_params": str(source),
                "params_path": str(params_path.relative_to(EXP_DIR)),
                "reused_existing_train_artifact": True,
            }
        else:
            start = time.monotonic()
            try:
                run["train"] = EXP111.train(source, env, variant["timesteps"], out_dir, variant["seed"])
            except ValueError as exc:
                # exp111 can raise after writing params because its relative path assumes exp111's folder.
                if not params_path.exists():
                    raise
                rewards_path = out_dir / "train" / "rewards.txt"
                run["train"] = {
                    "timesteps": variant["timesteps"],
                    "seed": variant["seed"],
                    "source_params": str(source),
                    "params_path": str(params_path.relative_to(EXP_DIR)),
                    "rewards_path": str(rewards_path.relative_to(EXP_DIR)) if rewards_path.exists() else None,
                    "train_min": (time.monotonic() - start) / 60.0,
                    "helper_relative_path_error": str(exc),
                }
        eval_params = params_path
    else:
        eval_params = source

    native = EXP111.native_eval(env, eval_params, args.seconds, out_dir)
    run["native"] = compact_native(native)
    run["verdict"] = native["verdict"]
    run["score"] = score(run)
    run["reward_delta"] = reward_delta(run.get("train"))
    run["browser_replay_attempted"] = bool(native["pass_visible_gate"])
    return run


def build_result(args: argparse.Namespace) -> dict[str, Any]:
    variants = [
        {
            "name": "source-exp105-no-train",
            "train": False,
            "target_drop": 0.09,
            "support_floor": 0.0,
            "slip_limit": 0.055,
            "lookahead_s": 0.55,
            "anticipatory_action_mix": 0.35,
            "contact_action_scale": 0.55,
            "timesteps": 0,
            "seed": 1180,
        },
        {
            "name": "longer-local-tracker-contact-tight",
            "train": True,
            "target_drop": 0.09,
            "support_floor": 0.0,
            "slip_limit": 0.050,
            "lookahead_s": 0.70,
            "anticipatory_action_mix": 0.50,
            "contact_action_scale": 0.80,
            "timesteps": args.timesteps,
            "seed": 1181,
        },
    ]
    result: dict[str, Any] = {
        "planning_gate": {
            "team_validation_mode": "manual-pass",
            "spec_delta": "M19 tests whether longer local-scene tracker training has a measurable native-gate improvement after exp116/117 failures.",
            "perspectives": {
                "product": "checks whether the next showable route should be tracker training rather than another qfrc controller smoke",
                "architecture": "reuses checkpoint-compatible future-reference tracker env and native exp29 gate",
                "security": "local MuJoCo/JAX training only; no credentials",
                "qa": "source baseline, longer restored PPO train, native gate, browser replay flag, raw params and native JSON",
                "skeptic": "20k steps may still be too short to represent true long training, but it should reveal whether reward optimization moves the native metric in the right direction",
            },
            "dod": [
                "source baseline native gate",
                "longer restored PPO native gate",
                "state whether browser replay was attempted",
            ],
        },
        "web_sources": WEB_SOURCES,
        "visible_gate": VISIBLE_GATE,
        "evaluation_seconds": args.seconds,
        "runs": [],
    }
    for variant in variants:
        print(f"running {variant['name']}", flush=True)
        result["runs"].append(run_variant(variant, args))
    passed = [run for run in result["runs"] if run.get("native", {}).get("pass_visible_gate")]
    result["best"] = min(result["runs"], key=lambda run: run.get("score", 1e9))
    source_run = next(run for run in result["runs"] if run["name"] == "source-exp105-no-train")
    trained_run = next(run for run in result["runs"] if run["name"] != "source-exp105-no-train")
    result["native_delta_vs_source"] = {
        "drop_delta_m": trained_run["native"]["visible_drop"] - source_run["native"]["visible_drop"],
        "knee_delta_rad": trained_run["native"]["max_knee_delta_rad"] - source_run["native"]["max_knee_delta_rad"],
        "hip_delta_rad": trained_run["native"]["max_hip_pitch_delta_rad"] - source_run["native"]["max_hip_pitch_delta_rad"],
        "contact_delta": trained_run["native"]["foot_contact_ratio"] - source_run["native"]["foot_contact_ratio"],
        "slip_delta_m": trained_run["native"]["foot_slip_distance"] - source_run["native"]["foot_slip_distance"],
        "score_delta": trained_run["score"] - source_run["score"],
    }
    result["verdict"] = "PASS_VISIBLE_8CM_GATE" if passed else "FAIL_LONGER_LOCAL_TRACKER_TRAINING_GATE"
    result["browser_replay_attempted"] = bool(passed)
    result["next_action"] = (
        "attempt_browser_replay"
        if passed
        else "stop_short_local_tracker_sweeps_and_move_to_real_wbc_stack_or_substantially_longer_tracker_training"
    )
    return result


def write_summary(result: dict[str, Any]) -> None:
    lines = [
        "# G1 Longer Local Tracker Training Gate",
        "",
        f"Verdict: `{result['verdict']}`",
        f"Next action: `{result['next_action']}`",
        "",
        "| Run | Score | Verdict | Drop | Knee | Hip | Contact | Slip | Final h | Fall |",
        "|---|---:|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for run in result["runs"]:
        native = run["native"]
        fall = "never" if native["fell_at"] is None else f"{native['fell_at']:.2f}s"
        lines.append(
            f"| {run['name']} | {run['score']:.1f} | {run['verdict']} | "
            f"{native['visible_drop']:.4f}m | {native['max_knee_delta_rad']:.3f} | "
            f"{native['max_hip_pitch_delta_rad']:.3f} | {native['foot_contact_ratio']:.2f} | "
            f"{native['foot_slip_distance']:.3f}m | {native['final_height']:.4f}m | {fall} |"
        )
    lines.extend([
        "",
        f"Delta trained-vs-source: `{json.dumps(result['native_delta_vs_source'], ensure_ascii=False)}`",
        f"Best run: `{result['best']['name']}` -> `{result['best']['verdict']}`",
        "Browser replay is attempted only after native exp29 visible gate passes.",
    ])
    (VERIFY / "longer-local-tracker-training-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_readme(result: dict[str, Any]) -> None:
    rows = []
    for run in result["runs"]:
        native = run["native"]
        fall = "never" if native["fell_at"] is None else f"{native['fell_at']:.2f}s"
        rows.append(
            f"| {run['name']} | {run['verdict']} | {native['visible_drop']:.4f}m | "
            f"{native['max_knee_delta_rad']:.3f} | {native['max_hip_pitch_delta_rad']:.3f} | "
            f"{native['foot_contact_ratio']:.2f} | {native['foot_slip_distance']:.3f}m | "
            f"{native['final_height']:.4f}m | {fall} |"
        )
    best = result["best"]
    best_native = best["native"]
    delta = result["native_delta_vs_source"]
    readme = f"""# 118-g1-longer-local-tracker-training-gate — G1 longer local tracker training gate

## 1. 가설 (Hypothesis)

Exp116의 512-step local retrain은 source 대비 drop/contact가 거의 변하지 않았고, exp117의 qfrc-applied full-order formulation smoke는 1.40~1.46초 fall로 붕괴했다. 같은 local scene에서 restored PPO를 20k-step 수준으로 늘리면, shallow attractor를 벗어나 M19 native visible gate에 의미 있게 가까워질 수 있다.

## 2. 방법 (Method)

- 기반: exp111 `ContactAwareReferenceSquat`, exp105 future-reference tracker checkpoint, exp29 native visible gate.
- 비교: source no-train baseline vs longer local tracker retrain.
- 학습 variant: target_drop 9cm, lookahead 0.70s, anticipatory action mix 0.50, contact action scale 0.80, slip limit 5cm.
- 판정: native gate가 PASS할 때만 browser replay를 시도한다.

### 웹 근거

- HybridRobotics whole-body tracking stack은 retargeted generalized-coordinate reference motion과 training registry를 전제로 한다. 접근일: 2026-06-18. https://github.com/HybridRobotics/whole_body_tracking
- UniTracker는 Unitree G1 29-DoF에서 8,100개 이상 motion sequence tracking을 목표로 한 unified tracker 접근을 제시한다. 접근일: 2026-06-18. https://arxiv.org/html/2507.07356v3
- Whole-body humanoid locomotion on Unitree G1은 motion generation, tracker, fine-tuning 조합을 사용한다. 접근일: 2026-06-18. https://arxiv.org/html/2604.17335v1
- GR00T WholeBodyControl 문서는 Unitree G1 중심의 재사용 가능한 WBC/teleoperation/data exporter stack을 전제로 한다. 접근일: 2026-06-18. https://nvlabs.github.io/GR00T-WholeBodyControl/references/decoupled_wbc.html
- Humanoid squat TP-MPC/WBC 연구는 squat를 CoM/ZMP/foot force/whole-body coordination 문제로 다룬다. 접근일: 2026-06-18. https://pmc.ncbi.nlm.nih.gov/articles/PMC11769464/

## 3. 결과 (Results)

| Run | Verdict | Drop | Knee | Hip | Contact | Slip | Final h | Fall |
|---|---|---:|---:|---:|---:|---:|---:|---|
{chr(10).join(rows)}

Verdict: `{result['verdict']}`.
Best run: `{best['name']}` with drop `{best_native['visible_drop']:.4f}m`, knee `{best_native['max_knee_delta_rad']:.3f}`, hip `{best_native['max_hip_pitch_delta_rad']:.3f}`.

Trained-vs-source delta:
- drop `{delta['drop_delta_m']:.4f}m`
- knee `{delta['knee_delta_rad']:.3f}rad`
- hip `{delta['hip_delta_rad']:.3f}rad`
- contact `{delta['contact_delta']:.3f}`
- slip `{delta['slip_delta_m']:.3f}m`
- score `{delta['score_delta']:.1f}`

### 박제 위치
- `verify/result.json`
- `verify/longer-local-tracker-training-summary.md`
- `verify/<run>/native-eval.json`
- `verify/<trained-run>/train/params.pkl`
- `verify/<trained-run>/train/rewards.txt`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- Longer local tracker training gate verdict는 `{result['verdict']}`이다.
- Browser replay attempted: `{result['browser_replay_attempted']}`.
- 20k-step급 restored PPO가 native gate를 닫지 못하면, 같은 짧은 local tracker sweep을 반복하는 것은 M19 완료와 정렬이 약하다.
- 이 실험은 “장기 학습 전체”가 아니라 next-route gate다. 실패 시 다음은 실제 WBC stack 통합 또는 훨씬 긴 tracker training budget으로 가야 한다.

### 가설은 통과했나?
- [{'x' if result['verdict'] == 'PASS_VISIBLE_8CM_GATE' else ' '}] PASS — native exp29 visible gate를 통과했다.
- [{' ' if result['verdict'] == 'PASS_VISIBLE_8CM_GATE' else 'x'}] FAIL — longer local tracker training gate만으로 native visible gate를 닫지 못했다.

### 정의에 반영
- M19 완료 기준은 그대로 native exp29 visible gate + browser replay다.
"""
    (EXP_DIR / "README.md").write_text(readme, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timesteps", type=int, default=20_000)
    parser.add_argument("--seconds", type=float, default=6.0)
    parser.add_argument("--rollout-steps", type=int, default=20)
    parser.add_argument("--reuse-train", action="store_true")
    args = parser.parse_args()
    VERIFY.mkdir(parents=True, exist_ok=True)
    result = build_result(args)
    (VERIFY / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    write_summary(result)
    write_readme(result)
    print(json.dumps({
        "verdict": result["verdict"],
        "best": result["best"]["name"],
        "delta": result["native_delta_vs_source"],
        "browser_replay_attempted": result["browser_replay_attempted"],
        "next_action": result["next_action"],
    }, indent=2), flush=True)


if __name__ == "__main__":
    main()
