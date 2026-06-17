"""Audit G1 squat recovery with a full return horizon after deep no-fall descent."""

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
        "downward_floor": 0.095,
        "stand_height": 0.74,
        "height_floor": 0.615,
        "upright_floor": 0.81,
        "qfrc_soft_cap": 56.0,
        "return_safety_boost": 0.22,
        "return_min_safety": 0.62,
        "descend_rate": 0.038,
        "small_hold": 0.010,
        "w_height": 58.0,
        "w_stand": 340.0,
        "w_height_floor": 1150.0,
        "w_upright": 700.0,
        "w_support": 2300.0,
        "w_zmp": 1650.0,
        "w_slip": 1200.0,
        "w_contact": 280.0,
        "w_downward": 150.0,
        "w_qfrc": 2.0,
        "w_smooth": 1.7,
    }


def variants() -> list[dict[str, Any]]:
    common = make_common()
    rows: list[dict[str, Any]] = []
    for drop in [0.0830, 0.0832, 0.0840]:
        for max_blend in [0.532, 0.533, 0.536]:
            for return_s in [1.15, 1.45, 1.75]:
                for release in [(0.09, 0.18), (0.12, 0.24)]:
                    slow_release, fast_release = release
                    rows.append({
                        **common,
                        "attempt": f"recover-d{drop:.4f}-b{max_blend:.3f}-tr{return_s:.2f}-rel{slow_release:.2f}-{fast_release:.2f}".replace(".", "p"),
                        "drop": drop,
                        "max_blend": max_blend,
                        "residual_scale": 0.0682,
                        "joint_kp": 25.5,
                        "torque_clip": 37.0,
                        "descend_s": 3.50,
                        "return_s": return_s,
                        "slow_release": slow_release,
                        "fast_release": fast_release,
                    })
    # Keep the experiment bounded while covering the exp69 deep cliff first.
    priority = {
        (0.0832, 0.533, 1.15): 0,
        (0.0832, 0.533, 1.45): 1,
        (0.0832, 0.536, 1.15): 2,
        (0.0840, 0.533, 1.15): 3,
    }
    rows.sort(key=lambda row: (
        priority.get((row["drop"], row["max_blend"], row["return_s"]), 9),
        abs(row["drop"] - 0.0832),
        abs(row["max_blend"] - 0.533),
        row["return_s"],
        row["slow_release"],
    ))
    return rows[:18]


def write_summary(result: dict[str, Any], out_dir: Path) -> None:
    lines = [
        "# G1 Full Return Recovery Horizon Summary",
        "",
        "| Attempt | 8cm | 7cm | Verdict | Drop | Contact | Slip | CoM min | ZMP min | qfrc | Final h | Fell |",
        "|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for run in result["runs"]:
        fell = "never" if run["fell_at"] is None else f"{run['fell_at']:.2f}s"
        gate8 = "PASS" if run["visible_8cm_gate"] else "FAIL"
        gate7 = "PASS" if run["recoverable_7cm_gate"] else "FAIL"
        lines.append(
            f"| {run['attempt']} | {gate8} | {gate7} | {run['transition_verdict']} | "
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
        "This audit uses a 7s rollout so the return phase can finish before verdict assignment.",
    ])
    (out_dir / "full-return-recovery-horizon-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=7.0)
    args = parser.parse_args()
    out_dir = VERIFY / "full-return-recovery-horizon"
    out_dir.mkdir(parents=True, exist_ok=True)
    result = {
        "evaluation_seconds": args.seconds,
        "planning_gate": {
            "team_validation_mode": "manual-pass",
            "spec_delta": "M19 now separates descent success from full-return recovery by evaluating beyond descend+hold+return horizon.",
            "perspectives": {
                "product": "checks whether exp69's deep no-fall state was only cut short by a too-short rollout",
                "architecture": "keeps exp67 WBC selector and sweeps return release/stand weights around the deep no-fall corridor",
                "security": "local MuJoCo/JAX only",
                "qa": "raw native JSON per candidate plus 7cm/8cm gates",
                "skeptic": "if all deep candidates fall during return, the next step needs a truly separate recovery controller, not another release sweep",
            },
            "dod": [
                "return horizon exceeds descend+hold+return duration",
                "raw native evidence records whether deep candidates stand up, fall, or remain pending",
            ],
        },
        "sources": [
            {
                "url": "https://www.mdpi.com/1424-8220/25/2/435",
                "accessed": "2026-06-18",
                "note": "Squat-like humanoid motion separates trajectory optimization and WBC tracking.",
            },
            {
                "url": "https://arxiv.org/html/2505.19540v1",
                "accessed": "2026-06-18",
                "note": "WB-MPC uses horizon-level ZMP/contact constraints for biped stability.",
            },
            {
                "url": "https://www.lirmm.fr/krut/pdf/2014_galdeano_ssd-0568454426/2014_galdeano_ssd.pdf",
                "accessed": "2026-06-18",
                "note": "Task-based WBC for squat-like motion controls CoM with ZMP regulation, feet pose, and joint limits.",
            },
        ],
        "runs": [],
    }
    for variant in variants():
        run = EXP67.native_eval(
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
