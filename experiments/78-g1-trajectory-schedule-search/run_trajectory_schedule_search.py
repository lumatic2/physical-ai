"""Search MPC-style squat schedules for the G1 visible gate."""

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

ACTIVE_PROFILE: dict[str, float] = {}
ACTIVE_PROFILE_FRACTION = 0.0
ACTIVE_RETURN_PHASE = 0.0


def ramp(lo: float, hi: float, x: float) -> float:
    if hi <= lo:
        return 1.0 if x >= hi else 0.0
    return float(np.clip((x - lo) / (hi - lo), 0.0, 1.0))


def bell_window(x: float, start: float, peak: float, end: float) -> float:
    return ramp(start, peak, x) * (1.0 - ramp(peak, end, x))


def scheduled_fraction(desired_fraction: float, return_phase: float, profile: dict[str, float]) -> float:
    if return_phase <= 0.0:
        x = float(np.clip(desired_fraction, 0.0, 1.0))
        return float(np.clip(x ** profile["descend_gamma"], 0.0, 1.0))
    release = float(np.clip(1.0 - return_phase, 0.0, 1.0))
    return float(np.clip(release ** profile["return_gamma"], 0.0, 1.0))


def scheduled_choose_blend(*args, **kwargs):
    global ACTIVE_PROFILE_FRACTION, ACTIVE_RETURN_PHASE
    ACTIVE_RETURN_PHASE = float(kwargs["return_phase"])
    ACTIVE_PROFILE_FRACTION = scheduled_fraction(
        float(kwargs["desired_fraction"]),
        ACTIVE_RETURN_PHASE,
        ACTIVE_PROFILE,
    )
    kwargs["desired_fraction"] = ACTIVE_PROFILE_FRACTION
    return ORIGINAL_CHOOSE_BLEND(*args, **kwargs)


def scheduled_target(*args, **kwargs):
    ik_target = np.asarray(kwargs["ik_target"], dtype=np.float64).copy()
    if ACTIVE_PROFILE:
        health = min(
            float(kwargs["support_health"]),
            float(kwargs["zmp_health"]),
            float(kwargs["slip_health"]),
        )
        if health >= ACTIVE_PROFILE["min_health"]:
            pose_phase = ACTIVE_PROFILE_FRACTION
            if ACTIVE_RETURN_PHASE > 0.0:
                pose_phase *= ACTIVE_PROFILE["return_pose_scale"]
            window = bell_window(
                pose_phase,
                ACTIVE_PROFILE["pose_start"],
                ACTIVE_PROFILE["pose_peak"],
                ACTIVE_PROFILE["pose_end"],
            )
            scale = window * health
            ik_target[3] += ACTIVE_PROFILE["knee_amp"] * scale
            ik_target[9] += ACTIVE_PROFILE["knee_amp"] * scale
            ik_target[0] -= ACTIVE_PROFILE["hip_bias"] * scale
            ik_target[6] -= ACTIVE_PROFILE["hip_bias"] * scale
    kwargs["ik_target"] = ik_target
    return ORIGINAL_BUILD_TARGET(*args, **kwargs)


EXP71.EXP67.choose_blend = scheduled_choose_blend
EXP71.EXP62.build_target = scheduled_target


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
        "drop": 0.096,
        "max_blend": 0.552,
        "residual_scale": 0.0682,
        "joint_kp": 26.0,
        "joint_kd": 1.2,
        "torque_clip": 38.0,
        "descend_s": 3.65,
        "return_s": 1.25,
        "slow_release": 0.085,
        "fast_release": 0.165,
        "recapture_trigger_drop": 0.0680,
        "recapture_hold_s": 0.18,
        "recapture_support_floor": 0.010,
        "recapture_zmp_floor": -0.018,
        "recapture_error_gain": 2.8,
        "w_support": 3000.0,
        "w_zmp": 2450.0,
        "w_slip": 1500.0,
    }


