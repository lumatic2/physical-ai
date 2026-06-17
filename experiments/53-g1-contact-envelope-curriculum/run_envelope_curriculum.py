"""Find the stable contact-aware curriculum boundary for G1 squat."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any


EXP_DIR = Path(__file__).resolve().parent
ROOT = EXP_DIR.parents[1]
VERIFY = EXP_DIR / "verify"
EXP52_PATH = ROOT / "experiments/52-g1-foot-contact-aware-height-controller/run_contact_height_controller.py"


def load_exp52():
    spec = importlib.util.spec_from_file_location("exp52_contact_height", EXP52_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {EXP52_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EXP52 = load_exp52()


def stance_pass(run: dict[str, Any]) -> bool:
    return (
        run["fell_at"] is None
        and run["return_to_stand"]
        and run["foot_contact_ratio"] >= 0.90
        and run["foot_slip_distance"] <= 0.15
        and run["max_joint_limit_violation"] <= 0.05
    )


def pose_pass(run: dict[str, Any]) -> bool:
    return run["visible_drop"] >= 0.08 and run["max_knee_delta_rad"] >= 0.60 and run["max_hip_pitch_delta_rad"] >= 0.35


def verdict(run: dict[str, Any]) -> str:
    if stance_pass(run) and pose_pass(run):
        return "PASS_NATIVE_VISIBLE_GATE"
    if not stance_pass(run):
        return "STANCE_ENVELOPE_BROKEN"
    return "STABLE_BUT_SHALLOW"


def write_summary(result: dict[str, Any], out_dir: Path) -> None:
    lines = [
        "# G1 Contact Envelope Curriculum Summary",
        "",
        "| Level | Verdict | Drop | Knee | Hip | Contact | Slip | Final h | Fell |",
        "|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for run in result["runs"]:
        fell = "never" if run["fell_at"] is None else f"{run['fell_at']:.2f}s"
        lines.append(
            f"| {run['attempt']} | {run['curriculum_verdict']} | {run['visible_drop']:.4f}m | "
            f"{run['max_knee_delta_rad']:.3f} | {run['max_hip_pitch_delta_rad']:.3f} | "
            f"{run['foot_contact_ratio']:.2f} | {run['foot_slip_distance']:.3f}m | "
            f"{run['final_height']:.4f}m | {fell} |"
        )
    lines.extend([
        "",
        f"Stable boundary: {result['stable_boundary']}",
        f"First broken level: {result['first_broken_level']}",
        "",
        "M19 closes only when visible depth, knee/hip pose, no-fall, contact, stance, return, and browser replay gates pass together.",
    ])
    (out_dir / "envelope-curriculum-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=6.0)
    parser.add_argument("--support-floor", type=float, default=-0.005)
    parser.add_argument("--slip-limit", type=float, default=0.08)
    args = parser.parse_args()

    out_dir = VERIFY / "envelope-curriculum"
    out_dir.mkdir(parents=True, exist_ok=True)
    levels = [
        {"attempt": "level-0p025", "drop": 0.025, "max_blend": 0.30, "adapt_gain": 0.08},
        {"attempt": "level-0p040", "drop": 0.040, "max_blend": 0.34, "adapt_gain": 0.09},
        {"attempt": "level-0p060", "drop": 0.060, "max_blend": 0.36, "adapt_gain": 0.10},
        {"attempt": "level-0p080", "drop": 0.080, "max_blend": 0.38, "adapt_gain": 0.11},
    ]
    result = {
        "planning_gate": {
            "team_validation_mode": "manual-pass",
            "spec_delta": "M19 probes a residual curriculum boundary inside the contact-aware controller envelope.",
            "perspectives": {
                "product": "keeps the visible squat native/browser gate intact",
                "architecture": "reuses exp52 controller; curriculum changes only target drop and blend residual envelope",
                "security": "no credentials or external side effects",
                "qa": "native rollout per level with stance and pose gates",
                "skeptic": "curriculum may reveal a hard stance cliff before visible depth",
            },
            "dod": [
                "native JSON per curriculum level",
                "summary identifies stable boundary and first broken level",
            ],
        },
        "runs": [],
    }
    stable_boundary = None
    first_broken = None
    for level in levels:
        run_dir = out_dir / level["attempt"]
        run = EXP52.native_eval(
            attempt=level["attempt"],
            drop=level["drop"],
            max_blend=level["max_blend"],
            policy_weight=1.0,
            adapt_gain=level["adapt_gain"],
            descend_s=2.6,
            hold_s=0.4,
            return_s=1.4,
            seconds=args.seconds,
            support_floor=args.support_floor,
            slip_limit=args.slip_limit,
            out_dir=run_dir,
        )
        run["curriculum_verdict"] = verdict(run)
        result["runs"].append(run)
        if stance_pass(run):
            stable_boundary = {
                "attempt": run["attempt"],
                "configured_drop": level["drop"],
                "actual_drop": run["visible_drop"],
                "slip": run["foot_slip_distance"],
            }
        elif first_broken is None:
            first_broken = {
                "attempt": run["attempt"],
                "configured_drop": level["drop"],
                "actual_drop": run["visible_drop"],
                "fell_at": run["fell_at"],
                "slip": run["foot_slip_distance"],
            }
    result["stable_boundary"] = stable_boundary
    result["first_broken_level"] = first_broken
    result["verdict"] = "PASS_M19_NATIVE_ONLY" if any(run["curriculum_verdict"] == "PASS_NATIVE_VISIBLE_GATE" for run in result["runs"]) else "FAIL_M19_NATIVE_GATE"
    write_summary(result, out_dir)
    (out_dir / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(result["verdict"], json.dumps({"stable_boundary": stable_boundary, "first_broken_level": first_broken}, indent=2), flush=True)


if __name__ == "__main__":
    main()
