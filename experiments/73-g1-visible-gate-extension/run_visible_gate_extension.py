"""Extend the exp72 recoverable corridor toward the exp29 8cm visible gate."""

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


def visible_gap(run: dict[str, Any]) -> dict[str, float]:
    return {
        "drop_shortfall_m": max(0.0, 0.08 - run["visible_drop"]),
        "knee_shortfall_rad": max(0.0, 0.60 - run["max_knee_delta_rad"]),
        "hip_shortfall_rad": max(0.0, 0.35 - run["max_hip_pitch_delta_rad"]),
        "slip_excess_m": max(0.0, run["foot_slip_distance"] - 0.08),
    }


def annotate(run: dict[str, Any]) -> dict[str, Any]:
    run["recoverable_7cm_gate"] = recoverable_7cm_gate(run)
    run["visible_8cm_gate"] = visible_8cm_gate(run)
    run["visible_gap"] = visible_gap(run)
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
        "residual_scale": 0.0682,
        "joint_kp": 26.0,
        "torque_clip": 38.0,
        "descend_s": 3.50,
        "return_s": 1.15,
        "slow_release": 0.090,
        "fast_release": 0.180,
        "recapture_support_floor": 0.010,
        "recapture_zmp_floor": -0.018,
        "recapture_error_gain": 2.7,
        "w_support": 2850.0,
        "w_zmp": 2250.0,
        "w_slip": 1450.0,
    }


def variants() -> list[dict[str, Any]]:
    base = base_variant()
    rows: list[dict[str, Any]] = []
    for drop in [0.086, 0.089, 0.092]:
        for blend in [0.542, 0.546, 0.550]:
            for trigger in [0.0660, 0.0670, 0.0680]:
                for hold in [0.14, 0.16, 0.18]:
                    # Keep run count bounded; center around exp72's pass with a bit more authority.
                    if blend == 0.550 and hold == 0.18 and trigger > 0.066:
                        continue
                    rows.append({
                        **base,
                        "attempt": f"visible-d{drop:.3f}-b{blend:.3f}-trig{trigger:.4f}-hold{hold:.2f}".replace(".", "p"),
                        "drop": drop,
                        "max_blend": blend,
                        "recapture_trigger_drop": trigger,
                        "recapture_hold_s": hold,
                    })
    rows.sort(key=lambda row: (
        abs(row["drop"] - 0.089),
        abs(row["max_blend"] - 0.546),
        abs(row["recapture_trigger_drop"] - 0.066),
        abs(row["recapture_hold_s"] - 0.16),
    ))
    return rows[:27]


def run_score(run: dict[str, Any]) -> float:
    gap = run["visible_gap"]
    fall = 1000.0 if run["fell_at"] is not None else 0.0
    return (
        fall
        + 100.0 * gap["drop_shortfall_m"]
        + 15.0 * gap["knee_shortfall_rad"]
        + 15.0 * gap["hip_shortfall_rad"]
        + 20.0 * gap["slip_excess_m"]
        - run["visible_drop"]
    )


