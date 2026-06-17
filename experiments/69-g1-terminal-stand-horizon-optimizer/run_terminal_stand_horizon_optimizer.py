"""Optimize terminal-stand constrained G1 squat plans over full native rollouts."""

from __future__ import annotations

import argparse
import importlib.util
import itertools
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


def terminal_stand_score(run: dict[str, Any]) -> float:
    fall = 10000.0 if run["fell_at"] is not None else 0.0
    depth_shortfall = max(0.0, 0.07 - run["visible_drop"])
    terminal_shortfall = max(0.0, 0.74 - run["final_height"])
    contact_shortfall = max(0.0, 0.90 - run["foot_contact_ratio"])
    slip_excess = max(0.0, run["foot_slip_distance"] - 0.08)
    support_breach = max(0.0, 0.006 - run["min_support_margin"])
    zmp_breach = max(0.0, -0.035 - run["min_zmp_margin"])
    joint_excess = max(0.0, run["max_joint_limit_violation"] - 0.05)
    return (
        fall
        + 28000.0 * depth_shortfall
        + 22000.0 * terminal_shortfall
        + 5000.0 * contact_shortfall
        + 1800.0 * slip_excess
        + 2200.0 * support_breach
        + 1200.0 * zmp_breach
        + 1000.0 * joint_excess
        - 15.0 * run["visible_drop"]
    )


def annotate(run: dict[str, Any]) -> dict[str, Any]:
    run["terminal_stand_score"] = terminal_stand_score(run)
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
        "return_safety_boost": 0.20,
        "return_min_safety": 0.58,
        "descend_rate": 0.038,
        "slow_release": 0.060,
        "fast_release": 0.132,
        "small_hold": 0.010,
        "w_height": 78.0,
        "w_stand": 210.0,
        "w_height_floor": 1050.0,
        "w_upright": 620.0,
        "w_support": 2100.0,
        "w_zmp": 1500.0,
        "w_slip": 1100.0,
        "w_contact": 260.0,
        "w_downward": 145.0,
        "w_qfrc": 2.0,
        "w_smooth": 1.7,
    }


def candidate_grid(limit: int) -> list[dict[str, Any]]:
    common = make_common()
    rows: list[dict[str, Any]] = []
    grid = itertools.product(
        [0.0826, 0.0828, 0.0830, 0.0832],
        [0.531, 0.532, 0.533],
        [0.0678, 0.0682, 0.0686],
        [3.44, 3.50, 3.56],
        [2.12, 2.20, 2.28],
    )
    for drop, max_blend, residual, descend_s, return_s in grid:
        rows.append({
            **common,
            "attempt": f"horizon-d{drop:.4f}-b{max_blend:.3f}-r{residual:.4f}-td{descend_s:.2f}-tr{return_s:.2f}".replace(".", "p"),
            "drop": drop,
            "max_blend": max_blend,
            "residual_scale": residual,
            "joint_kp": 25.5,
            "torque_clip": 37.0,
            "descend_s": descend_s,
            "return_s": return_s,
        })

    # Pre-sort around the exp68 cliff: enough depth pressure for 7cm, but biased
    # toward slower return and lower blend to preserve terminal standing.
    def prior_score(row: dict[str, Any]) -> float:
        return (
            150.0 * abs(row["drop"] - 0.0830)
            + 80.0 * abs(row["max_blend"] - 0.532)
            + 100.0 * abs(row["residual_scale"] - 0.0682)
            + 1.4 * abs(row["descend_s"] - 3.50)
            + 1.0 * abs(row["return_s"] - 2.20)
        )

    rows.sort(key=prior_score)
    return rows[:limit]


