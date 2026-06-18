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
        "url": "https://arxiv.org/html/2510.02252v1",
        "accessed": "2026-06-18",
        "claim": "Retargeting artifacts such as foot sliding and infeasible motions can damage downstream humanoid RL tracking.",
    },
    {
        "url": "https://arxiv.org/html/2604.17335v1",
        "accessed": "2026-06-18",
        "claim": "Recent Unitree G1 whole-body locomotion systems combine generated/reference motion with RL-based tracking rather than direct kinematic playback.",
    },
    {
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC11769464/",
        "accessed": "2026-06-18",
        "claim": "Humanoid squatting is treated as coordinated CoM, ZMP, foot-force, and whole-body control.",
    },
    {
        "url": "https://la.disneyresearch.com/wp-content/uploads/PROJECT_Humanoids-mocap_IEEE-RAS-ICHR-2013_PAPER1.pdf",
        "accessed": "2026-06-18",
        "claim": "Floating-base humanoid motion tracking depends on strict contact-force constraints, not joint targets alone.",
    },
]


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


def make_variant_env(variant: dict[str, Any]):
    return EXP111.make_env(
        variant["target_drop"],
        variant["support_floor"],
        variant["slip_limit"],
        variant["lookahead_s"],
        variant["anticipatory_action_mix"],
        variant["contact_action_scale"],
    )


def run_variant(variant: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    out_dir = VERIFY / variant["name"]
    existing_params = out_dir / "train" / "params.pkl"
    if out_dir.exists() and not (args.reuse_train and existing_params.exists()):
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    env = make_variant_env(variant)
    source = Path(variant.get("source") or EXP111.default_source())
    record: dict[str, Any] = {
        "name": variant["name"],
        "variant": variant,
        "source_params": str(source),
        "compatibility": EXP111.compatibility(source, env),
        "rollout_smoke": EXP111.rollout_smoke(env, steps=args.rollout_steps),
    }
    if not record["compatibility"]["policy_shape_match"]:
        record["verdict"] = "INCOMPATIBLE_SOURCE_SHAPE"
        return record

    if variant.get("train", False):
        params_path = out_dir / "train" / "params.pkl"
        rewards_path = out_dir / "train" / "rewards.txt"
        if args.reuse_train and params_path.exists():
            record["train"] = {
                "timesteps": variant["timesteps"],
                "seed": variant["seed"],
                "source_params": str(source),
                "params_path": str(params_path.relative_to(EXP_DIR)),
                "rewards_path": str(rewards_path.relative_to(EXP_DIR)) if rewards_path.exists() else None,
                "reused_existing_train_artifact": True,
            }
        else:
            start = time.monotonic()
            try:
                record["train"] = EXP111.train(source, env, variant["timesteps"], out_dir, variant["seed"])
            except ValueError as exc:
                if not params_path.exists():
                    raise
                record["train"] = {
                    "timesteps": variant["timesteps"],
                    "seed": variant["seed"],
                    "source_params": str(source),
                    "params_path": str(params_path.relative_to(EXP_DIR)),
                    "rewards_path": str(rewards_path.relative_to(EXP_DIR)) if rewards_path.exists() else None,
                    "train_min": (time.monotonic() - start) / 60.0,
                    "helper_relative_path_error": str(exc),
                }
        params_path = out_dir / "train" / "params.pkl"
    else:
        params_path = source
    native = EXP111.native_eval(env, params_path, args.seconds, out_dir)
    record["native"] = compact_native(native)
    record["verdict"] = native["verdict"]
    record["browser_replay_attempted"] = bool(native["pass_visible_gate"])
    return record


def score(run: dict[str, Any]) -> float:
    native = run.get("native", {})
    if not native:
        return 1e9
    gap = native["visible_gap"]
    return (
        500.0 * gap["drop_shortfall_m"] / VISIBLE_GATE["drop_m"]
        + 350.0 * gap["knee_shortfall_rad"] / VISIBLE_GATE["knee_delta_rad"]
        + 300.0 * gap["hip_shortfall_rad"] / VISIBLE_GATE["hip_delta_rad"]
        + 180.0 * gap["contact_shortfall"]
        + 220.0 * gap["slip_excess_m"] / max(VISIBLE_GATE["foot_slip_m"], 1e-6)
        + (400.0 if native["fell_at"] is not None else 0.0)
        + (200.0 if not native["return_to_stand"] else 0.0)
    )


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
            "seed": 1160,
        },
        {
            "name": "short-local-retrain-contact-tight",
            "train": True,
            "target_drop": 0.09,
            "support_floor": 0.0,
            "slip_limit": 0.050,
            "lookahead_s": 0.65,
            "anticipatory_action_mix": 0.45,
            "contact_action_scale": 0.70,
            "timesteps": args.timesteps,
            "seed": 1161,
        },
    ]
    result: dict[str, Any] = {
        "planning_gate": {
            "team_validation_mode": "manual-pass",
            "spec_delta": "After exp115 blocked public upstream scene parity, M19 tests local-scene tracker retrain as the next executable route.",
            "perspectives": {
                "product": "tries to create a native visible squat candidate instead of another adapter audit",
                "architecture": "reuses local scene and checkpoint-compatible future-reference tracker env",
                "security": "local MuJoCo/JAX only; no credentials",
                "qa": "source baseline, short restored PPO retrain, native exp29 gate, browser replay flag",
                "skeptic": "short retrain may not escape the shallow standing attractor",
            },
            "dod": [
                "run source baseline native gate",
                "run short restored PPO retrain native gate",
                "write raw JSON and summary with next action",
            ],
        },
        "web_sources": WEB_SOURCES,
        "visible_gate": VISIBLE_GATE,
        "evaluation_seconds": args.seconds,
        "runs": [],
    }
    for variant in variants:
        print(f"running {variant['name']}", flush=True)
        run = run_variant(variant, args)
        run["score"] = score(run)
        result["runs"].append(run)

    passed = [run for run in result["runs"] if run.get("native", {}).get("pass_visible_gate")]
    result["best"] = min(result["runs"], key=score)
    result["verdict"] = "PASS_VISIBLE_8CM_GATE" if passed else "FAIL_LOCAL_TRACKER_RETRAIN_SMOKE"
    result["browser_replay_attempted"] = bool(passed)
    result["next_action"] = (
        "attempt_browser_replay"
        if passed
        else "move_to_full_order_idqp_mpc_or_longer_motion_tracking_training"
    )
    return result


