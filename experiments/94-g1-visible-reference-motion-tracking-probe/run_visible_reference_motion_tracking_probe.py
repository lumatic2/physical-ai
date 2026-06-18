"""Visible squat reference plus stabilizer-conditioned tracking probe for G1."""

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
EXP28 = EXP67.EXP28
EXP36 = EXP67.EXP36
EXP37 = EXP67.EXP37
EXP62 = EXP67.EXP62
EXP60 = EXP67.EXP60


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
        "contact_shortfall": max(0.0, 0.90 - run["foot_contact_ratio"]),
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


def phase_scale(desired_fraction: float, return_phase: float) -> tuple[str, float]:
    if return_phase <= 0.0:
        return "descend_hold", float(np.clip(desired_fraction, 0.0, 1.0))
    return "return", float(np.clip(1.0 - return_phase, 0.0, 1.0))


def reference_target(
    model: mujoco.MjModel,
    variant: dict[str, Any],
    ik_target: np.ndarray,
    desired_fraction: float,
    return_phase: float,
) -> tuple[np.ndarray, dict[str, float | str]]:
    phase, scale = phase_scale(desired_fraction, return_phase)
    default_pose = variant["default_pose"]
    visible_pose = ik_target.copy()
    visible_pose[3] = default_pose[3] + variant["target_knee_delta"]
    visible_pose[9] = default_pose[9] + variant["target_knee_delta"]
    visible_pose[0] = default_pose[0] - variant["target_hip_delta"]
    visible_pose[6] = default_pose[6] - variant["target_hip_delta"]
    ctrlrange = model.actuator_ctrlrange
    np.clip(visible_pose, ctrlrange[:, 0], ctrlrange[:, 1], out=visible_pose)
    target = default_pose + scale * (visible_pose - default_pose)
    np.clip(target, ctrlrange[:, 0], ctrlrange[:, 1], out=target)
    return target.astype(np.float32), {
        "reference_phase": phase,
        "reference_scale": float(scale),
        "reference_target_knee_delta": float(variant["target_knee_delta"] * scale),
        "reference_target_hip_delta": float(variant["target_hip_delta"] * scale),
    }


def apply_stance_preload(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    foot_site_ids: np.ndarray,
    initial_foot_xyz: np.ndarray,
    foot_contact_sensor_ids: list[int],
    preload_force: float,
    height_kp: float,
    force_clip: float,
) -> tuple[np.ndarray, dict[str, float]]:
    qfrc = np.zeros(model.nv)
    if preload_force <= 0.0 or force_clip <= 0.0:
        return qfrc, {"stance_preload_max_force": 0.0}
    max_force = 0.0
    for idx, site_id in enumerate(foot_site_ids):
        jacp = np.zeros((3, model.nv))
        jacr = np.zeros((3, model.nv))
        mujoco.mj_jacSite(model, data, jacp, jacr, int(site_id))
        sensor_id = foot_contact_sensor_ids[idx]
        contact = float(data.sensordata[model.sensor_adr[sensor_id]]) > 0.0
        height_err = float(data.site_xpos[site_id, 2] - initial_foot_xyz[idx, 2])
        contact_mult = 1.0 if contact else 1.6
        down_force = min(force_clip, preload_force * contact_mult + height_kp * max(0.0, height_err))
        qfrc += jacp.T @ np.array([0.0, 0.0, -down_force])
        max_force = max(max_force, float(down_force))
    return qfrc, {"stance_preload_max_force": max_force}


