"""Finetune exp80 visible geometry toward contact-preserving return."""

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

from g1_constrained_return_env import ConstrainedReturnSquat  # noqa: E402


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


def make_env(target_drop: float, support_floor: float, slip_limit: float) -> ConstrainedReturnSquat:
    return ConstrainedReturnSquat(
        target_drop=target_drop,
        support_floor=support_floor,
        slip_limit=slip_limit,
        descend_s=3.0,
        hold_s=0.2,
        return_s=1.8,
        config_overrides={"impl": "jax"},
    )


def ppo_config(timesteps: int):
    cfg = EXP80_PPO_CONFIG(timesteps)
    cfg.learning_rate = 5.0e-6
    cfg.num_evals = 3
    return cfg


def write_summary(result: dict, out_dir: Path) -> None:
    native = result["native"]
    train_result = result.get("train", {})
    fell = "never" if native["fell_at"] is None else f"{native['fell_at']:.2f}s"
    gap = native["visible_gap"]
    lines = [
        "# G1 Constrained Return Finetune Summary",
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
        "This experiment starts from exp80 visible geometry and asks whether contact/slip/terminal stand can be recovered without losing the visible gate.",
    ]
    (out_dir / "constrained-return-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=None)
    parser.add_argument("--target-drop", type=float, default=0.080)
    parser.add_argument("--support-floor", type=float, default=0.000)
    parser.add_argument("--slip-limit", type=float, default=0.06)
    parser.add_argument("--train", action="store_true")
    parser.add_argument("--timesteps", type=int, default=20_000)
    parser.add_argument("--seed", type=int, default=81)
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
            "spec_delta": "M19 now tests a second-stage constrained return finetune from the exp80 visible-geometry checkpoint.",
            "perspectives": {
                "product": "targets exp80's remaining failure: contact/slip/return collapse after reaching visible geometry",
                "architecture": "reuses exp80 evaluator and checkpoint shape; only env rewards and source checkpoint differ",
                "security": "no secrets or external credentials",
                "qa": "compatibility, rollout smoke, restored PPO, native exp29 visible gate audit",
                "skeptic": "strong contact/slip terms may erase visible depth and return to a conservative micro-squat",
            },
            "dod": [
                "constrained return reward metrics execute",
                "exp80 checkpoint finetunes without shape mismatch",
                "native exp29 visible gate is audited with contact/slip/return metrics",
            ],
        },
        "web_sources": [
            {
                "url": "https://arxiv.org/html/2502.12152v2",
                "accessed": "2026-06-18",
                "use": "G1 getting-up work motivates a second stage that refines discovered motions into smooth deployable motions.",
            },
            {
                "url": "https://www.mdpi.com/2313-7673/10/11/783",
                "accessed": "2026-06-18",
                "use": "Two-stage sit-stand RL motivates separating transient contact-rich discovery from constrained execution.",
            },
            {
                "url": "https://www.mdpi.com/1424-8220/25/2/435",
                "accessed": "2026-06-18",
                "use": "Humanoid squat control literature emphasizes foot forces, dynamic constraints, MPC trajectory, and WBC tracking.",
            },
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
    print(result["verdict"], json.dumps(result["native"], indent=2), flush=True)


if __name__ == "__main__":
    main()