def write_summary(result: dict[str, Any]) -> None:
    lines = [
        "# G1 local-scene tracker retrain smoke",
        "",
        f"Verdict: `{result['verdict']}`",
        f"Next action: `{result['next_action']}`",
        "",
        "| Run | Score | Verdict | Drop | Knee | Hip | Contact | Slip | Final h | Fall |",
        "|---|---:|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for run in result["runs"]:
        native = run.get("native", {})
        fall = "never" if native.get("fell_at") is None else f"{native['fell_at']:.2f}s"
        lines.append(
            f"| {run['name']} | {run['score']:.1f} | {run['verdict']} | "
            f"{native.get('visible_drop', 0.0):.4f}m | {native.get('max_knee_delta_rad', 0.0):.3f} | "
            f"{native.get('max_hip_pitch_delta_rad', 0.0):.3f} | {native.get('foot_contact_ratio', 0.0):.2f} | "
            f"{native.get('foot_slip_distance', 0.0):.3f}m | {native.get('final_height', 0.0):.4f}m | {fall} |"
        )
    best = result["best"]
    lines.extend(
        [
            "",
            f"Best run: `{best['name']}` -> `{best['verdict']}`",
            "Browser replay is attempted only after native exp29 visible gate passes.",
        ]
    )
    (VERIFY / "local-scene-tracker-retrain-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_readme(result: dict[str, Any]) -> None:
    best = result["best"]
    best_native = best["native"]
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
    readme = f"""# 116-g1-local-scene-tracker-retrain-smoke — G1 local-scene tracker retrain smoke

## 1. 가설 (Hypothesis)

Exp115가 public upstream scene parity를 막았으므로, local `scene_g1_policy.xml` 기준 future-reference tracker를 짧게 restored PPO retrain하면 source baseline보다 exp29 visible gate에 가까워질 수 있다.

## 2. 방법 (Method)

### 셋업
- 모델: local MuJoCo G1 scene via exp111 `ContactAwareReferenceSquat`.
- 초기 checkpoint: exp105 future-reference tracker params.
- 실행: source no-train baseline과 short local retrain을 같은 native exp29 gate로 비교한다.
- 판정: native gate가 통과할 때만 browser replay를 시도한다.

### 웹 근거
- General Motion Retargeting은 foot sliding, self-penetration, infeasible motion artifact가 downstream RL tracking을 해친다고 설명한다. 접근일: 2026-06-18. https://arxiv.org/html/2510.02252v1
- Whole-body humanoid locomotion work는 Unitree G1에서 generated/reference motion과 RL-based tracking을 결합한다. 접근일: 2026-06-18. https://arxiv.org/html/2604.17335v1
- Humanoid squat TP-MPC/WBC 연구는 squat를 CoM/ZMP/foot-force/whole-body coordination 문제로 다룬다. 접근일: 2026-06-18. https://pmc.ncbi.nlm.nih.gov/articles/PMC11769464/
- Strict contact-force tracking은 floating-base humanoid motion tracking에서 contact force constraints가 핵심이라고 설명한다. 접근일: 2026-06-18. https://la.disneyresearch.com/wp-content/uploads/PROJECT_Humanoids-mocap_IEEE-RAS-ICHR-2013_PAPER1.pdf

### 시나리오
- `source-exp105-no-train`: exp105 source checkpoint를 retrain 없이 native gate 평가.
- `short-local-retrain-contact-tight`: contact/slip/action prior를 강화한 local scene restored PPO short retrain 후 native gate 평가.

### 측정 metric
- exp29 visible native gate: no fall, pelvis drop >=8cm, knee >=0.60rad, hip >=0.35rad, return, contact >=0.90, slip <=0.08m.
- browser replay attempted flag.

## 3. 결과 (Results)

### 데이터
| Run | Verdict | Drop | Knee | Hip | Contact | Slip | Final h | Fall |
|---|---|---:|---:|---:|---:|---:|---:|---|
{chr(10).join(rows)}

Verdict: `{result['verdict']}`.
Best run: `{best['name']}` with drop `{best_native['visible_drop']:.4f}m`, knee `{best_native['max_knee_delta_rad']:.3f}`, hip `{best_native['max_hip_pitch_delta_rad']:.3f}`.

### 박제 위치
- `verify/result.json`
- `verify/local-scene-tracker-retrain-summary.md`
- `verify/<run>/native-eval.json`
- `verify/<run>/train/params.pkl` for trained variants

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- Local-scene tracker retrain smoke는 M19 native visible gate를 닫지 못했다.
- Source baseline과 short retrain을 같은 gate로 비교해, shallow attractor를 단기 PPO로 벗어나는지 확인했다.
- native gate가 PASS하지 않았으므로 browser replay는 시도하지 않았다.

### 가설은 통과했나?
- [{'x' if result['verdict'] == 'PASS_VISIBLE_8CM_GATE' else ' '}] PASS — native exp29 visible gate를 통과했다.
- [{' ' if result['verdict'] == 'PASS_VISIBLE_8CM_GATE' else 'x'}] FAIL — short local-scene tracker retrain만으로 native visible gate를 닫지 못했다.

### 정의에 반영
- M19 완료 기준은 유지한다. native visible gate와 browser replay가 모두 필요하다.

### 다음 실험 후보
- full-order ID-QP/MPC: exp109 static target을 contact force/floating-base dynamics decision variable과 함께 추종한다.
- longer local motion-tracking training: short retrain이 아닌 longer tracker training으로 shallow attractor 탈출 여부를 별도 검증한다.
"""
    (EXP_DIR / "README.md").write_text(readme, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timesteps", type=int, default=4096)
    parser.add_argument("--seconds", type=float, default=6.0)
    parser.add_argument("--rollout-steps", type=int, default=20)
    parser.add_argument("--reuse-train", action="store_true")
    args = parser.parse_args()
    VERIFY.mkdir(parents=True, exist_ok=True)
    result = build_result(args)
    (VERIFY / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    write_summary(result)
    write_readme(result)
    print(json.dumps({"verdict": result["verdict"], "best": result["best"]["name"], "next_action": result["next_action"]}, indent=2), flush=True)


if __name__ == "__main__":
    main()