def reference_choose_blend(**kwargs):
    model = kwargs["model"]
    data = kwargs["data"]
    maps = kwargs["maps"]
    variant = kwargs["variant"]
    support_now = kwargs["support_now"]
    zmp_now = kwargs["zmp_now"]
    foot_slip_now = kwargs["foot_slip_now"]
    desired_fraction = kwargs["desired_fraction"]
    return_phase = kwargs["return_phase"]

    support_health = float(np.clip((support_now["support_margin"] + 0.005) / 0.045, 0.0, 1.0))
    zmp_health = float(np.clip((zmp_now + 0.005) / 0.045, 0.0, 1.0))
    slip_health = float(np.clip(1.0 - foot_slip_now / variant["slip_release"], 0.0, 1.0))
    health = min(support_health, zmp_health, slip_health)
    ref_target, ref_terms = reference_target(
        model=model,
        variant=variant,
        ik_target=kwargs["ik_target"],
        desired_fraction=desired_fraction,
        return_phase=return_phase,
    )
    if variant["release_on_unhealthy"]:
        ref_weight = variant["reference_weight"] * float(np.clip((health - variant["health_floor"]) / max(1e-6, 1.0 - variant["health_floor"]), 0.0, 1.0))
    else:
        ref_weight = variant["reference_weight"]
    if return_phase > 0.0:
        ref_weight *= variant["return_reference_weight"]
    stabilizer_target = kwargs["policy_targets"]
    target = (1.0 - ref_weight) * stabilizer_target + ref_weight * ref_target
    target = variant["default_pose"] + variant["residual_scale"] * (target - variant["default_pose"])
    np.clip(target, model.actuator_ctrlrange[:, 0], model.actuator_ctrlrange[:, 1], out=target)

    safety_scale = max(variant["min_safety_scale"], health)
    pd_qfrc, _ = EXP62.lower_pd_torque(
        model=model,
        data=data,
        maps=maps,
        target_qpos=target,
        kp=variant["joint_kp"],
        kd=variant["joint_kd"],
        torque_clip=variant["torque_clip"],
        safety_scale=safety_scale,
    )
    stance_qfrc, _ = EXP62.apply_stance_force(
        model=model,
        data=data,
        foot_site_ids=kwargs["foot_site_ids"],
        initial_foot_xyz=kwargs["initial_foot_xyz"],
        kp_xy=variant["foot_kp_xy"],
        kd_xy=variant["foot_kd_xy"],
        lift_force=variant["foot_lift_force"],
        force_clip=variant["foot_force_clip"],
    )
    preload_qfrc, preload_terms = apply_stance_preload(
        model=model,
        data=data,
        foot_site_ids=kwargs["foot_site_ids"],
        initial_foot_xyz=kwargs["initial_foot_xyz"],
        foot_contact_sensor_ids=kwargs["foot_contact_sensor_ids"],
        preload_force=variant["preload_force"],
        height_kp=variant["preload_height_kp"],
        force_clip=variant["preload_force_clip"],
    )
    qfrc = pd_qfrc + stance_qfrc + preload_qfrc
    chosen = {
        "blend": float(ref_weight),
        "cost": float((1.0 - health) + max(0.0, foot_slip_now - variant["slip_release"]) * 10.0),
        "qfrc_max": float(np.max(np.abs(qfrc))),
        "height": float(data.qpos[2]),
        "support_margin": float(support_now["support_margin"]),
        "zmp_margin": float(zmp_now),
        "foot_slip_distance": float(foot_slip_now),
        "support_health": support_health,
        "zmp_health": zmp_health,
        "slip_health": slip_health,
        "reference_weight_effective": float(ref_weight),
        **ref_terms,
        **preload_terms,
    }
    return target, qfrc, chosen


