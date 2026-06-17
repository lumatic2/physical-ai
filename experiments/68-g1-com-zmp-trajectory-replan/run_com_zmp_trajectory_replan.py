"""Sweep multi-step CoM/ZMP trajectory parameters for the G1 squat corridor."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any


EXP_DIR = Path(__file__).resolve().parent
ROOT = EXP_DIR.parents[1]
VERIFY = EXP_DIR / "verify"
EXP67_PATH = ROOT / "experiments/67-g1-qfrc-wbc-return-selector/run_qfrc_wbc_return_selector.py"


def load_exp67():
    spec = importlib.util.spec_from_file_location("exp67_qfrc_wbc_selector", EXP67_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {EXP67_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EXP67 = load_exp67()


def recoverable_7cm_gate(run: dict[str, Any]) -> bool:
    return (
        run["fell_at"] is None
        and run["visible_drop"] >= 0.07
        and run["return_to_stand"]
        and run["foot_contact_ratio"] >= 0.90
        and run["foot_slip_distance"] <= 0.08
        and run["max_joint_limit_violation"] <= 0.05
    )


def annotate(run: dict[str, Any]) -> dict[str, Any]:
    run["recoverable_7cm_gate"] = recoverable_7cm_gate(run)
    if run["recoverable_7cm_gate"]:
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


def make_common() -> dict[str, Any]:
    return {
        "policy_weight": 1.0,
        "joint_kd": 1.2,
        "foot_kp_xy": 0.0,
        "foot_force_clip": 0.0,
        "foot_kd_xy": 12.0,
        "foot_lift_force": 120.0,
        "support_floor": 0.006,
        "zmp_floor": -0.035,
        "slip_floor": 0.070,
        "downward_floor": 0.10,
        "stand_height": 0.74,
        "height_floor": 0.61,
        "upright_floor": 0.80,
        "qfrc_soft_cap": 55.0,
        "return_safety_boost": 0.18,
        "return_min_safety": 0.55,
        "descend_rate": 0.040,
        "slow_release": 0.060,
        "fast_release": 0.130,
        "small_hold": 0.010,
        "w_height": 70.0,
        "w_stand": 190.0,
        "w_height_floor": 950.0,
        "w_upright": 540.0,
        "w_support": 1800.0,
        "w_zmp": 1200.0,
        "w_slip": 900.0,
        "w_contact": 220.0,
        "w_downward": 120.0,
        "w_qfrc": 2.0,
        "w_smooth": 1.6,
    }


def write_summary(result: dict[str, Any], out_dir: Path) -> None:
    lines = [
        "# G1 CoM/ZMP Trajectory Replan Summary",
        "",
        "| Attempt | 7cm gate | Verdict | Drop | Contact | Slip | CoM min | ZMP min | qfrc | Final h | Fell |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for run in result["runs"]:
        fell = "never" if run["fell_at"] is None else f"{run['fell_at']:.2f}s"
        gate = "PASS" if run["recoverable_7cm_gate"] else "FAIL"
        lines.append(
            f"| {run['attempt']} | {gate} | {run['transition_verdict']} | "
            f"{run['visible_drop']:.4f}m | {run['foot_contact_ratio']:.2f} | "
            f"{run['foot_slip_distance']:.3f}m | {run['min_support_margin']:.4f}m | "
            f"{run['min_zmp_margin']:.4f}m | {run['max_qfrc_applied']:.1f} | "
            f"{run['final_height']:.4f}m | {fell} |"
        )
    lines.extend([
        "",
        f"Best recoverable run: {result['best_recoverable']}",
        f"Best no-fall run: {result['best_no_fall']}",
        f"Best depth run: {result['best_depth']}",
        "",
        "This is still an intermediate 7cm recoverable gate. M19 closes only after the exp29 8cm native/browser gate passes.",
    ])
    (out_dir / "com-zmp-trajectory-replan-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=6.0)
    args = parser.parse_args()
    out_dir = VERIFY / "com-zmp-trajectory-replan"
    out_dir.mkdir(parents=True, exist_ok=True)
    common = make_common()
    variants = [
        {**common, "attempt": "plan-8cm-early-return", "drop": 0.080, "max_blend": 0.52, "residual_scale": 0.066, "joint_kp": 24.0, "torque_clip": 34.0, "descend_s": 3.45, "return_s": 2.15},
        {**common, "attempt": "plan-8p2cm-early-return", "drop": 0.082, "max_blend": 0.53, "residual_scale": 0.068, "joint_kp": 25.0, "torque_clip": 36.0, "descend_s": 3.50, "return_s": 2.10},
        {**common, "attempt": "plan-8p25cm-fine", "drop": 0.0825, "max_blend": 0.532, "residual_scale": 0.0685, "joint_kp": 25.0, "torque_clip": 36.0, "descend_s": 3.50, "return_s": 2.12, "w_height": 78.0, "w_stand": 180.0},
        {**common, "attempt": "plan-8p3cm-fine", "drop": 0.083, "max_blend": 0.535, "residual_scale": 0.069, "joint_kp": 25.0, "torque_clip": 36.0, "descend_s": 3.52, "return_s": 2.12, "w_height": 82.0, "w_stand": 175.0},
        {**common, "attempt": "plan-8p35cm-fine", "drop": 0.0835, "max_blend": 0.538, "residual_scale": 0.0695, "joint_kp": 25.0, "torque_clip": 36.0, "descend_s": 3.54, "return_s": 2.10, "w_height": 86.0, "w_stand": 170.0},
        {**common, "attempt": "plan-8p4cm-early-return", "drop": 0.084, "max_blend": 0.54, "residual_scale": 0.070, "joint_kp": 25.0, "torque_clip": 36.0, "descend_s": 3.55, "return_s": 2.05},
        {**common, "attempt": "plan-8p2cm-mid-return", "drop": 0.082, "max_blend": 0.535, "residual_scale": 0.069, "joint_kp": 24.0, "torque_clip": 34.0, "descend_s": 3.80, "return_s": 1.80, "w_height": 95.0, "w_stand": 145.0},
        {**common, "attempt": "plan-8p5cm-mid-return", "drop": 0.085, "max_blend": 0.545, "residual_scale": 0.070, "joint_kp": 25.0, "torque_clip": 36.0, "descend_s": 3.85, "return_s": 1.75, "w_height": 110.0, "w_stand": 130.0},
        {**common, "attempt": "plan-9cm-support-heavy", "drop": 0.090, "max_blend": 0.55, "residual_scale": 0.070, "joint_kp": 26.0, "torque_clip": 38.0, "descend_s": 4.00, "return_s": 1.70, "w_support": 2400.0, "w_zmp": 1800.0, "w_height": 90.0},
    ]
    result = {
        "evaluation_seconds": args.seconds,
        "planning_gate": {
            "team_validation_mode": "manual-pass",
            "spec_delta": "M19 moves from single-step target selection to multi-step trajectory parameter replanning over descend/return timing and CoM/ZMP-heavy costs.",
            "perspectives": {
                "product": "directly targets the 7cm recoverable gate blocking visible squat",
                "architecture": "reuses exp67 qfrc WBC selector but changes trajectory timing and cost weights as the planning layer",
                "security": "no credentials or external side effects",
                "qa": "native sweep records raw JSON, contact, slip, support/ZMP, qfrc, return, and fall",
                "skeptic": "parameter sweep is still weaker than a continuous MPC optimizer, but it tests whether planning-level timing is the missing factor",
            },
            "dod": [
                "raw native JSON per trajectory plan",
                "summary states whether any plan passes recoverable_7cm_gate",
            ],
        },
        "sources": [
            {
                "url": "https://www.mdpi.com/1424-8220/25/2/435",
                "accessed": "2026-06-18",
                "note": "TP-MPC optimizes the rough squat trajectory and WBC tracks it with constraints.",
            },
            {
                "url": "https://arxiv.org/html/2505.19540v1",
                "accessed": "2026-06-18",
                "note": "Whole-body MPC handles ZMP and contact force constraints over a horizon.",
            },
            {
                "url": "https://underactuated.mit.edu/humanoids.html",
                "accessed": "2026-06-18",
                "note": "ZMP planning frames humanoid balance as CoM trajectory generation against support constraints.",
            },
        ],
        "runs": [],
    }
    for variant in variants:
        result["runs"].append(annotate(EXP67.native_eval(
            variant=variant,
            seconds=args.seconds,
            out_dir=out_dir / variant["attempt"],
        )))
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
    result["verdict"] = "PASS_RECOVERABLE_7CM_GATE" if recoverable else "FAIL_RECOVERABLE_7CM_GATE"
    write_summary(result, out_dir)
    (out_dir / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(result["verdict"], json.dumps({
        "best_recoverable": result["best_recoverable"],
        "best_no_fall": result["best_no_fall"],
        "best_depth": result["best_depth"],
    }, indent=2), flush=True)


if __name__ == "__main__":
    main()
