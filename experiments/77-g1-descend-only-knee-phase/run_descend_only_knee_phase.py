"""Probe descend-only knee shaping for the G1 visible squat gate."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any

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
ORIGINAL_BUILD_TARGET = EXP71.EXP62.build_target
ORIGINAL_CHOOSE_BLEND = EXP71.EXP67.choose_blend

ACTIVE_MICRO: dict[str, float] = {}
ACTIVE_DESCEND_FRACTION = 0.0
ACTIVE_RETURN_PHASE = 0.0


def ramp(lo: float, hi: float, x: float) -> float:
    if hi <= lo:
        return 1.0 if x >= hi else 0.0
    return float(np.clip((x - lo) / (hi - lo), 0.0, 1.0))


def micro_window(phase: float, start: float, peak: float, end: float) -> float:
    return ramp(start, peak, phase) * (1.0 - ramp(peak, end, phase))


def descend_only_choose_blend(*args, **kwargs):
    global ACTIVE_DESCEND_FRACTION, ACTIVE_RETURN_PHASE
    ACTIVE_RETURN_PHASE = float(kwargs["return_phase"])
    ACTIVE_DESCEND_FRACTION = float(kwargs["desired_fraction"]) if ACTIVE_RETURN_PHASE <= 0.0 else 0.0
    return ORIGINAL_CHOOSE_BLEND(*args, **kwargs)


def descend_only_target(*args, **kwargs):
    ik_target = np.asarray(kwargs["ik_target"], dtype=np.float64).copy()
    if ACTIVE_MICRO and ACTIVE_DESCEND_FRACTION > 0.0:
        health = min(
            float(kwargs["support_health"]),
            float(kwargs["zmp_health"]),
            float(kwargs["slip_health"]),
        )
        window = micro_window(
            ACTIVE_DESCEND_FRACTION,
            ACTIVE_MICRO["phase_start"],
            ACTIVE_MICRO["phase_peak"],
            ACTIVE_MICRO["phase_end"],
        )
        if ACTIVE_MICRO["return_cutoff"] and ACTIVE_RETURN_PHASE > 0.0:
            window = 0.0
        scale = window * health if health >= ACTIVE_MICRO["min_health"] else 0.0
        ik_target[3] += ACTIVE_MICRO["knee_amp"] * scale
        ik_target[9] += ACTIVE_MICRO["knee_amp"] * scale
        ik_target[0] -= ACTIVE_MICRO["hip_bias"] * scale
        ik_target[6] -= ACTIVE_MICRO["hip_bias"] * scale
    kwargs["ik_target"] = ik_target
    return ORIGINAL_BUILD_TARGET(*args, **kwargs)


EXP71.EXP67.choose_blend = descend_only_choose_blend
EXP71.EXP62.build_target = descend_only_target


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
    }


def variants() -> list[dict[str, Any]]:
    base = base_variant()
    rows: list[dict[str, Any]] = []
    for knee_amp in [0.08, 0.10, 0.11, 0.12, 0.14]:
        for hip_bias in [0.02, 0.03, 0.04]:
            for window in [(0.45, 0.65, 0.85), (0.55, 0.75, 0.95)]:
                for min_health in [0.65, 0.75, 0.85]:
                    if knee_amp >= 0.12 and min_health < 0.75:
                        continue
                    phase_start, phase_peak, phase_end = window
                    rows.append({
                        **base,
                        "attempt": (
                            f"desc-k{knee_amp:.2f}-h{hip_bias:.2f}-"
                            f"p{phase_start:.2f}-{phase_peak:.2f}-{phase_end:.2f}-"
                            f"mh{min_health:.2f}"
                        ).replace(".", "p"),
                        "knee_amp": knee_amp,
                        "hip_bias": hip_bias,
                        "phase_start": phase_start,
                        "phase_peak": phase_peak,
                        "phase_end": phase_end,
                        "min_health": min_health,
                        "return_cutoff": True,
                    })
    rows.sort(key=lambda row: (
        abs(row["knee_amp"] - 0.11),
        abs(row["hip_bias"] - 0.03),
        abs(row["min_health"] - 0.80),
        abs(row["phase_peak"] - 0.75),
    ))
    return rows[:30]


def run_variant(variant: dict[str, Any], seconds: float, out_dir: Path) -> dict[str, Any]:
    global ACTIVE_MICRO
    ACTIVE_MICRO = {
        "knee_amp": variant["knee_amp"],
        "hip_bias": variant["hip_bias"],
        "phase_start": variant["phase_start"],
        "phase_peak": variant["phase_peak"],
        "phase_end": variant["phase_end"],
        "min_health": variant["min_health"],
        "return_cutoff": variant["return_cutoff"],
    }
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
        "# G1 Descend-Only Knee Phase Summary",
        "",
        "| Attempt | 8cm | 7cm | Verdict | Drop | Knee | Hip | Contact | Slip | CoM min | ZMP min | Final h | Fell | k/h/window/min-health | Gap d/k/h |",
        "|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|",
    ]
    for run in sorted(result["runs"], key=run_score):
        fell = "never" if run["fell_at"] is None else f"{run['fell_at']:.2f}s"
        gate8 = "PASS" if run["visible_8cm_gate"] else "FAIL"
        gate7 = "PASS" if run["recoverable_7cm_gate"] else "FAIL"
        gap = run["visible_gap"]
        v = run["variant"]
        lines.append(
            f"| {run['attempt']} | {gate8} | {gate7} | {run['transition_verdict']} | "
            f"{run['visible_drop']:.4f}m | {run['max_knee_delta_rad']:.3f} | "
            f"{run['max_hip_pitch_delta_rad']:.3f} | {run['foot_contact_ratio']:.2f} | "
            f"{run['foot_slip_distance']:.3f}m | {run['min_support_margin']:.4f}m | "
            f"{run['min_zmp_margin']:.4f}m | {run['final_height']:.4f}m | {fell} | "
            f"{v['knee_amp']:.2f}/{v['hip_bias']:.2f}/"
            f"{v['phase_start']:.2f}-{v['phase_peak']:.2f}-{v['phase_end']:.2f}/"
            f"{v['min_health']:.2f} | "
            f"{gap['drop_shortfall_m']:.4f}/{gap['knee_shortfall_rad']:.3f}/{gap['hip_shortfall_rad']:.3f} |"
        )
    lines.extend([
        "",
        f"Best visible run: {result['best_visible']}",
        f"Best recoverable run: {result['best_recoverable']}",
        f"Best no-fall run: {result['best_no_fall']}",
        f"Best depth run: {result['best_depth']}",
    ])
    (out_dir / "descend-only-knee-phase-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=7.0)
    args = parser.parse_args()
    out_dir = VERIFY / "descend-only-knee-phase"
    out_dir.mkdir(parents=True, exist_ok=True)
    result: dict[str, Any] = {
        "evaluation_seconds": args.seconds,
        "planning_gate": {
            "team_validation_mode": "manual-pass",
            "spec_delta": "M19 separates knee-flexion shaping from the return phase instead of patching build_target symmetrically.",
            "perspectives": {
                "product": "tests the current ROADMAP next step: descend-only custom phase logic before browser replay",
                "architecture": "wraps choose_blend to expose return_phase to the target patch while preserving exp71 gates",
                "security": "local MuJoCo/JAX execution only",
                "qa": "native JSON per candidate plus visible 8cm, knee/hip, contact, slip, return gates",
                "skeptic": "this is still a heuristic target family; a true trajectory optimizer may still be required",
            },
            "dod": [
                "run return-cutoff knee/hip micro-target candidates around the exp76 knee/fall boundary",
                "report whether return-phase cutoff improves stable knee flexion beyond 0.516rad",
            ],
        },
        "sources": [
            {
                "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC11769464/",
                "accessed": "2026-06-18",
                "note": "Humanoid squatting requires trajectory optimization and whole-body control, not an isolated knee target.",
            },
            {
                "url": "https://www.lirmm.fr/krut/pdf/2014_galdeano_ssd-0568454426/2014_galdeano_ssd.pdf",
                "accessed": "2026-06-18",
                "note": "Squat-like humanoid motion uses CoM, feet pose, ZMP regulation, and joint-limit handling together.",
            },
            {
                "url": "https://arxiv.org/html/2502.13013v1",
                "accessed": "2026-06-18",
                "note": "G1-class loco-manipulation work reports squatting to specific heights via height tracking and curriculum.",
            },
            {
                "url": "https://underactuated.mit.edu/humanoids.html",
                "accessed": "2026-06-18",
                "note": "Humanoid motion planning commonly reasons about CoM vertical motion and angular momentum.",
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
        "max_knee_delta_rad": best_visible["max_knee_delta_rad"],
        "max_hip_pitch_delta_rad": best_visible["max_hip_pitch_delta_rad"],
    }
    result["best_recoverable"] = None if best_recoverable is None else {
        "attempt": best_recoverable["attempt"],
        "visible_drop": best_recoverable["visible_drop"],
        "max_knee_delta_rad": best_recoverable["max_knee_delta_rad"],
        "max_hip_pitch_delta_rad": best_recoverable["max_hip_pitch_delta_rad"],
        "transition_verdict": best_recoverable["transition_verdict"],
        "visible_gap": best_recoverable["visible_gap"],
    }
    result["best_no_fall"] = None if best_no_fall is None else {
        "attempt": best_no_fall["attempt"],
        "visible_drop": best_no_fall["visible_drop"],
        "max_knee_delta_rad": best_no_fall["max_knee_delta_rad"],
        "max_hip_pitch_delta_rad": best_no_fall["max_hip_pitch_delta_rad"],
        "transition_verdict": best_no_fall["transition_verdict"],
        "visible_gap": best_no_fall["visible_gap"],
        "final_height": best_no_fall["final_height"],
    }
    result["best_depth"] = {
        "attempt": best_depth["attempt"],
        "visible_drop": best_depth["visible_drop"],
        "max_knee_delta_rad": best_depth["max_knee_delta_rad"],
        "max_hip_pitch_delta_rad": best_depth["max_hip_pitch_delta_rad"],
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