def build_reference_probe() -> dict[str, Any]:
    env = EXP28.ContactAwareSquat(
        stage_height=0.67,
        controller_blend=0.5,
        freeze_phase=True,
        blend_schedule="squat",
        reference_scale=1.0,
        config_overrides={"impl": "jax"},
    )
    model = env.mj_model
    data = mujoco.MjData(model)
    key = model.keyframe("knees_bent")
    data.qpos[:] = key.qpos
    data.ctrl[:] = key.qpos[7:]
    mujoco.mj_forward(model, data)
    foot_site_ids = np.asarray(env._feet_site_id)
    initial_foot_xyz = data.site_xpos[foot_site_ids, :3].copy()
    default_pose = key.qpos[7:].astype(np.float32).copy()
    ik = EXP36.solve_foot_fixed_target(model, key.qpos.copy(), foot_site_ids, 0.09)
    ik_target = default_pose.copy()
    ik_target[:15] = np.asarray(ik["lower_body_target"], dtype=np.float32)
    variant = {
        "default_pose": default_pose,
        "target_knee_delta": 0.64,
        "target_hip_delta": 0.38,
    }
    target, _ = reference_target(model, variant, ik_target, 1.0, 0.0)
    probe = mujoco.MjData(model)
    probe.qpos[:] = key.qpos
    probe.qpos[2] = float(ik["target_height"])
    probe.qpos[7:] = target
    mujoco.mj_forward(model, probe)
    pose_indices = {
        name: EXP62.qpos_index(model, name)
        for name in ["left_knee_joint", "right_knee_joint", "left_hip_pitch_joint", "right_hip_pitch_joint"]
    }
    return {
        "description": "Static visible reference target before dynamics tracking.",
        "start_height": float(data.qpos[2]),
        "reference_height": float(probe.qpos[2]),
        "intended_base_drop_m": float(data.qpos[2] - probe.qpos[2]),
        "foot_site_z_error_m": float(np.max(np.abs(probe.site_xpos[foot_site_ids, 2] - initial_foot_xyz[:, 2]))),
        "foot_site_xy_error_m": float(np.max(np.linalg.norm(probe.site_xpos[foot_site_ids, :2] - initial_foot_xyz[:, :2], axis=1))),
        "target_knee_delta_rad": max(
            abs(float(probe.qpos[pose_indices["left_knee_joint"]] - key.qpos[pose_indices["left_knee_joint"]])),
            abs(float(probe.qpos[pose_indices["right_knee_joint"]] - key.qpos[pose_indices["right_knee_joint"]])),
        ),
        "target_hip_pitch_delta_rad": max(
            abs(float(probe.qpos[pose_indices["left_hip_pitch_joint"]] - key.qpos[pose_indices["left_hip_pitch_joint"]])),
            abs(float(probe.qpos[pose_indices["right_hip_pitch_joint"]] - key.qpos[pose_indices["right_hip_pitch_joint"]])),
        ),
        "foot_sites_start": initial_foot_xyz.tolist(),
        "foot_sites_reference": probe.site_xpos[foot_site_ids, :3].tolist(),
    }


def optimizer_score(run: dict[str, Any]) -> float:
    gap = run["visible_gap"]
    score = 0.0
    score += 1500.0 if run["fell_at"] is not None else 0.0
    score += 480.0 * gap["drop_shortfall_m"] / 0.08
    score += 560.0 * gap["knee_shortfall_rad"] / 0.60
    score += 280.0 * gap["hip_shortfall_rad"] / 0.35
    score += 420.0 * gap["slip_excess_m"] / 0.08
    score += 280.0 * gap["contact_shortfall"]
    if not run["return_to_stand"]:
        score += 250.0
    if run["visible_8cm_gate"]:
        score -= 1000.0
    return float(score)


