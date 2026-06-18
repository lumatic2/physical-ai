"""Probe visible-squat WBC guard variants with explicit stance-foot forces."""

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
    spec = importlib.util.spec_from_file_location("exp67_qfrc_wbc", EXP67_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {EXP67_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EXP67 = load_exp67()


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


def annotate_visible(run: dict[str, Any]) -> dict[str, Any]:
    run["visible_8cm_gate"] = visible_8cm_gate(run)
    run["visible_gap"] = visible_gap(run)
    if run["visible_8cm_gate"]:
        run["visible_verdict"] = "PASS_VISIBLE_8CM_GATE"
    elif run["fell_at"] is not None:
        run["visible_verdict"] = "FAIL_FALL"
    elif run["visible_drop"] < 0.08:
        run["visible_verdict"] = "DEPTH_PENDING_8CM"
    elif run["max_knee_delta_rad"] < 0.60 or run["max_hip_pitch_delta_rad"] < 0.35:
        run["visible_verdict"] = "POSE_GATE_PENDING"
    elif not run["return_to_stand"]:
        run["visible_verdict"] = "RETURN_PENDING"
    elif run["foot_contact_ratio"] < 0.90:
        run["visible_verdict"] = "CONTACT_PENDING"
    elif run["foot_slip_distance"] > 0.08:
        run["visible_verdict"] = "STANCE_SLIP_PENDING"
    else:
        run["visible_verdict"] = "GATE_PENDING"
    return run


def variants() -> list[dict[str, Any]]:
    common = {
        "policy_weight": 1.0,
        "joint_kd": 1.4,
        "foot_kd_xy": 22.0,
        "foot_lift_force": 180.0,
        "support_floor": 0.012,
        "zmp_floor": -0.015,
        "slip_floor": 0.045,
        "downward_floor": 0.10,
        "stand_height": 0.74,
        "height_floor": 0.63,
        "upright_floor": 0.84,
        "qfrc_soft_cap": 55.0,
        "return_safety_boost": 0.20,
        "return_min_safety": 0.55,
        "descend_rate": 0.030,
        "slow_release": 0.030,
        "fast_release": 0.080,
        "small_hold": 0.010,
        "w_height": 105.0,
        "w_stand": 160.0,
        "w_height_floor": 980.0,
        "w_upright": 700.0,
        "w_support": 5200.0,
        "w_zmp": 3800.0,
        "w_slip": 3600.0,
        "w_contact": 560.0,
        "w_downward": 180.0,
        "w_qfrc": 6.0,
        "w_smooth": 2.0,
    }
    return [
        {
            **common,
            "attempt": "visible-8cm-stance-force",
            "drop": 0.080,
            "max_blend": 0.56,
            "residual_scale": 0.070,
            "joint_kp": 24.0,
            "torque_clip": 34.0,
            "foot_kp_xy": 260.0,
            "foot_force_clip": 220.0,
            "descend_s": 4.2,
            "return_s": 2.0,
        },
        {
            **common,
            "attempt": "visible-8p2cm-stance-force",
            "drop": 0.082,
            "max_blend": 0.57,
            "residual_scale": 0.072,
            "joint_kp": 25.0,
            "torque_clip": 36.0,
            "foot_kp_xy": 320.0,
            "foot_force_clip": 260.0,
            "descend_s": 4.4,
            "return_s": 2.1,
        },
        {
            **common,
            "attempt": "visible-8cm-slow-guard",
            "drop": 0.080,
            "max_blend": 0.54,
            "residual_scale": 0.066,
            "joint_kp": 24.0,
            "torque_clip": 32.0,
            "foot_kp_xy": 360.0,
            "foot_force_clip": 240.0,
            "descend_s": 5.0,
            "return_s": 2.2,
            "w_height": 80.0,
            "w_support": 7000.0,
            "w_slip": 5200.0,
        },
        {
            **common,
            "attempt": "visible-8p5cm-depth-biased-guard",
            "drop": 0.085,
            "max_blend": 0.59,
            "residual_scale": 0.076,
            "joint_kp": 26.0,
            "torque_clip": 40.0,
            "foot_kp_xy": 320.0,
            "foot_force_clip": 300.0,
            "descend_s": 4.5,
            "return_s": 2.0,
            "w_height": 150.0,
            "w_stand": 110.0,
        },
    ]


def write_summary(result: dict[str, Any], out_dir: Path) -> None:
    lines = [
        "# G1 Visible Stance WBC Guard Summary",
        "",
        "| Attempt | Visible gate | Verdict | Drop | Knee | Hip | Contact | Slip | Support min | ZMP min | Final h | Fell |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for run in result["runs"]:
        fell = "never" if run["fell_at"] is None else f"{run['fell_at']:.2f}s"
        gate = "PASS" if run["visible_8cm_gate"] else "FAIL"
        lines.append(
            f"| {run['attempt']} | {gate} | {run['visible_verdict']} | "
            f"{run['visible_drop']:.4f}m | {run['max_knee_delta_rad']:.3f} | "
            f"{run['max_hip_pitch_delta_rad']:.3f} | {run['foot_contact_ratio']:.2f} | "
            f"{run['foot_slip_distance']:.3f}m | {run['min_support_margin']:.4f}m | "
            f"{run['min_zmp_margin']:.4f}m | {run['final_height']:.4f}m | {fell} |"
        )
    lines.extend([
        "",
        f"Best visible run: {result['best_visible']}",
        f"Best no-fall run: {result['best_no_fall']}",
        f"Best depth run: {result['best_depth']}",
        "",
        "M19 closes only when visible native and browser replay both pass.",
    ])
    (out_dir / "visible-stance-wbc-guard-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=6.0)
    args = parser.parse_args()
    out_dir = VERIFY / "visible-stance-wbc-guard"
    out_dir.mkdir(parents=True, exist_ok=True)
    result = {
        "evaluation_seconds": args.seconds,
        "planning_gate": {
            "team_validation_mode": "manual-pass",
            "spec_delta": "M19 now tests explicit stance-foot qfrc/WBC guard variants against the exp29 visible gate.",
            "perspectives": {
                "product": "targets exp81's remaining blocker: reward-only training cannot keep stance feet anchored",
                "architecture": "reuses exp67 WBC-lite candidate rollout and adds stricter 8cm visible-gate annotation",
                "security": "no credentials or external side effects",
                "qa": "native sweep records raw JSON with drop, knee, hip, contact, slip, support, ZMP, return, and fall",
                "skeptic": "Jacobian-transpose stance force can overconstrain the model and convert slip into fall or shallow depth",
            },
            "dod": [
                "raw native JSON per WBC guard variant",
                "summary states whether any variant passes visible_8cm_gate",
            ],
        },
        "sources": [
            {
                "url": "https://www.mdpi.com/1424-8220/25/2/435",
                "accessed": "2026-06-18",
                "note": "Humanoid squat control combines optimized trajectory planning with WBC tracking.",
            },
            {
                "url": "https://arxiv.org/html/2312.16465v4",
                "accessed": "2026-06-18",
                "note": "Multi-contact WBC motivates posture correction under contact constraints.",
            },
            {
                "url": "https://mujoco.readthedocs.io/en/3.4.0/computation/",
                "accessed": "2026-06-18",
                "note": "MuJoCo contact/inverse dynamics notes caution that contact force constraints cannot be inferred from kinematics alone.",
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
        result["runs"].append(annotate_visible(run))

    visible = [run for run in result["runs"] if run["visible_8cm_gate"]]
    no_fall = [run for run in result["runs"] if run["fell_at"] is None]
    best_visible = max(visible, key=lambda run: run["visible_drop"], default=None)
    best_no_fall = max(no_fall, key=lambda run: run["visible_drop"], default=None)
    best_depth = max(result["runs"], key=lambda run: run["visible_drop"])
    result["best_visible"] = None if best_visible is None else {
        "attempt": best_visible["attempt"],
        "visible_drop": best_visible["visible_drop"],
        "max_knee_delta_rad": best_visible["max_knee_delta_rad"],
        "max_hip_pitch_delta_rad": best_visible["max_hip_pitch_delta_rad"],
    }
    result["best_no_fall"] = None if best_no_fall is None else {
        "attempt": best_no_fall["attempt"],
        "visible_drop": best_no_fall["visible_drop"],
        "max_knee_delta_rad": best_no_fall["max_knee_delta_rad"],
        "max_hip_pitch_delta_rad": best_no_fall["max_hip_pitch_delta_rad"],
        "visible_gap": best_no_fall["visible_gap"],
        "visible_verdict": best_no_fall["visible_verdict"],
    }
    result["best_depth"] = {
        "attempt": best_depth["attempt"],
        "visible_drop": best_depth["visible_drop"],
        "fell_at": best_depth["fell_at"],
        "visible_verdict": best_depth["visible_verdict"],
    }
    result["verdict"] = "PASS_VISIBLE_8CM_GATE" if visible else "FAIL_VISIBLE_8CM_GATE"
    write_summary(result, out_dir)
    (out_dir / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(result["verdict"], json.dumps({
        "best_visible": result["best_visible"],
        "best_no_fall": result["best_no_fall"],
        "best_depth": result["best_depth"],
    }, indent=2), flush=True)


if __name__ == "__main__":
    main()
