"""Probe phase-split hip-forward descent and terminal stand-up recovery."""

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
EXP67_PATH = ROOT / "experiments/67-g1-qfrc-wbc-return-selector/run_qfrc_wbc_return_selector.py"


def load_exp67():
    spec = importlib.util.spec_from_file_location("exp67_qfrc_wbc", EXP67_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {EXP67_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EXP67 = load_exp67()
EXP62 = EXP67.EXP62
EXP37 = EXP67.EXP37


def pose_delta(model: mujoco.MjModel, data: mujoco.MjData) -> dict[str, float]:
    start = model.keyframe("knees_bent").qpos
    qpos_index = EXP62.qpos_index
    lk = qpos_index(model, "left_knee_joint")
    rk = qpos_index(model, "right_knee_joint")
    lh = qpos_index(model, "left_hip_pitch_joint")
    rh = qpos_index(model, "right_hip_pitch_joint")
    return {
        "knee": max(abs(float(data.qpos[lk] - start[lk])), abs(float(data.qpos[rk] - start[rk]))),
        "hip": max(abs(float(data.qpos[lh] - start[lh])), abs(float(data.qpos[rh] - start[rh]))),
    }


def bell_window(x: float, start: float, peak: float, end: float) -> float:
    if x <= start or x >= end:
        return 0.0
    if x <= peak:
        return float(np.clip((x - start) / max(1e-6, peak - start), 0.0, 1.0))
    return float(np.clip((end - x) / max(1e-6, end - peak), 0.0, 1.0))


def apply_pose_bias(
    model: mujoco.MjModel,
    target: np.ndarray,
    variant: dict[str, Any],
    desired_fraction: float,
    return_phase: float,
    support_health: float,
    zmp_health: float,
    slip_health: float,
) -> tuple[np.ndarray, dict[str, float]]:
    biased = target.copy()
    if return_phase > 0.0:
        return biased, {
            "pose_bias_scale": 0.0,
            "pose_health": float(min(support_health, zmp_health, slip_health)),
            "pose_health_scale": 0.0,
        }
    descend_window = bell_window(
        desired_fraction,
        variant["pose_start"],
        variant["pose_peak"],
        variant["pose_end"],
    )
    return_scale = max(0.0, 1.0 - return_phase) * variant["return_pose_scale"]
    health = min(support_health, zmp_health, slip_health)
    health_scale = float(np.clip((health - variant["pose_health_floor"]) / max(1e-6, 1.0 - variant["pose_health_floor"]), 0.0, 1.0))
    scale = max(descend_window, return_scale) * health_scale
    biased[3] += variant["knee_amp"] * scale
    biased[9] += variant["knee_amp"] * scale
    biased[0] -= variant["hip_bias"] * scale
    biased[6] -= variant["hip_bias"] * scale
    ctrlrange = model.actuator_ctrlrange
    np.clip(biased, ctrlrange[:, 0], ctrlrange[:, 1], out=biased)
    return biased, {
        "pose_bias_scale": float(scale),
        "pose_health": float(health),
        "pose_health_scale": float(health_scale),
    }


def return_policy_targets(policy_targets: np.ndarray, variant: dict[str, Any], return_phase: float) -> np.ndarray:
    default = variant["default_pose"]
    keep = float(variant["return_policy_weight"]) * max(0.0, 1.0 - return_phase)
    return default + keep * (policy_targets - default)


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


def multi_step_choose_blend(**kwargs):
    model = kwargs["model"]
    data = kwargs["data"]
    variant = kwargs["variant"]
    support_now = kwargs["support_now"]
    zmp_now = kwargs["zmp_now"]
    foot_slip_now = kwargs["foot_slip_now"]
    prev_blend = kwargs["prev_blend"]
    desired_fraction = kwargs["desired_fraction"]
    return_phase = kwargs["return_phase"]
    ctrl_dt = kwargs["ctrl_dt"]
    n_substeps = kwargs["n_substeps"]
    horizon_steps = int(variant.get("horizon_steps", 4))

    support_health = float(np.clip((support_now["support_margin"] + 0.005) / 0.045, 0.0, 1.0))
    zmp_health = float(np.clip((zmp_now + 0.005) / 0.045, 0.0, 1.0))
    slip_health = float(np.clip(1.0 - foot_slip_now / 0.08, 0.0, 1.0))
    desired_blend = variant["max_blend"] * desired_fraction
    if return_phase > 0.0:
        raw = np.array([
            0.0,
            max(0.0, prev_blend - variant["fast_release"]),
            max(0.0, prev_blend - variant["slow_release"]),
            prev_blend,
            min(desired_blend, prev_blend + variant["small_hold"]),
        ])
    else:
        raw = np.array([
            0.35 * desired_blend,
            0.55 * desired_blend,
            0.75 * desired_blend,
            desired_blend,
            min(desired_blend, prev_blend + variant["descend_rate"]),
        ])
    blend_candidates = np.unique(np.round(np.clip(raw, 0.0, variant["max_blend"]), 5))
    best: dict[str, Any] | None = None
    for blend in blend_candidates:
        if return_phase > 0.0:
            policy_targets = return_policy_targets(kwargs["policy_targets"], variant, return_phase)
            ik_target = variant["default_pose"]
            build_blend = 0.0
            build_fraction = 0.0
            residual_scale = variant["return_residual_scale"]
        else:
            policy_targets = kwargs["policy_targets"]
            ik_target = kwargs["ik_target"]
            build_blend = float(blend)
            build_fraction = desired_fraction
            residual_scale = variant["residual_scale"]
        target = EXP62.build_target(
            model=model,
            default_pose=variant["default_pose"],
            policy_targets=policy_targets,
            ik_target=ik_target,
            blend=build_blend,
            residual_scale=residual_scale,
            desired_fraction=build_fraction,
            support_health=support_health,
            zmp_health=zmp_health,
            slip_health=slip_health,
            error_xy=kwargs["error_xy"],
        )
        target, pose_bias_terms = apply_pose_bias(
            model=model,
            target=target,
            variant=variant,
            desired_fraction=desired_fraction,
            return_phase=return_phase,
            support_health=support_health,
            zmp_health=zmp_health,
            slip_health=slip_health,
        )
        cand = EXP67.clone_data(model, data)
        cand.ctrl[:] = target
        safety_scale = min(1.0, support_health, zmp_health, slip_health)
        if return_phase > 0.0:
            safety_scale = max(variant["return_min_safety"], min(1.0, safety_scale + variant["return_safety_boost"]))
        pd_qfrc, _ = EXP62.lower_pd_torque(
            model=model,
            data=cand,
            maps=kwargs["maps"],
            target_qpos=target,
            kp=variant["return_joint_kp"] if return_phase > 0.0 else variant["joint_kp"],
            kd=variant["return_joint_kd"] if return_phase > 0.0 else variant["joint_kd"],
            torque_clip=variant["return_torque_clip"] if return_phase > 0.0 else variant["torque_clip"],
            safety_scale=safety_scale,
        )
        stance_qfrc, _ = EXP62.apply_stance_force(
            model=model,
            data=cand,
            foot_site_ids=kwargs["foot_site_ids"],
            initial_foot_xyz=kwargs["initial_foot_xyz"],
            kp_xy=variant["foot_kp_xy"],
            kd_xy=variant["foot_kd_xy"],
            lift_force=variant["foot_lift_force"],
            force_clip=variant["foot_force_clip"],
        )
        qfrc = pd_qfrc + stance_qfrc
        cand.qfrc_applied[:] = qfrc

        min_support = float("inf")
        min_zmp = float("inf")
        max_slip = 0.0
        contact_loss_count = 0
        prev_com_xy = kwargs["prev_com_xy"].copy()
        prev_com_vel = kwargs["prev_com_vel"].copy()
        height_before = kwargs["height_before"]
        final_height = float(cand.qpos[2])
        for _ in range(max(1, horizon_steps)):
            for _ in range(n_substeps):
                mujoco.mj_step(model, cand)
            support = EXP37.support_metrics(model, cand, kwargs["foot_geom_ids"])
            com_xy, com_vel, zmp = EXP67.zmp_margin(
                model=model,
                data=cand,
                support=support,
                prev_com_xy=prev_com_xy,
                prev_com_vel=prev_com_vel,
                ctrl_dt=ctrl_dt,
            )
            contacts = [
                float(cand.sensordata[model.sensor_adr[sensor_id]]) > 0
                for sensor_id in kwargs["foot_contact_sensor_ids"]
            ]
            foot_slip = float(np.max(np.linalg.norm(
                cand.site_xpos[kwargs["foot_site_ids"], :2] - kwargs["initial_foot_xyz"][:, :2],
                axis=1,
            )))
            min_support = min(min_support, support["support_margin"])
            min_zmp = min(min_zmp, zmp)
            max_slip = max(max_slip, foot_slip)
            contact_loss_count += 0 if all(contacts) else 1
            prev_com_xy = com_xy.copy()
            prev_com_vel = com_vel.copy()
            final_height = float(cand.qpos[2])
        cand.qfrc_applied[:] = 0.0

        support = EXP37.support_metrics(model, cand, kwargs["foot_geom_ids"])
        _, _, zmp = EXP67.zmp_margin(
            model=model,
            data=cand,
            support=support,
            prev_com_xy=kwargs["prev_com_xy"],
            prev_com_vel=kwargs["prev_com_vel"],
            ctrl_dt=ctrl_dt,
        )
        target_fraction = max(0.0, desired_fraction - return_phase)
        pose = pose_delta(model, cand)
        pose_fraction = 0.0 if return_phase > 0.0 else min(1.0, max(0.0, desired_fraction))
        knee_shortfall = max(0.0, variant["target_knee_delta"] * pose_fraction - pose["knee"])
        hip_shortfall = max(0.0, variant["target_hip_delta"] * pose_fraction - pose["hip"])
        immediate_cost, terms = EXP67.score_candidate(
            model=model,
            cand=cand,
            start_height=kwargs["start_height"],
            target_fraction=target_fraction,
            variant=variant,
            support=support,
            zmp=zmp,
            foot_slip=max_slip,
            both_feet=contact_loss_count == 0,
            height_before=height_before,
            ctrl_dt=ctrl_dt,
            blend=float(blend),
            prev_blend=prev_blend,
            qfrc_max=float(np.max(np.abs(qfrc))),
        )
        horizon_cost = (
            variant["w_support"] * max(0.0, variant["support_floor"] - min_support) ** 2
            + variant["w_zmp"] * max(0.0, variant["zmp_floor"] - min_zmp) ** 2
            + variant["w_slip"] * max(0.0, max_slip - variant["slip_floor"]) ** 2
            + variant["w_contact"] * contact_loss_count
            + variant["w_depth_cap"] * max(0.0, kwargs["start_height"] - final_height - variant["depth_cap"]) ** 2
            + variant["w_knee"] * knee_shortfall ** 2
            + variant["w_hip"] * hip_shortfall ** 2
            + variant["w_stand"] * max(0.0, variant["stand_height"] - final_height) ** 2 * max(0.0, return_phase)
            + variant["w_return_slip"] * max(0.0, max_slip - variant["return_slip_floor"]) ** 2 * max(0.0, return_phase)
        )
        cost = immediate_cost + float(variant.get("horizon_weight", 1.0)) * horizon_cost
        row = {
            "blend": float(blend),
            "cost": cost,
            "terms": terms,
            "horizon_cost": horizon_cost,
            "horizon_min_support": min_support,
            "horizon_min_zmp": min_zmp,
            "horizon_max_slip": max_slip,
            "horizon_contact_loss_count": contact_loss_count,
            "horizon_knee_delta": pose["knee"],
            "horizon_hip_delta": pose["hip"],
            "horizon_knee_shortfall": knee_shortfall,
            "horizon_hip_shortfall": hip_shortfall,
            **pose_bias_terms,
            "support_margin": support["support_margin"],
            "zmp_margin": zmp,
            "foot_slip_distance": max_slip,
            "height": final_height,
            "qfrc_max": float(np.max(np.abs(qfrc))),
            "target": target,
            "qfrc": qfrc,
        }
        if best is None or cost < best["cost"]:
            best = row
    assert best is not None
    chosen = {k: v for k, v in best.items() if k not in {"target", "qfrc"}}
    return best["target"], best["qfrc"], chosen


def variants() -> list[dict[str, Any]]:
    common = {
        "policy_weight": 1.0,
        "joint_kd": 1.4,
        "foot_kd_xy": 22.0,
        "foot_lift_force": 180.0,
        "support_floor": 0.006,
        "zmp_floor": -0.020,
        "slip_floor": 0.055,
        "downward_floor": 0.10,
        "stand_height": 0.74,
        "height_floor": 0.62,
        "upright_floor": 0.82,
        "qfrc_soft_cap": 58.0,
        "return_safety_boost": 0.20,
        "return_min_safety": 0.55,
        "return_policy_weight": 0.05,
        "return_residual_scale": 0.0,
        "return_joint_kp": 38.0,
        "return_joint_kd": 2.0,
        "return_torque_clip": 56.0,
        "return_slip_floor": 0.065,
        "descend_rate": 0.040,
        "slow_release": 0.035,
        "fast_release": 0.090,
        "small_hold": 0.012,
        "w_height": 135.0,
        "w_stand": 150.0,
        "w_height_floor": 850.0,
        "w_upright": 620.0,
        "w_support": 4200.0,
        "w_zmp": 3200.0,
        "w_slip": 2800.0,
        "w_contact": 480.0,
        "w_downward": 160.0,
        "w_qfrc": 5.0,
        "w_smooth": 2.0,
        "w_knee": 44.0,
        "w_hip": 40.0,
        "w_return_slip": 6200.0,
        "w_depth_cap": 1200.0,
        "depth_cap": 0.22,
        "horizon_weight": 1.1,
        "target_knee_delta": 0.60,
        "target_hip_delta": 0.35,
        "pose_start": 0.30,
        "pose_peak": 0.78,
        "pose_end": 1.02,
        "pose_health_floor": 0.25,
        "return_pose_scale": 0.25,
    }
    return [
        {**common, "attempt": "cap18-split-hip0p16-return2p3", "drop": 0.080, "max_blend": 0.51, "residual_scale": 0.060, "joint_kp": 26.0, "torque_clip": 36.0, "foot_kp_xy": 400.0, "foot_force_clip": 305.0, "descend_s": 3.8, "return_s": 2.3, "horizon_steps": 6, "w_height": 102.0, "w_support": 7600.0, "w_slip": 6200.0, "w_stand": 680.0, "knee_amp": 0.08, "hip_bias": 0.16, "w_knee": 58.0, "w_hip": 320.0, "pose_health_floor": 0.10, "depth_cap": 0.18, "w_depth_cap": 18000.0},
        {**common, "attempt": "cap22-split-hip0p18-return2p4", "drop": 0.080, "max_blend": 0.52, "residual_scale": 0.062, "joint_kp": 27.0, "torque_clip": 38.0, "foot_kp_xy": 420.0, "foot_force_clip": 325.0, "descend_s": 4.0, "return_s": 2.4, "horizon_steps": 6, "w_height": 104.0, "w_support": 7800.0, "w_slip": 6400.0, "w_stand": 720.0, "knee_amp": 0.09, "hip_bias": 0.18, "w_knee": 64.0, "w_hip": 380.0, "pose_health_floor": 0.10, "depth_cap": 0.22, "w_depth_cap": 16000.0},
        {**common, "attempt": "cap25-split-hip0p20-return2p6", "drop": 0.080, "max_blend": 0.52, "residual_scale": 0.062, "joint_kp": 28.0, "torque_clip": 40.0, "foot_kp_xy": 440.0, "foot_force_clip": 340.0, "descend_s": 4.2, "return_s": 2.6, "horizon_steps": 6, "w_height": 104.0, "w_support": 8000.0, "w_slip": 6600.0, "w_stand": 760.0, "knee_amp": 0.10, "hip_bias": 0.20, "w_knee": 68.0, "w_hip": 440.0, "pose_health_floor": 0.10, "depth_cap": 0.25, "w_depth_cap": 14000.0},
        {**common, "attempt": "cap18-guarded-hip0p14-return2p6", "drop": 0.080, "max_blend": 0.50, "residual_scale": 0.058, "joint_kp": 26.0, "torque_clip": 36.0, "foot_kp_xy": 460.0, "foot_force_clip": 350.0, "descend_s": 4.0, "return_s": 2.6, "horizon_steps": 6, "w_height": 100.0, "w_support": 9000.0, "w_slip": 7600.0, "w_stand": 800.0, "return_joint_kp": 44.0, "return_torque_clip": 64.0, "knee_amp": 0.08, "hip_bias": 0.14, "w_knee": 58.0, "w_hip": 300.0, "pose_health_floor": 0.14, "depth_cap": 0.18, "w_depth_cap": 22000.0},
    ]


def write_summary(result: dict[str, Any], out_dir: Path) -> None:
    lines = [
        "# G1 Phase-Split Hip Return Controller Summary",
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
    (out_dir / "phase-split-hip-return-controller-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=6.0)
    args = parser.parse_args()
    out_dir = VERIFY / "phase-split-hip-return-controller"
    out_dir.mkdir(parents=True, exist_ok=True)
    EXP67.choose_blend = multi_step_choose_blend
    result = {
        "evaluation_seconds": args.seconds,
        "planning_gate": {
            "team_validation_mode": "manual-pass",
            "spec_delta": "M19 now separates hip-forward descent from terminal stand-up recovery instead of optimizing both in one selector branch.",
            "perspectives": {
                "product": "tries to close the hip/return gap left by exp84 while preserving 8cm depth, knee, contact, and slip evidence",
                "architecture": "monkeypatches exp67 WBC-lite candidate selection with separate descent and return target construction",
                "security": "no credentials or external side effects",
                "qa": "native sweep records raw JSON and visible gate metrics per phase-split variant",
                "skeptic": "early return may recover height by sacrificing hip pose, while stronger hip descent may still slip or fall",
            },
            "dod": [
                "raw native JSON per horizon variant",
                "summary states whether any variant passes visible_8cm_gate",
            ],
        },
        "sources": [
            {
                "url": "https://www.mdpi.com/1424-8220/25/2/435",
                "accessed": "2026-06-18",
                "note": "Squat motion study combines trajectory optimization and WBC instead of using a single monolithic tracking objective.",
            },
            {
                "url": "https://arxiv.org/html/2502.12152v1",
                "accessed": "2026-06-18",
                "note": "HumanUP motivates two-stage discovery and refinement for robust Unitree G1 getting-up policies.",
            },
            {
                "url": "https://arxiv.org/html/2502.08378v1",
                "accessed": "2026-06-18",
                "note": "Humanoid standing-up control is framed as a multi-stage skill with time-varying contacts and motion constraints.",
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
