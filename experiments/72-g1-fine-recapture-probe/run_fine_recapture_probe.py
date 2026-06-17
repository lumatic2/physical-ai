"""Fine probe around the G1 event-triggered recapture 7cm boundary."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any


EXP_DIR = Path(__file__).resolve().parent
ROOT = EXP_DIR.parents[1]
VERIFY = EXP_DIR / "verify"
EXP71_PATH = ROOT / "experiments/71-g1-event-triggered-recapture/run_event_triggered_recapture.py"


def load_exp71():
    spec = importlib.util.spec_from_file_location("exp71_event_recap", EXP71_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {EXP71_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EXP71 = load_exp71()


def recoverable_7cm_gate(run: dict[str, Any]) -> bool:
    return (
        run["fell_at"] is None
        and run["visible_drop"] >= 0.07
        and run["return_to_stand"]
        and run["foot_contact_ratio"] >= 0.90
        and run["foot_slip_distance"] <= 0.08
        and run["max_joint_limit_violation"] <= 0.05
    )


def visible_8cm_gate(run: dict[str, Any]) -> bool:
    return (
        run["fell_at"] is None
        and run["visible_drop"] >= 0.08
        and run["max_knee_delta_rad"] >= 0.60
        and run["max_hip_pitch_delta_rad"] >= 0.35
        and run["return_to_stand"]
        and run["foot_contact_ratio"] >= 0.90
        and run["foot_slip_distance"] <= 0.08
        and run["max_joint_limit_violation"] <= 0.05
    )


def annotate(run: dict[str, Any]) -> dict[str, Any]:
    run["recoverable_7cm_gate"] = recoverable_7cm_gate(run)
    run["visible_8cm_gate"] = visible_8cm_gate(run)
    if run["visible_8cm_gate"]:
        run["transition_verdict"] = "PASS_VISIBLE_8CM_GATE"
    elif run["recoverable_7cm_gate"]:
        run["transition_verdict"] = "PASS_RECOVERABLE_7CM_GATE"
    elif run["fell_at"] is not None:
        run["transition_verdict"] = "FAIL_FALL"
    elif run["visible_drop"] < 0.07:
        run["transition_verdict"] = "DEPTH_PENDING_7CM"
    elif not run["return_to_stand"]:
        run["transition_verdict"] = "RETURN_PENDING"
    elif run["foot_contact_ratio"] < 0.90:
        run["transition_verdict"] = "CONTACT_PENDING"
    elif run["foot_slip_distance"] > 0.08:
        run["transition_verdict"] = "STANCE_SLIP_PENDING"
    else:
        run["transition_verdict"] = "GATE_PENDING"
    return run


def base_variant() -> dict[str, Any]:
    common = EXP71.make_common()
    return {
        **common,
        "drop": 0.0835,
        "residual_scale": 0.0682,
        "joint_kp": 25.5,
        "torque_clip": 37.0,
        "descend_s": 3.50,
        "return_s": 1.15,
        "slow_release": 0.090,
        "fast_release": 0.180,
        "recapture_support_floor": 0.010,
        "recapture_zmp_floor": -0.018,
    }


def variants() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    base = base_variant()
    for trigger in [0.0660, 0.0662, 0.0664, 0.0666]:
        for hold in [0.12, 0.14, 0.16, 0.18]:
            for blend in [0.540, 0.542]:
                row = {
                    **base,
                    "attempt": f"fine-trig{trigger:.4f}-hold{hold:.2f}-b{blend:.3f}".replace(".", "p"),
                    "max_blend": blend,
                    "recapture_trigger_drop": trigger,
                    "recapture_hold_s": hold,
                    "recapture_error_gain": 2.6,
                }
                rows.append(row)
    # Add a few higher support-gain candidates around the previous best.
    for hold in [0.14, 0.16]:
        rows.append({
            **base,
            "attempt": f"fine-support-heavy-hold{hold:.2f}".replace(".", "p"),
            "max_blend": 0.540,
            "recapture_trigger_drop": 0.0660,
            "recapture_hold_s": hold,
            "recapture_error_gain": 3.0,
            "w_support": 3100.0,
            "w_zmp": 2450.0,
            "w_slip": 1500.0,
        })
    rows.sort(key=lambda row: (
        abs(row["recapture_hold_s"] - 0.14),
        abs(row["recapture_trigger_drop"] - 0.0660),
        abs(row["max_blend"] - 0.540),
        -row["recapture_error_gain"],
    ))
    return rows[:24]


def write_summary(result: dict[str, Any], out_dir: Path) -> None:
    lines = [
        "# G1 Fine Recapture Probe Summary",
        "",
        "| Attempt | 8cm | 7cm | Verdict | Drop | Recap | Contact | Slip | CoM min | ZMP min | Final h | Knee | Hip | Fell |",
        "|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for run in result["runs"]:
        fell = "never" if run["fell_at"] is None else f"{run['fell_at']:.2f}s"
        gate8 = "PASS" if run["visible_8cm_gate"] else "FAIL"
        gate7 = "PASS" if run["recoverable_7cm_gate"] else "FAIL"
        recap = "-" if run["recapture_at"] is None else f"{run['recapture_at']:.2f}s"
        lines.append(
            f"| {run['attempt']} | {gate8} | {gate7} | {run['transition_verdict']} | "
            f"{run['visible_drop']:.4f}m | {recap} | {run['foot_contact_ratio']:.2f} | "
            f"{run['foot_slip_distance']:.3f}m | {run['min_support_margin']:.4f}m | "
            f"{run['min_zmp_margin']:.4f}m | {run['final_height']:.4f}m | "
            f"{run['max_knee_delta_rad']:.3f} | {run['max_hip_pitch_delta_rad']:.3f} | {fell} |"
        )
    lines.extend([
        "",
        f"Best recoverable run: {result['best_recoverable']}",
        f"Best no-fall run: {result['best_no_fall']}",
        f"Best depth run: {result['best_depth']}",
    ])
    (out_dir / "fine-recapture-probe-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=7.0)
    args = parser.parse_args()
    out_dir = VERIFY / "fine-recapture-probe"
    out_dir.mkdir(parents=True, exist_ok=True)
    result = {
        "evaluation_seconds": args.seconds,
        "planning_gate": {
            "team_validation_mode": "manual-pass",
            "spec_delta": "M19 narrows event-triggered recapture to the 6.86-7.00cm support/ZMP boundary instead of broad controller search.",
            "perspectives": {
                "product": "tries to close the intermediate 7cm recoverable gate that blocks the visible squat path",
                "architecture": "reuses exp71's event-triggered phase machine and only changes trigger/hold/blend/support weights",
                "security": "local MuJoCo/JAX only",
                "qa": "native raw JSON per candidate plus summary gates",
                "skeptic": "the 7cm cliff may be a hard support constraint for this actuator-space controller",
            },
            "dod": [
                "run at least 20 fine candidates around exp71 best",
                "report whether any run passes recoverable_7cm_gate",
            ],
        },
        "sources": [
            {
                "url": "https://arxiv.org/abs/1612.08034",
                "accessed": "2026-06-18",
                "note": "Capture-point recovery motivates narrow timing around support-capture boundaries.",
            },
            {
                "url": "https://underactuated.mit.edu/humanoids.html",
                "accessed": "2026-06-18",
                "note": "ZMP/CoM stability is evaluated relative to the support region.",
            },
            {
                "url": "https://arxiv.org/html/2505.19540v1",
                "accessed": "2026-06-18",
                "note": "WB-MPC constrains ZMP/contact over the horizon for humanoid stability.",
            },
        ],
        "runs": [],
    }
    for variant in variants():
        run = EXP71.native_eval_event(
            variant=variant,
            seconds=args.seconds,
            out_dir=out_dir / variant["attempt"],
        )
        result["runs"].append(annotate(run))
    recoverable = [run for run in result["runs"] if run["recoverable_7cm_gate"]]
    no_fall = [run for run in result["runs"] if run["fell_at"] is None]
    best_recoverable = max(recoverable, key=lambda run: run["visible_drop"], default=None)
    best_no_fall = max(no_fall, key=lambda run: run["visible_drop"], default=None)
    best_depth = max(result["runs"], key=lambda run: run["visible_drop"])
    result["best_recoverable"] = None if best_recoverable is None else {
        "attempt": best_recoverable["attempt"],
        "visible_drop": best_recoverable["visible_drop"],
        "final_height": best_recoverable["final_height"],
    }
    result["best_no_fall"] = None if best_no_fall is None else {
        "attempt": best_no_fall["attempt"],
        "visible_drop": best_no_fall["visible_drop"],
        "transition_verdict": best_no_fall["transition_verdict"],
        "final_height": best_no_fall["final_height"],
    }
    result["best_depth"] = {
        "attempt": best_depth["attempt"],
        "visible_drop": best_depth["visible_drop"],
        "fell_at": best_depth["fell_at"],
        "transition_verdict": best_depth["transition_verdict"],
    }
    if any(run["visible_8cm_gate"] for run in result["runs"]):
        result["verdict"] = "PASS_VISIBLE_8CM_GATE"
    elif recoverable:
        result["verdict"] = "PASS_RECOVERABLE_7CM_GATE"
    else:
        result["verdict"] = "FAIL_RECOVERABLE_7CM_GATE"
    write_summary(result, out_dir)
    (out_dir / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(result["verdict"], json.dumps({
        "best_recoverable": result["best_recoverable"],
        "best_no_fall": result["best_no_fall"],
        "best_depth": result["best_depth"],
    }, indent=2), flush=True)


if __name__ == "__main__":
    main()