def variants() -> list[dict[str, Any]]:
    common = {
        "drop": 0.09,
        "policy_weight": 1.0,
        "target_knee_delta": 0.64,
        "target_hip_delta": 0.38,
        "joint_kd": 1.5,
        "foot_kd_xy": 20.0,
        "foot_lift_force": 170.0,
        "slip_release": 0.08,
        "health_floor": 0.20,
        "min_safety_scale": 0.45,
        "return_reference_weight": 0.25,
        "release_on_unhealthy": True,
        "descend_s": 4.2,
        "return_s": 2.2,
    }
    return [
        {**common, "attempt": "reference-open-loop", "max_blend": 1.0, "reference_weight": 1.0, "residual_scale": 1.0, "joint_kp": 0.0, "torque_clip": 0.0, "foot_kp_xy": 0.0, "foot_force_clip": 0.0, "preload_force": 0.0, "preload_height_kp": 0.0, "preload_force_clip": 0.0, "release_on_unhealthy": False},
        {**common, "attempt": "stabilizer-reference-025", "max_blend": 0.25, "reference_weight": 0.25, "residual_scale": 0.55, "joint_kp": 22.0, "torque_clip": 32.0, "foot_kp_xy": 220.0, "foot_force_clip": 180.0, "preload_force": 12.0, "preload_height_kp": 220.0, "preload_force_clip": 54.0},
        {**common, "attempt": "stabilizer-reference-040-contact", "max_blend": 0.40, "reference_weight": 0.40, "residual_scale": 0.72, "joint_kp": 28.0, "torque_clip": 42.0, "foot_kp_xy": 420.0, "foot_force_clip": 320.0, "preload_force": 24.0, "preload_height_kp": 480.0, "preload_force_clip": 88.0},
        {**common, "attempt": "stabilizer-reference-055-contact", "max_blend": 0.55, "reference_weight": 0.55, "residual_scale": 0.86, "joint_kp": 34.0, "torque_clip": 54.0, "foot_kp_xy": 560.0, "foot_force_clip": 450.0, "preload_force": 34.0, "preload_height_kp": 680.0, "preload_force_clip": 112.0},
        {**common, "attempt": "release-reference-050", "max_blend": 0.50, "reference_weight": 0.50, "residual_scale": 0.82, "joint_kp": 32.0, "torque_clip": 50.0, "foot_kp_xy": 600.0, "foot_force_clip": 470.0, "preload_force": 36.0, "preload_height_kp": 720.0, "preload_force_clip": 118.0, "health_floor": 0.38},
        {**common, "attempt": "knee-priority-reference-045", "max_blend": 0.45, "reference_weight": 0.45, "residual_scale": 0.90, "target_knee_delta": 0.70, "target_hip_delta": 0.40, "joint_kp": 30.0, "torque_clip": 48.0, "foot_kp_xy": 520.0, "foot_force_clip": 420.0, "preload_force": 32.0, "preload_height_kp": 650.0, "preload_force_clip": 110.0, "health_floor": 0.42},
    ]


