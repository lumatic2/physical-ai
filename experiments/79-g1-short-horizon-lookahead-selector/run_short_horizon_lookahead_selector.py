"""Probe short-horizon lookahead selection for the G1 visible squat gate."""

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
ORIGINAL_BUILD_TARGET = EXP71.EXP62.build_target
ORIGINAL_CHOOSE_BLEND = EXP71.EXP67.choose_blend

ACTIVE_PROFILE: dict[str, Any] = {}
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


def pose_delta(model: mujoco.MjModel, data: mujoco.MjData) -> dict[str, float]:
    start = model.keyframe("knees_bent").qpos
    qpos_index = EXP71.EXP62.qpos_index
    lk = qpos_index(model, "left_knee_joint")
    rk = qpos_index(model, "right_knee_joint")
    lh = qpos_index(model, "left_hip_pitch_joint")
    rh = qpos_index(model, "right_hip_pitch_joint")
    return {
        "knee": max(abs(float(data.qpos[lk] - start[lk])), abs(float(data.qpos[rk] - start[rk]))),
        "hip": max(abs(float(data.qpos[lh] - start[lh])), abs(float(data.qpos[rh] - start[rh]))),
    }


def lookahead_cost(
    *,
    model: mujoco.MjModel,
    cand: mujoco.MjData,
    start_height: float,
    target_fraction: float,
    return_phase: float,
    variant: dict[str, Any],
    support: dict[str, Any],
    zmp: float,
    foot_slip: float,
    both_feet: bool,
) -> tuple[float, dict[str, float]]:
    height = float(cand.qpos[2])
    quat = cand.qpos[3:7]
    mat = np.empty(9)
    mujoco.mju_quat2Mat(mat, quat)
    up_z = float(mat.reshape(3, 3)[2, 2])
    pose = pose_delta(model, cand)
    visible_drop = start_height - height
    desired_height = start_height - variant["drop"] * target_fraction
    support_breach = max(0.0, variant["support_floor"] - support["support_margin"])
    zmp_breach = max(0.0, variant["zmp_floor"] - zmp)
    slip_excess = max(0.0, foot_slip - variant["slip_floor"])
    drop_shortfall = max(0.0, min(0.08, variant["drop"] * target_fraction) - visible_drop)
    knee_shortfall = max(0.0, 0.60 * min(1.0, target_fraction) - pose["knee"])
    hip_shortfall = max(0.0, 0.35 * min(1.0, target_fraction) - pose["hip"])
    stand_err = max(0.0, variant["stand_height"] - height) if return_phase > 0.0 else 0.0
    terms = {
        "height": 90.0 * (height - desired_height) ** 2,
        "drop": ACTIVE_PROFILE["w_drop"] * drop_shortfall ** 2,
        "knee": ACTIVE_PROFILE["w_knee"] * knee_shortfall ** 2,
        "hip": ACTIVE_PROFILE["w_hip"] * hip_shortfall ** 2,
        "stand": 420.0 * stand_err ** 2,
        "upright": 900.0 * max(0.0, 0.82 - up_z) ** 2,
        "support": variant["w_support"] * support_breach ** 2,
        "zmp": variant["w_zmp"] * zmp_breach ** 2,
        "slip": variant["w_slip"] * slip_excess ** 2,
        "contact": 260.0 * (0.0 if both_feet else 1.0),
    }
    return float(sum(terms.values())), terms


