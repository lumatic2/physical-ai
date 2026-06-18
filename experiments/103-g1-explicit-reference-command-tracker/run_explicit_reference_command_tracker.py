"""Train/evaluate an explicit visible-reference command tracker for G1 squat."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path


EXP_DIR = Path(__file__).resolve().parent
ROOT = EXP_DIR.parents[1]
VERIFY = EXP_DIR / "verify"
EXP80 = ROOT / "experiments/80-g1-corridor-curriculum-training"
EXP80_RUNNER = EXP80 / "run_corridor_curriculum.py"
EXP80_PARAMS = EXP80 / "verify/target-0p078-slip-0p08/train/params.pkl"
EXP50_PARAMS = ROOT / "experiments/50-g1-stance-constrained-curriculum-ppo/verify/target-0p03-slip-0p08/train/params.pkl"

if str(EXP80) not in sys.path:
    sys.path.insert(0, str(EXP80))
if str(EXP_DIR) not in sys.path:
    sys.path.insert(0, str(EXP_DIR))

from g1_explicit_reference_command_env import ExplicitReferenceCommandSquat  # noqa: E402


def load_exp80_runner():
    spec = importlib.util.spec_from_file_location("exp80_corridor_runner", EXP80_RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {EXP80_RUNNER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EXP80_MODULE = load_exp80_runner()
EXP80_PPO_CONFIG = EXP80_MODULE.ppo_config


def default_source() -> Path:
    return EXP80_PARAMS if EXP80_PARAMS.exists() else EXP50_PARAMS


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
    cfg = EXP80_PPO_CONFIG(timesteps)
    cfg.learning_rate = 4.0e-6
    cfg.num_evals = 3
    return cfg


def write_summary(result: dict, out_dir: Path) -> None:
    native = result["native"]
    train_result = result.get("train", {})
    fell = "never" if native["fell_at"] is None else f"{native['fell_at']:.2f}s"
    gap = native["visible_gap"]
    lines = [
        "# G1 Explicit Reference Command Tracker Summary",
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
        f"Visible gate gap: drop {gap['drop_shortfall_m']:.4f}m, knee {gap['knee_shortfall_rad']:.4f}rad, hip {gap['hip_shortfall_rad']:.4f}rad, slip excess {gap['slip_excess_m']:.4f}m.",
    ]
    (out_dir / "explicit-reference-command-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def update_readme(result: dict) -> None:
    readme = EXP_DIR / "README.md"
    text = readme.read_text(encoding="utf-8")
    native = result["native"]
    train = result.get("train", {})
    fell = "never" if native["fell_at"] is None else f"{native['fell_at']:.2f}s"
    evidence_dir = f"target-{result['target_drop']:.3f}-slip-{result['slip_limit']:.2f}".replace(".", "p")
    replacement = f"""## 3. 결과 (Results)

### 데이터
| Run | Verdict | Timesteps | Drop | Knee | Hip | Contact | Slip | Final h | Fall |
|-----|---------|---:|---:|---:|---:|---:|---:|---:|---|
| explicit-reference-command | {native['verdict']} | {train.get('timesteps', 0)} | {native['visible_drop']:.4f}m | {native['max_knee_delta_rad']:.3f}rad | {native['max_hip_pitch_delta_rad']:.3f}rad | {native['foot_contact_ratio']:.2f} | {native['foot_slip_distance']:.3f}m | {native['final_height']:.4f}m | {fell} |

Verdict: `{result['verdict']}`.

### 박제 위치
- `verify/{evidence_dir}/result.json`
- `verify/{evidence_dir}/native-eval.json`
- `verify/{evidence_dir}/explicit-reference-command-summary.md`
- `verify/{evidence_dir}/train/params.pkl`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- Explicit foot-fixed visible reference command training did not close M19 in this short finetune.
- Native rollout reached drop `{native['visible_drop']:.4f}m`, knee `{native['max_knee_delta_rad']:.3f}rad`, hip `{native['max_hip_pitch_delta_rad']:.3f}rad`, contact `{native['foot_contact_ratio']:.2f}`, slip `{native['foot_slip_distance']:.3f}m`.
- The result tells us whether changing the supervised command target alone is enough before moving to larger future-reference observations or external tracker ingestion.