def write_summary(result: dict[str, Any], out_dir: Path) -> None:
    lines = [
        "# G1 Visible Reference Motion Tracking Probe Summary",
        "",
        "| Rank | Attempt | Score | Visible gate | Verdict | Drop | Knee | Hip | Contact | Slip | Final h | Fell |",
        "|---:|---|---:|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for rank, run in enumerate(sorted(result["runs"], key=lambda item: item["optimizer_score"]), start=1):
        fell = "never" if run["fell_at"] is None else f"{run['fell_at']:.2f}s"
        gate = "PASS" if run["visible_8cm_gate"] else "FAIL"
        lines.append(
            f"| {rank} | {run['attempt']} | {run['optimizer_score']:.1f} | {gate} | {run['visible_verdict']} | "
            f"{run['visible_drop']:.4f}m | {run['max_knee_delta_rad']:.3f} | "
            f"{run['max_hip_pitch_delta_rad']:.3f} | {run['foot_contact_ratio']:.2f} | "
            f"{run['foot_slip_distance']:.3f}m | {run['final_height']:.4f}m | {fell} |"
        )
    lines.extend([
        "",
        f"Static reference: {result['reference_probe']}",
        f"Best optimizer run: {result['best_optimizer']}",
        f"Best no-fall run: {result['best_no_fall']}",
        "",
        "M19 closes only when visible native and browser replay both pass.",
    ])
    (out_dir / "visible-reference-motion-tracking-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=6.0)
    args = parser.parse_args()
    out_dir = VERIFY / "visible-reference-motion-tracking-probe"
    out_dir.mkdir(parents=True, exist_ok=True)
    EXP67.choose_blend = reference_choose_blend
    result = {
        "evaluation_seconds": args.seconds,
        "planning_gate": {
            "team_validation_mode": "manual-pass",
            "spec_delta": "M19 stops scalar action-wrapper search and probes explicit visible squat reference tracking with the existing stabilizer prior.",
            "perspectives": {
                "product": "answers whether the current G1 stack can express a visible squat reference before investing in longer tracker training",
                "architecture": "reuses exp67 native metrics and swaps only the target selector to isolate reference-tracking feasibility",
                "security": "local MuJoCo/JAX run only; no credentials or external side effects",
                "qa": "raw native JSON per variant plus static reference probe and exp29 visible gate annotation",
                "skeptic": "without training a dedicated motion tracker, direct reference injection may still trade knee flexion for fall/slip",
            },
            "dod": [
                "static reference JSON shows the intended visible squat pose",
                "native rollout JSON shows whether stabilizer-conditioned tracking passes exp29 visible_8cm_gate",
            ],
        },
        "sources": [
            {
                "url": "https://www.unitree.com/g1/",
                "accessed": "2026-06-18",
                "note": "Official G1 specs list 23 to 43 joint motors, 6 DoF per leg, large hip/knee range, and knee torque values that make squat-like poses kinematically plausible.",
            },
            {
                "url": "https://arxiv.org/html/2507.07356v2",
                "accessed": "2026-06-18",
                "note": "UniTracker reports 29-DoF Unitree G1 whole-body motion tracking, including squatting among tracked real-world motions.",
            },
            {
                "url": "https://agile.human2humanoid.com/",
                "accessed": "2026-06-18",
                "note": "ASAP motivates pre-training motion tracking policies on retargeted human motions before sim-to-real alignment on Unitree G1.",
            },
            {
                "url": "https://huggingface.co/datasets/exptech/g1-moves",
                "accessed": "2026-06-18",
                "note": "G1 Moves provides retargeted Unitree G1 joint trajectories, processed RL training data, and trained policies, supporting the reference-motion route.",
            },
        ],
        "reference_probe": build_reference_probe(),
        "runs": [],
    }
    (out_dir / "visible_reference_probe.json").write_text(json.dumps(result["reference_probe"], indent=2), encoding="utf-8")
    for variant in variants():
        run = EXP67.native_eval(
            variant=variant,
            seconds=args.seconds,
            out_dir=out_dir / variant["attempt"],
        )
        run = annotate_visible(run)
        run["optimizer_score"] = optimizer_score(run)
        result["runs"].append(run)
    visible = [run for run in result["runs"] if run["visible_8cm_gate"]]
    no_fall = [run for run in result["runs"] if run["fell_at"] is None]
    best_optimizer = min(result["runs"], key=lambda run: run["optimizer_score"])
    best_no_fall = min(no_fall, key=lambda run: run["optimizer_score"], default=None)
    result["best_optimizer"] = {
        "attempt": best_optimizer["attempt"],
        "optimizer_score": best_optimizer["optimizer_score"],
        "visible_drop": best_optimizer["visible_drop"],
        "max_knee_delta_rad": best_optimizer["max_knee_delta_rad"],
        "max_hip_pitch_delta_rad": best_optimizer["max_hip_pitch_delta_rad"],
        "visible_gap": best_optimizer["visible_gap"],
        "visible_verdict": best_optimizer["visible_verdict"],
        "fell_at": best_optimizer["fell_at"],
    }
    result["best_no_fall"] = None if best_no_fall is None else {
        "attempt": best_no_fall["attempt"],
        "optimizer_score": best_no_fall["optimizer_score"],
        "visible_drop": best_no_fall["visible_drop"],
        "max_knee_delta_rad": best_no_fall["max_knee_delta_rad"],
        "max_hip_pitch_delta_rad": best_no_fall["max_hip_pitch_delta_rad"],
        "visible_gap": best_no_fall["visible_gap"],
        "visible_verdict": best_no_fall["visible_verdict"],
    }
    result["verdict"] = "PASS_VISIBLE_8CM_GATE" if visible else "FAIL_VISIBLE_8CM_GATE"
    write_summary(result, out_dir)
    (out_dir / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(result["verdict"], json.dumps({
        "reference_probe": result["reference_probe"],
        "best_optimizer": result["best_optimizer"],
        "best_no_fall": result["best_no_fall"],
    }, indent=2), flush=True)


if __name__ == "__main__":
    main()
