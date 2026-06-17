"""Probe pose-aware selector costs for the G1 visible squat gate."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any

import mujoco
import numpy as np


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
ORIGINAL_SCORE_CANDIDATE = EXP71.EXP67.score_candidate
ORIGINAL_BUILD_TARGET = EXP71.EXP62.build_target


def qpos_index(model: mujoco.MjModel, joint_name: str) -> int:
    return int(model.jnt_qposadr[model.joint(joint_name).id])


def pose_metrics(model: mujoco.MjModel, cand: mujoco.MjData) -> dict[str, float]:
    start = model.keyframe("knees_bent").qpos
    left_knee = qpos_index(model, "left_knee_joint")
    right_knee = qpos_index(model, "right_knee_joint")
    left_hip = qpos_index(model, "left_hip_pitch_joint")
    right_hip = qpos_index(model, "right_hip_pitch_joint")
    knee_delta = max(
        abs(float(cand.qpos[left_knee] - start[left_knee])),
        abs(float(cand.qpos[right_knee] - start[right_knee])),
    )
    hip_delta = max(
        abs(float(cand.qpos[left_hip] - start[left_hip])),
        abs(float(cand.qpos[right_hip] - start[right_hip])),
    )
    return {"knee_delta": knee_delta, "hip_delta": hip_delta}


def pose_aware_score_candidate(*args, **kwargs):
    cost, terms = ORIGINAL_SCORE_CANDIDATE(*args, **kwargs)
    model = kwargs["model"]
    cand = kwargs["cand"]
    variant = kwargs["variant"]
    pose = pose_metrics(model, cand)
    knee_target = variant.get("selector_knee_target", 0.60)
    hip_target = variant.get("selector_hip_target", 0.35)
    knee_progress = min(pose["knee_delta"], knee_target) / knee_target
    hip_progress = min(pose["hip_delta"], hip_target) / hip_target
    # Negative terms are deliberate: this is a selector reward added to the
    # existing support/ZMP/slip costs, not a raw target offset.
    terms = dict(terms)
    terms["pose_knee_reward"] = -variant.get("w_pose_knee", 0.0) * knee_progress * knee_progress
    terms["pose_hip_reward"] = -variant.get("w_pose_hip", 0.0) * hip_progress * hip_progress
    terms["pose_balance_penalty"] = variant.get("w_pose_balance", 0.0) * max(0.0, knee_progress - hip_progress - 0.20) ** 2
    return float(cost + terms["pose_knee_reward"] + terms["pose_hip_reward"] + terms["pose_balance_penalty"]), terms


ACTIVE_HIP_BIAS = 0.0


def hip_micro_bias_target(*args, **kwargs):
    ik_target = np.asarray(kwargs["ik_target"], dtype=np.float64).copy()
    if ACTIVE_HIP_BIAS:
        ik_target[0] -= ACTIVE_HIP_BIAS
        ik_target[6] -= ACTIVE_HIP_BIAS
    kwargs["ik_target"] = ik_target
    return ORIGINAL_BUILD_TARGET(*args, **kwargs)


EXP71.EXP67.score_candidate = pose_aware_score_candidate
EXP71.EXP62.build_target = hip_micro_bias_target


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
        "drop": 0.092,
        "max_blend": 0.546,
        "residual_scale": 0.0682,
        "joint_kp": 26.0,
        "joint_kd": 1.2,
        "torque_clip": 38.0,
        "descend_s": 3.50,
        "return_s": 1.15,
        "slow_release": 0.090,
        "fast_release": 0.180,
        "recapture_trigger_drop": 0.0660,
        "recapture_hold_s": 0.16,
        "recapture_support_floor": 0.010,
        "recapture_zmp_floor": -0.018,
        "recapture_error_gain": 2.7,
        "w_support": 2850.0,
        "w_zmp": 2250.0,
        "w_slip": 1450.0,
        "selector_knee_target": 0.60,
        "selector_hip_target": 0.35,
    }


def variants() -> list[dict[str, Any]]:
    base = base_variant()
    rows: list[dict[str, Any]] = []
    for hip_bias in [0.00, 0.02]:
        for w_knee in [0.02, 0.05, 0.08, 0.12, 0.18]:
            for w_hip in [0.00, 0.02, 0.05]:
                if w_hip == 0.05 and hip_bias == 0.02 and w_knee >= 0.12:
                    continue
                rows.append({
                    **base,
                    "attempt": (
                        f"pose-hb{hip_bias:.2f}-wk{w_knee:.2f}-wh{w_hip:.2f}"
                    ).replace(".", "p"),
                    "hip_micro_bias": hip_bias,
                    "w_pose_knee": w_knee,
                    "w_pose_hip": w_hip,
                    "w_pose_balance": 0.04,
                })
    rows.sort(key=lambda row: (
        abs(row["w_pose_knee"] - 0.08),
        abs(row["hip_micro_bias"] - 0.02),
        abs(row["w_pose_hip"] - 0.02),
    ))
    return rows[:24]


def run_variant(variant: dict[str, Any], seconds: float, out_dir: Path) -> dict[str, Any]:
    global ACTIVE_HIP_BIAS
    ACTIVE_HIP_BIAS = variant["hip_micro_bias"]
    run = EXP71.native_eval_event(
        variant=variant,
        seconds=seconds,
        out_dir=out_dir / variant["attempt"],
    )
    return annotate(run)


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
        "# G1 Pose-Aware Selector Summary",
        "",
        "| Attempt | 8cm | 7cm | Verdict | Drop | Knee | Hip | Contact | Slip | CoM min | ZMP min | Final h | Fell | Weights hb/k/h | Gap d/k/h |",
        "|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|",
    ]
    for run in sorted(result["runs"], key=run_score):
        fell = "never" if run["fell_at"] is None else f"{run['fell_at']:.2f}s"
        gate8 = "PASS" if run["visible_8cm_gate"] else "FAIL"
        gate7 = "PASS" if run["recoverable_7cm_gate"] else "FAIL"
        gap = run["visible_gap"]
        variant = run["variant"]
        lines.append(
            f"| {run['attempt']} | {gate8} | {gate7} | {run['transition_verdict']} | "
            f"{run['visible_drop']:.4f}m | {run['max_knee_delta_rad']:.3f} | "
            f"{run['max_hip_pitch_delta_rad']:.3f} | {run['foot_contact_ratio']:.2f} | "
            f"{run['foot_slip_distance']:.3f}m | {run['min_support_margin']:.4f}m | "
            f"{run['min_zmp_margin']:.4f}m | {run['final_height']:.4f}m | {fell} | "
            f"{variant['hip_micro_bias']:.2f}/{variant['w_pose_knee']:.2f}/{variant['w_pose_hip']:.2f} | "
            f"{gap['drop_shortfall_m']:.4f}/{gap['knee_shortfall_rad']:.3f}/{gap['hip_shortfall_rad']:.3f} |"
        )
    lines.extend([
        "",
        f"Best visible run: {result['best_visible']}",
        f"Best recoverable run: {result['best_recoverable']}",
        f"Best no-fall run: {result['best_no_fall']}",
        f"Best depth run: {result['best_depth']}",
    ])
    (out_dir / "pose-aware-selector-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=7.0)
    args = parser.parse_args()
    out_dir = VERIFY / "pose-aware-selector"
    out_dir.mkdir(parents=True, exist_ok=True)
    result: dict[str, Any] = {
        "evaluation_seconds": args.seconds,
        "planning_gate": {
            "team_validation_mode": "manual-pass",
            "spec_delta": "M19 tests achieved-pose rewards inside the one-step WBC selector while preserving support/ZMP/slip costs.",
            "perspectives": {
                "product": "directly targets the remaining knee-flexion visible-gate gap",
                "architecture": "patches selector scoring rather than raw knee target offsets",
                "security": "local MuJoCo/JAX only",
                "qa": "native raw JSON per candidate plus visible 8cm, knee/hip, support, slip, return gates",
                "skeptic": "pose reward may choose candidates that look good one step ahead but collapse later",
            },
            "dod": [
                "run pose-aware selector candidates around exp74 best timing",
                "report whether achieved-pose scoring closes knee gap without losing recovery",
            ],
        },
        "sources": [
            {
                "url": "https://www.lirmm.fr/krut/pdf/2014_galdeano_ssd-0568454426/2014_galdeano_ssd.pdf",
                "accessed": "2026-06-18",
                "note": "Task-based WBC combines feet pose, CoM/ZMP regulation, and joint objective handling.",
            },
            {
                "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC11769464/",
                "accessed": "2026-06-18",
                "note": "Humanoid squat control is framed as trajectory optimization plus WBC tracking.",
            },
            {
                "url": "https://arxiv.org/html/2502.17219v1",
                "accessed": "2026-06-18",
                "note": "ZMP inside the support polygon is used as a dynamic balance condition in humanoid WBC.",
            },
            {
                "url": "https://www.roboticsproceedings.org/rss21/p070.pdf",
                "accessed": "2026-06-18",
                "note": "Recent humanoid G1 work uses knee-flexion terms for squatting-to-height behavior, motivating achieved-pose scoring instead of raw offsets.",
            },
        ],
        "runs": [],
    }
    for variant in variants():
        result["runs"].append(run_variant(variant, args.seconds, out_dir))
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