def variants() -> list[dict[str, Any]]:
    base = base_variant()
    rows: list[dict[str, Any]] = []
    profiles = [
        # drop, blend, trigger, hold, return_s, descend_gamma, return_gamma, knee, hip, pose window, health, return_pose
        (0.094, 0.548, 0.066, 0.16, 1.20, 0.85, 1.25, 0.08, 0.03, (0.42, 0.62, 0.88), 0.75, 0.15),
        (0.096, 0.550, 0.068, 0.18, 1.25, 0.80, 1.35, 0.10, 0.03, (0.42, 0.64, 0.90), 0.80, 0.10),
        (0.098, 0.552, 0.070, 0.18, 1.30, 0.75, 1.45, 0.11, 0.04, (0.45, 0.66, 0.90), 0.85, 0.05),
        (0.100, 0.554, 0.070, 0.20, 1.35, 0.72, 1.55, 0.12, 0.04, (0.48, 0.70, 0.94), 0.85, 0.05),
        (0.092, 0.546, 0.066, 0.16, 1.20, 0.90, 1.20, 0.10, 0.03, (0.55, 0.75, 0.95), 0.80, 0.00),
        (0.096, 0.550, 0.066, 0.22, 1.40, 0.78, 1.60, 0.12, 0.04, (0.35, 0.55, 0.80), 0.85, 0.00),
    ]
    for i, profile in enumerate(profiles):
        (
            drop,
            max_blend,
            trigger,
            hold,
            return_s,
            descend_gamma,
            return_gamma,
            knee_amp,
            hip_bias,
            pose_window,
            min_health,
            return_pose_scale,
        ) = profile
        for recapture_error_gain in [2.6, 2.9]:
            for weight_boost in [1.0, 1.15]:
                phase_start, phase_peak, phase_end = pose_window
                rows.append({
                    **base,
                    "attempt": f"sched{i:02d}-eg{recapture_error_gain:.1f}-wb{weight_boost:.2f}".replace(".", "p"),
                    "drop": drop,
                    "max_blend": max_blend,
                    "recapture_trigger_drop": trigger,
                    "recapture_hold_s": hold,
                    "return_s": return_s,
                    "recapture_error_gain": recapture_error_gain,
                    "w_support": base["w_support"] * weight_boost,
                    "w_zmp": base["w_zmp"] * weight_boost,
                    "w_slip": base["w_slip"] * weight_boost,
                    "descend_gamma": descend_gamma,
                    "return_gamma": return_gamma,
                    "knee_amp": knee_amp,
                    "hip_bias": hip_bias,
                    "pose_start": phase_start,
                    "pose_peak": phase_peak,
                    "pose_end": phase_end,
                    "min_health": min_health,
                    "return_pose_scale": return_pose_scale,
                })
    focused = [
        (0.092, 0.546, 0.066, 0.16, 1.20, 0.90, 1.20, 0.10, 0.04, (0.55, 0.75, 0.95), 0.80, 0.00),
        (0.094, 0.548, 0.067, 0.18, 1.25, 0.88, 1.25, 0.11, 0.04, (0.55, 0.75, 0.95), 0.80, 0.05),
        (0.094, 0.548, 0.067, 0.18, 1.30, 0.88, 1.35, 0.11, 0.05, (0.55, 0.75, 0.95), 0.85, 0.05),
        (0.096, 0.550, 0.068, 0.20, 1.35, 0.85, 1.40, 0.12, 0.05, (0.50, 0.72, 0.95), 0.85, 0.05),
        (0.096, 0.552, 0.069, 0.20, 1.40, 0.82, 1.50, 0.12, 0.06, (0.50, 0.72, 0.95), 0.90, 0.00),
        (0.098, 0.552, 0.070, 0.22, 1.45, 0.80, 1.55, 0.13, 0.06, (0.48, 0.70, 0.94), 0.90, 0.00),
    ]
    for i, profile in enumerate(focused):
        (
            drop,
            max_blend,
            trigger,
            hold,
            return_s,
            descend_gamma,
            return_gamma,
            knee_amp,
            hip_bias,
            pose_window,
            min_health,
            return_pose_scale,
        ) = profile
        phase_start, phase_peak, phase_end = pose_window
        rows.append({
            **base,
            "attempt": f"focus{i:02d}".replace(".", "p"),
            "drop": drop,
            "max_blend": max_blend,
            "recapture_trigger_drop": trigger,
            "recapture_hold_s": hold,
            "return_s": return_s,
            "w_support": base["w_support"] * 1.15,
            "w_zmp": base["w_zmp"] * 1.15,
            "w_slip": base["w_slip"] * 1.15,
            "descend_gamma": descend_gamma,
            "return_gamma": return_gamma,
            "knee_amp": knee_amp,
            "hip_bias": hip_bias,
            "pose_start": phase_start,
            "pose_peak": phase_peak,
            "pose_end": phase_end,
            "min_health": min_health,
            "return_pose_scale": return_pose_scale,
        })
    return rows