def scheduled_choose_blend(*args, **kwargs):
    global ACTIVE_PROFILE_FRACTION, ACTIVE_RETURN_PHASE
    ACTIVE_RETURN_PHASE = float(kwargs["return_phase"])
    base_fraction = scheduled_fraction(
        float(kwargs["desired_fraction"]),
        ACTIVE_RETURN_PHASE,
        ACTIVE_PROFILE,
    )
    best: dict[str, Any] | None = None
    offsets = ACTIVE_PROFILE["return_offsets"] if ACTIVE_RETURN_PHASE > 0.0 else ACTIVE_PROFILE["descend_offsets"]
    for offset in offsets:
        ACTIVE_PROFILE_FRACTION = float(np.clip(base_fraction + offset, 0.0, 1.0))
        trial_kwargs = dict(kwargs)
        trial_kwargs["desired_fraction"] = ACTIVE_PROFILE_FRACTION
        target, qfrc, chosen = ORIGINAL_CHOOSE_BLEND(*args, **trial_kwargs)
        model = kwargs["model"]
        cand = EXP71.EXP67.clone_data(model, kwargs["data"])
        cand.ctrl[:] = target
        cand.qfrc_applied[:] = qfrc
        for _ in range(max(1, int(ACTIVE_PROFILE["horizon_steps"]))):
            for _ in range(kwargs["n_substeps"]):
                mujoco.mj_step(model, cand)
        cand.qfrc_applied[:] = 0.0
        support = EXP71.EXP37.support_metrics(model, cand, kwargs["foot_geom_ids"])
        _, _, zmp = EXP71.EXP67.zmp_margin(
            model=model,
            data=cand,
            support=support,
            prev_com_xy=kwargs["prev_com_xy"],
            prev_com_vel=kwargs["prev_com_vel"],
            ctrl_dt=kwargs["ctrl_dt"],
        )
        contacts = [
            float(cand.sensordata[model.sensor_adr[sensor_id]]) > 0
            for sensor_id in kwargs["foot_contact_sensor_ids"]
        ]
        foot_slip = float(np.max(np.linalg.norm(
            cand.site_xpos[kwargs["foot_site_ids"], :2] - kwargs["initial_foot_xyz"][:, :2],
            axis=1,
        )))
        cost, terms = lookahead_cost(
            model=model,
            cand=cand,
            start_height=kwargs["start_height"],
            target_fraction=ACTIVE_PROFILE_FRACTION,
            return_phase=ACTIVE_RETURN_PHASE,
            variant=kwargs["variant"],
            support=support,
            zmp=zmp,
            foot_slip=foot_slip,
            both_feet=all(contacts),
        )
        row = {
            "cost": cost,
            "target": target,
            "qfrc": qfrc,
            "chosen": chosen,
            "fraction": ACTIVE_PROFILE_FRACTION,
            "lookahead_terms": terms,
            "lookahead_support": support["support_margin"],
            "lookahead_zmp": zmp,
            "lookahead_slip": foot_slip,
        }
        if best is None or row["cost"] < best["cost"]:
            best = row
    assert best is not None
    chosen = dict(best["chosen"])
    chosen["lookahead_cost"] = best["cost"]
    chosen["lookahead_fraction"] = best["fraction"]
    chosen["lookahead_support"] = best["lookahead_support"]
    chosen["lookahead_zmp"] = best["lookahead_zmp"]
    chosen["lookahead_slip"] = best["lookahead_slip"]
    chosen["lookahead_terms"] = best["lookahead_terms"]
    return best["target"], best["qfrc"], chosen


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
                    "horizon_steps": 2,
                    "descend_offsets": [-0.04, 0.0, 0.04, 0.08],
                    "return_offsets": [-0.08, -0.04, 0.0, 0.04],
                    "w_drop": 3200.0,
                    "w_knee": 36.0,
                    "w_hip": 30.0,
                })
    focused = [
        (0.092, 0.546, 0.066, 0.16, 1.20, 0.90, 1.20, 0.10, 0.04, (0.55, 0.75, 0.95), 0.80, 0.00, 2),
        (0.094, 0.548, 0.067, 0.18, 1.25, 0.88, 1.25, 0.11, 0.04, (0.55, 0.75, 0.95), 0.80, 0.05, 2),
        (0.094, 0.548, 0.067, 0.18, 1.30, 0.88, 1.35, 0.11, 0.05, (0.55, 0.75, 0.95), 0.85, 0.05, 3),
        (0.096, 0.550, 0.068, 0.20, 1.35, 0.85, 1.40, 0.12, 0.05, (0.50, 0.72, 0.95), 0.85, 0.05, 3),
        (0.096, 0.552, 0.069, 0.20, 1.40, 0.82, 1.50, 0.12, 0.06, (0.50, 0.72, 0.95), 0.90, 0.00, 4),
        (0.098, 0.552, 0.070, 0.22, 1.45, 0.80, 1.55, 0.13, 0.06, (0.48, 0.70, 0.94), 0.90, 0.00, 4),
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
            horizon_steps,
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
            "horizon_steps": horizon_steps,
            "descend_offsets": [-0.06, 0.0, 0.04, 0.08],
            "return_offsets": [-0.08, -0.04, 0.0, 0.04],
            "w_drop": 3600.0,
            "w_knee": 42.0,
            "w_hip": 34.0,
        })
    safe_focus = [
        (0.096, 0.550, 0.066, 0.22, 1.40, 0.78, 1.60, 0.10, 0.05, (0.55, 0.75, 0.95), 0.82, 0.00, 2, 0.95),
        (0.098, 0.550, 0.067, 0.24, 1.45, 0.78, 1.65, 0.10, 0.05, (0.55, 0.75, 0.95), 0.85, 0.00, 2, 0.95),
        (0.098, 0.552, 0.067, 0.24, 1.50, 0.76, 1.70, 0.11, 0.05, (0.52, 0.74, 0.95), 0.85, 0.00, 2, 1.00),
        (0.100, 0.552, 0.068, 0.26, 1.55, 0.74, 1.75, 0.11, 0.06, (0.52, 0.74, 0.95), 0.88, 0.00, 3, 0.95),
        (0.100, 0.554, 0.068, 0.26, 1.60, 0.72, 1.80, 0.12, 0.06, (0.50, 0.72, 0.95), 0.90, 0.00, 3, 0.90),
        (0.102, 0.554, 0.069, 0.28, 1.65, 0.70, 1.85, 0.12, 0.07, (0.50, 0.72, 0.95), 0.90, 0.00, 3, 0.90),
    ]
    narrow: list[dict[str, Any]] = []
    for i, profile in enumerate(safe_focus):
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
            horizon_steps,
            weight_boost,
        ) = profile
        phase_start, phase_peak, phase_end = pose_window
        narrow.append({
            **base,
            "attempt": f"narrow{i:02d}",
            "drop": drop,
            "max_blend": max_blend,
            "recapture_trigger_drop": trigger,
            "recapture_hold_s": hold,
            "return_s": return_s,
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
            "horizon_steps": horizon_steps,
            "descend_offsets": [-0.06, -0.02, 0.0, 0.04],
            "return_offsets": [-0.10, -0.06, -0.02, 0.0],
            "w_drop": 3400.0,
            "w_knee": 38.0,
            "w_hip": 38.0,
        })
    return rows[:24] + narrow


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
        "horizon_steps": variant["horizon_steps"],
        "descend_offsets": variant["descend_offsets"],
        "return_offsets": variant["return_offsets"],
        "w_drop": variant["w_drop"],
        "w_knee": variant["w_knee"],
        "w_hip": variant["w_hip"],
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
        "# G1 Short-Horizon Lookahead Selector Summary",
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
    out_dir = VERIFY / "short-horizon-lookahead-selector"
    out_dir.mkdir(parents=True, exist_ok=True)
    result: dict[str, Any] = {
        "evaluation_seconds": args.seconds,
        "planning_gate": {
            "team_validation_mode": "manual-pass",
        "spec_delta": "M19 replaces one-step target selection with short-horizon MuJoCo lookahead over trajectory fractions.",
            "perspectives": {
                "product": "directly targets the visible squat native gate before browser replay",
                "architecture": "wraps choose_blend with clone-based lookahead scoring over future support/ZMP/slip/pose state",
                "security": "local MuJoCo/JAX execution only",
                "qa": "native JSON per schedule plus visible 8cm, knee/hip, contact, slip, return gates",
                "skeptic": "short-horizon constant-control rollout is still a coarse approximation of full MPC",
            },
            "dod": [
                "evaluate short-horizon fraction candidates around the exp76/78 recoverable boundary",
                "rank candidates by lookahead visible-gate shortfall, support/ZMP/slip, and terminal stand objective",
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