### 가설은 통과했나?
- [ ] PASS
- [x] FAIL — explicit reference-command PPO did not produce a native visible gate pass.

### 정의에 반영
- M19 remains open. Browser replay is not attempted until the native gate passes.
"""
    start = text.index("## 3. 결과 (Results)")
    readme.write_text(text[:start] + replacement, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=None)
    parser.add_argument("--target-drop", type=float, default=0.090)
    parser.add_argument("--support-floor", type=float, default=-0.005)
    parser.add_argument("--slip-limit", type=float, default=0.08)
    parser.add_argument("--train", action="store_true")
    parser.add_argument("--timesteps", type=int, default=20_000)
    parser.add_argument("--seed", type=int, default=103)
    parser.add_argument("--seconds", type=float, default=6.0)
    args = parser.parse_args()

    EXP80_MODULE.make_env = make_env
    EXP80_MODULE.ppo_config = ppo_config
    EXP80_MODULE.EXP_DIR = EXP_DIR
    EXP80_MODULE.VERIFY = VERIFY
    source = args.source or default_source()
    out_dir = VERIFY / f"target-{args.target_drop:.3f}-slip-{args.slip_limit:.2f}".replace(".", "p")
    out_dir.mkdir(parents=True, exist_ok=True)
    result = {
        "planning_gate": {
            "team_validation_mode": "manual-pass",
            "spec_delta": "M19 tests a checkpoint-compatible explicit visible-reference command tracker.",
            "perspectives": {
                "product": "moves from hand-authored scalar injection toward a reference-conditioned policy route",
                "architecture": "preserves obs/action shape while swapping command target family to an explicit foot-fixed visible reference",
                "security": "local MuJoCo/JAX run only; no credentials",
                "qa": "compatibility, rollout smoke, restored PPO, native exp29 visible gate audit",
                "skeptic": "short finetune may still inherit exp80 stance/contact failure or under-flexed knee behavior",
            },
            "dod": [
                "explicit reference target env initializes",
                "source checkpoint shape matches",
                "native exp29 visible gate is audited after restored PPO",
            ],
        },
        "web_sources": [
            {"url": "https://arxiv.org/html/2507.07356v2", "accessed": "2026-06-18"},
            {"url": "https://arxiv.org/html/2506.14770v1", "accessed": "2026-06-18"},
            {"url": "https://github.com/LeCAR-Lab/ASAP", "accessed": "2026-06-18"},
            {"url": "https://www.mdpi.com/1424-8220/25/2/435", "accessed": "2026-06-18"},
        ],
        "visible_gate": EXP80_MODULE.VISIBLE_GATE,
        "target_drop": args.target_drop,
        "support_floor": args.support_floor,
        "slip_limit": args.slip_limit,
        "source_params": str(source),
        "compatibility": EXP80_MODULE.compatibility(source, args.target_drop, args.support_floor, args.slip_limit),
        "rollout": EXP80_MODULE.rollout_smoke(args.target_drop, args.support_floor, args.slip_limit),
    }
    if not result["compatibility"]["policy_shape_match"]:
        raise SystemExit("source and target policy shapes do not match")
    if args.train:
        result["train"] = EXP80_MODULE.train(source, args.target_drop, args.support_floor, args.slip_limit, args.timesteps, out_dir, args.seed)
        params_path = out_dir / "train" / "params.pkl"
    else:
        params_path = source
    result["native"] = EXP80_MODULE.native_eval(args.target_drop, args.support_floor, args.slip_limit, params_path, args.seconds, out_dir)
    result["verdict"] = result["native"]["verdict"]
    write_summary(result, out_dir)
    (out_dir / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    update_readme(result)
    print(result["verdict"], json.dumps(result["native"], indent=2), flush=True)


if __name__ == "__main__":
    main()