def write_summary(result: dict[str, Any], out_dir: Path) -> None:
    lines = [
        "# G1 Terminal Stand Horizon Optimizer Summary",
        "",
        "| Attempt | Score | 8cm | 7cm | Verdict | Drop | Contact | Slip | CoM min | ZMP min | qfrc | Final h | Fell |",
        "|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for run in sorted(result["runs"], key=lambda item: item["terminal_stand_score"]):
        fell = "never" if run["fell_at"] is None else f"{run['fell_at']:.2f}s"
        gate8 = "PASS" if run["visible_8cm_gate"] else "FAIL"
        gate7 = "PASS" if run["recoverable_7cm_gate"] else "FAIL"
        lines.append(
            f"| {run['attempt']} | {run['terminal_stand_score']:.2f} | {gate8} | {gate7} | "
            f"{run['transition_verdict']} | {run['visible_drop']:.4f}m | "
            f"{run['foot_contact_ratio']:.2f} | {run['foot_slip_distance']:.3f}m | "
            f"{run['min_support_margin']:.4f}m | {run['min_zmp_margin']:.4f}m | "
            f"{run['max_qfrc_applied']:.1f} | {run['final_height']:.4f}m | {fell} |"
        )
    lines.extend([
        "",
        f"Best terminal plan: {result['best_terminal_plan']}",
        f"Best recoverable run: {result['best_recoverable']}",
        f"Best no-fall run: {result['best_no_fall']}",
        f"Best depth run: {result['best_depth']}",
        "",
        "M19 closes only after the exp29 visible 8cm native gate and browser replay both pass.",
    ])
    (out_dir / "terminal-stand-horizon-optimizer-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=6.0)
    parser.add_argument("--limit", type=int, default=12)
    args = parser.parse_args()
    out_dir = VERIFY / "terminal-stand-horizon-optimizer"
    out_dir.mkdir(parents=True, exist_ok=True)
    result = {
        "evaluation_seconds": args.seconds,
        "candidate_limit": args.limit,
        "planning_gate": {
            "team_validation_mode": "manual-pass",
            "spec_delta": "M19 tests a full-rollout terminal stand objective over multi-step CoM/ZMP trajectory plans rather than another hand-picked parameter sweep.",
            "perspectives": {
                "product": "directly targets the 7cm recoverable gate that blocks a visible G1 squat",
                "architecture": "keeps exp67 qfrc WBC selector as actuator layer and adds a terminal objective over the plan horizon",
                "security": "local MuJoCo/JAX run only; no credentials or external writes",
                "qa": "raw JSON per candidate plus sorted terminal objective summary",
                "skeptic": "still a discrete black-box optimizer, not a real-time continuous MPC solver",
            },
            "dod": [
                "candidate plans are generated programmatically",
                "each candidate is evaluated by native MuJoCo rollout",
                "summary reports terminal stand score, recoverable 7cm gate, and visible 8cm gate",
            ],
        },
        "sources": [
            {
                "url": "https://www.unitree.com/g1",
                "accessed": "2026-06-18",
                "note": "G1 is advertised with large joint movement angle space and imitation/RL-driven motion.",
            },
            {
                "url": "https://support.unitree.com/home/en/G1_developer",
                "accessed": "2026-06-18",
                "note": "G1 developer guide describes six degrees of freedom per leg and waist DOF.",
            },
            {
                "url": "https://www.mdpi.com/1424-8220/25/2/435",
                "accessed": "2026-06-18",
                "note": "Humanoid squat can be formulated as TP-MPC trajectory optimization plus WBC tracking.",
            },
            {
                "url": "https://arxiv.org/html/2505.19540v1",
                "accessed": "2026-06-18",
                "note": "Real-time whole-body MPC uses ZMP/contact constraints over a horizon for bipedal robots.",
            },
            {
                "url": "https://underactuated.mit.edu/humanoids.html",
                "accessed": "2026-06-18",
                "note": "ZMP/CoM framing connects humanoid balance to support-constrained CoM trajectory generation.",
            },
        ],
        "runs": [],
    }
    for variant in candidate_grid(args.limit):
        run = EXP67.native_eval(
            variant=variant,
            seconds=args.seconds,
            out_dir=out_dir / variant["attempt"],
        )
        result["runs"].append(annotate(run))

    recoverable = [run for run in result["runs"] if run["recoverable_7cm_gate"]]
    no_fall = [run for run in result["runs"] if run["fell_at"] is None]
    best_terminal = min(result["runs"], key=lambda run: run["terminal_stand_score"])
    best_recoverable = max(recoverable, key=lambda run: run["visible_drop"], default=None)
    best_no_fall = max(no_fall, key=lambda run: run["visible_drop"], default=None)
    best_depth = max(result["runs"], key=lambda run: run["visible_drop"])
    result["best_terminal_plan"] = {
        "attempt": best_terminal["attempt"],
        "terminal_stand_score": best_terminal["terminal_stand_score"],
        "visible_drop": best_terminal["visible_drop"],
        "final_height": best_terminal["final_height"],
        "transition_verdict": best_terminal["transition_verdict"],
    }
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
        "best_terminal_plan": result["best_terminal_plan"],
        "best_recoverable": result["best_recoverable"],
        "best_no_fall": result["best_no_fall"],
        "best_depth": result["best_depth"],
    }, indent=2), flush=True)


if __name__ == "__main__":
    main()