def write_summary(result: dict[str, Any], out_dir: Path) -> None:
    lines = [
        "# G1 Visible Gate Extension Summary",
        "",
        "| Attempt | 8cm | 7cm | Verdict | Drop | Knee | Hip | Contact | Slip | CoM min | ZMP min | Final h | Fell | Gap d/k/h |",
        "|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for run in sorted(result["runs"], key=run_score):
        fell = "never" if run["fell_at"] is None else f"{run['fell_at']:.2f}s"
        gate8 = "PASS" if run["visible_8cm_gate"] else "FAIL"
        gate7 = "PASS" if run["recoverable_7cm_gate"] else "FAIL"
        gap = run["visible_gap"]
        lines.append(
            f"| {run['attempt']} | {gate8} | {gate7} | {run['transition_verdict']} | "
            f"{run['visible_drop']:.4f}m | {run['max_knee_delta_rad']:.3f} | "
            f"{run['max_hip_pitch_delta_rad']:.3f} | {run['foot_contact_ratio']:.2f} | "
            f"{run['foot_slip_distance']:.3f}m | {run['min_support_margin']:.4f}m | "
            f"{run['min_zmp_margin']:.4f}m | {run['final_height']:.4f}m | {fell} | "
            f"{gap['drop_shortfall_m']:.4f}/{gap['knee_shortfall_rad']:.3f}/{gap['hip_shortfall_rad']:.3f} |"
        )
    lines.extend([
        "",
        f"Best visible run: {result['best_visible']}",
        f"Best recoverable run: {result['best_recoverable']}",
        f"Best no-fall run: {result['best_no_fall']}",
        f"Best depth run: {result['best_depth']}",
    ])
    (out_dir / "visible-gate-extension-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=7.0)
    args = parser.parse_args()
    out_dir = VERIFY / "visible-gate-extension"
    out_dir.mkdir(parents=True, exist_ok=True)
    result = {
        "evaluation_seconds": args.seconds,
        "planning_gate": {
            "team_validation_mode": "manual-pass",
            "spec_delta": "M19 moves from a 7cm recoverable intermediate gate to the exp29 8cm visible gate with knee/hip checks.",
            "perspectives": {
                "product": "targets the actual visible squat criteria instead of another intermediate gate",
                "architecture": "reuses exp71 event recapture and increases target drop/blend while measuring joint flexion gaps",
                "security": "local MuJoCo/JAX only",
                "qa": "native raw JSON per candidate plus 8cm/knee/hip/support gates",
                "skeptic": "more target authority may immediately re-enter the support/ZMP collapse branch",
            },
            "dod": [
                "run visible-gate candidates around exp72's pass",
                "report best 8cm gate result and remaining drop/knee/hip gaps",
            ],
        },
        "sources": [
            {
                "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC11769464/",
                "accessed": "2026-06-18",
                "note": "Humanoid squat motion is framed as trajectory optimization plus WBC tracking.",
            },
            {
                "url": "https://www.lirmm.fr/krut/pdf/2014_galdeano_ssd-0568454426/2014_galdeano_ssd.pdf",
                "accessed": "2026-06-18",
                "note": "Squat-like WBC controls CoM/ZMP, feet pose, and joint limits.",
            },
            {
                "url": "https://arxiv.org/html/2502.17219v1",
                "accessed": "2026-06-18",
                "note": "ZMP inside the support polygon is a dynamic balance condition for humanoids.",
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
    visible = [run for run in result["runs"] if run["visible_8cm_gate"]]
    recoverable = [run for run in result["runs"] if run["recoverable_7cm_gate"]]
    no_fall = [run for run in result["runs"] if run["fell_at"] is None]
    best_visible = max(visible, key=lambda run: run["visible_drop"], default=None)
    best_recoverable = max(recoverable, key=lambda run: run["visible_drop"], default=None)
    best_no_fall = min(no_fall, key=run_score, default=None)
    best_depth = max(result["runs"], key=lambda run: run["visible_drop"])
    result["best_visible"] = None if best_visible is None else {
        "attempt": best_visible["attempt"],
        "visible_drop": best_visible["visible_drop"],
        "final_height": best_visible["final_height"],
    }
    result["best_recoverable"] = None if best_recoverable is None else {
        "attempt": best_recoverable["attempt"],
        "visible_drop": best_recoverable["visible_drop"],
        "transition_verdict": best_recoverable["transition_verdict"],
        "visible_gap": best_recoverable["visible_gap"],
    }
    result["best_no_fall"] = None if best_no_fall is None else {
        "attempt": best_no_fall["attempt"],
        "visible_drop": best_no_fall["visible_drop"],
        "transition_verdict": best_no_fall["transition_verdict"],
        "visible_gap": best_no_fall["visible_gap"],
        "final_height": best_no_fall["final_height"],
    }
    result["best_depth"] = {
        "attempt": best_depth["attempt"],
        "visible_drop": best_depth["visible_drop"],
        "fell_at": best_depth["fell_at"],
        "transition_verdict": best_depth["transition_verdict"],
    }
    if visible:
        result["verdict"] = "PASS_VISIBLE_8CM_GATE"
    elif recoverable:
        result["verdict"] = "PASS_RECOVERABLE_7CM_GATE"
    else:
        result["verdict"] = "FAIL_VISIBLE_8CM_GATE"
    write_summary(result, out_dir)
    (out_dir / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(result["verdict"], json.dumps({
        "best_visible": result["best_visible"],
        "best_recoverable": result["best_recoverable"],
        "best_no_fall": result["best_no_fall"],
        "best_depth": result["best_depth"],
    }, indent=2), flush=True)


if __name__ == "__main__":
    main()