def run_variant(variant: dict[str, Any], seconds: float, out_dir: Path) -> dict[str, Any]:
    global ACTIVE_PROFILE
    ACTIVE_PROFILE = {
        "descend_gamma": variant["descend_gamma"],
        "return_gamma": variant["return_gamma"],
        "knee_amp": variant["knee_amp"],
        "hip_bias": variant["hip_bias"],
        "pose_start": variant["pose_start"],
        "pose_peak": variant["pose_peak"],
        "pose_end": variant["pose_end"],
        "min_health": variant["min_health"],
        "return_pose_scale": variant["return_pose_scale"],
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
    contact = max(0.0, 0.90 - run["foot_contact_ratio"]) * 10.0
    return_penalty = 5.0 if not run["return_to_stand"] else 0.0
    return (
        fall
        + return_penalty
        + contact
        + 120.0 * gap["drop_shortfall_m"]
        + 18.0 * gap["knee_shortfall_rad"]
        + 18.0 * gap["hip_shortfall_rad"]
        + 25.0 * gap["slip_excess_m"]
        - 0.5 * run["visible_drop"]
    )


def write_summary(result: dict[str, Any], out_dir: Path) -> None:
    lines = [
        "# G1 Trajectory Schedule Search Summary",
        "",
        "| Attempt | 8cm | 7cm | Verdict | Drop | Knee | Hip | Contact | Slip | CoM min | ZMP min | Final h | Fell | profile d/b/trig/hold/ret/gammas | Gap d/k/h |",
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
            f"{v['drop']:.3f}/{v['max_blend']:.3f}/{v['recapture_trigger_drop']:.3f}/"
            f"{v['recapture_hold_s']:.2f}/{v['return_s']:.2f}/"
            f"{v['descend_gamma']:.2f}-{v['return_gamma']:.2f} | "
            f"{gap['drop_shortfall_m']:.4f}/{gap['knee_shortfall_rad']:.3f}/{gap['hip_shortfall_rad']:.3f} |"
        )
    lines.extend([
        "",
        f"Best visible run: {result['best_visible']}",
        f"Best recoverable run: {result['best_recoverable']}",
        f"Best no-fall run: {result['best_no_fall']}",
        f"Best depth run: {result['best_depth']}",
    ])
    (out_dir / "trajectory-schedule-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=7.0)
    args = parser.parse_args()
    out_dir = VERIFY / "trajectory-schedule-search"
    out_dir.mkdir(parents=True, exist_ok=True)
    result: dict[str, Any] = {
        "evaluation_seconds": args.seconds,
        "planning_gate": {
            "team_validation_mode": "manual-pass",
            "spec_delta": "M19 searches explicit descend/return trajectory profiles with full-rollout visible-gate scoring.",
            "perspectives": {
                "product": "directly targets the visible squat native gate before browser replay",
                "architecture": "wraps choose_blend to replace one-step desired_fraction with scheduled trajectory fractions",
                "security": "local MuJoCo/JAX execution only",
                "qa": "native JSON per schedule plus visible 8cm, knee/hip, contact, slip, return gates",
                "skeptic": "finite schedule search is still a coarse approximation of true TP-MPC/WBC",
            },
            "dod": [
                "evaluate explicit trajectory schedules around the exp76/77 recoverable boundary",
                "rank candidates by full-rollout visible gate shortfall and terminal stand objective",
            ],
        },
        "sources": [
            {
                "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC11769464/",
                "accessed": "2026-06-18",
                "note": "TP-MPC plus WBC optimizes squat trajectories and tracks them under constraints.",
            },
            {
                "url": "https://www.mdpi.com/1424-8220/25/2/435",
                "accessed": "2026-06-18",
                "note": "Same squat paper: rough trajectory optimization plus WBC tracking motivates scheduled trajectory search.",
            },
            {
                "url": "https://arxiv.org/html/2502.13013v1",
                "accessed": "2026-06-18",
                "note": "G1-class work reports squat-to-height behavior using height tracking reward and curriculum.",
            },
            {
                "url": "https://underactuated.mit.edu/humanoids.html",
                "accessed": "2026-06-18",
                "note": "Humanoid planning links CoM plans to whole-body plans through centroidal dynamics.",
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
