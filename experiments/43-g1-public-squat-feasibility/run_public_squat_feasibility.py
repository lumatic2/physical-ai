"""Refresh public and local feasibility evidence for G1 visible squat."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import mujoco
import numpy as np


EXP_DIR = Path(__file__).resolve().parent
ROOT = EXP_DIR.parents[1]
VERIFY = EXP_DIR / "verify"
EXP36_PATH = ROOT / "experiments/36-g1-wbc-ik-squat-prototype/run_ik_squat.py"

VISIBLE_GATE = {
    "pelvis_drop_m": 0.08,
    "knee_delta_rad": 0.60,
    "hip_pitch_delta_rad": 0.35,
}

PUBLIC_EVIDENCE = [
    {
        "source": "Unitree G1-Comp product page",
        "url": "https://www.unitree.com/robocup/",
        "accessed": "2026-06-18",
        "claim": "standing height 1320mm, folded height 690mm, 6 DoF per leg, knee 0~165deg, hip pitch +/-154deg, knee torque 120N.m",
        "weight": "official-spec",
    },
    {
        "source": "IEEE Robots Guide: Unitree G1",
        "url": "https://robotsguide.com/robots/unitree-g1",
        "accessed": "2026-06-18",
        "claim": "shows Unitree G1 squatting down all the way; lists 130cm height, 35kg mass, 90Nm knee torque with EDU 120Nm",
        "weight": "credible-public-media",
    },
    {
        "source": "HuB: Learning Extreme Humanoid Balance",
        "url": "https://hub-robot.github.io/",
        "accessed": "2026-06-18",
        "claim": "reports validation on Unitree G1 and includes Deep Squat among extreme balance tasks",
        "weight": "research-project",
    },
]


def load_exp36():
    spec = importlib.util.spec_from_file_location("exp36_ik_squat", EXP36_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {EXP36_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EXP36 = load_exp36()


def joint_value(model: mujoco.MjModel, qpos: np.ndarray, name: str) -> float:
    return float(qpos[model.joint(name).qposadr[0]])


def static_drop_probe(drop: float) -> dict:
    env = EXP36.EXP28.ContactAwareSquat(
        stage_height=0.67,
        controller_blend=0.0,
        freeze_phase=True,
        blend_schedule="squat",
        reference_scale=1.0,
        config_overrides={"impl": "jax"},
    )
    model = env.mj_model
    key = model.keyframe("knees_bent")
    start_qpos = key.qpos.copy()
    foot_site_ids = np.asarray(env._feet_site_id)
    ik = EXP36.solve_foot_fixed_target(model, start_qpos, foot_site_ids, drop)

    data = mujoco.MjData(model)
    data.qpos[:] = start_qpos
    data.qpos[2] = ik["target_height"]
    data.qpos[7:22] = np.asarray(ik["lower_body_target"], dtype=np.float64)
    mujoco.mj_forward(model, data)

    knee_delta = max(
        abs(joint_value(model, data.qpos, "left_knee_joint") - joint_value(model, start_qpos, "left_knee_joint")),
        abs(joint_value(model, data.qpos, "right_knee_joint") - joint_value(model, start_qpos, "right_knee_joint")),
    )
    hip_delta = max(
        abs(joint_value(model, data.qpos, "left_hip_pitch_joint") - joint_value(model, start_qpos, "left_hip_pitch_joint")),
        abs(joint_value(model, data.qpos, "right_hip_pitch_joint") - joint_value(model, start_qpos, "right_hip_pitch_joint")),
    )
    ankle_delta = max(
        abs(joint_value(model, data.qpos, "left_ankle_pitch_joint") - joint_value(model, start_qpos, "left_ankle_pitch_joint")),
        abs(joint_value(model, data.qpos, "right_ankle_pitch_joint") - joint_value(model, start_qpos, "right_ankle_pitch_joint")),
    )

    return {
        "drop_m": drop,
        "target_height_m": ik["target_height"],
        "ik_success": ik["success"],
        "ik_cost": ik["cost"],
        "ik_max_foot_error_m": ik["max_foot_error"],
        "knee_delta_rad": knee_delta,
        "hip_pitch_delta_rad": hip_delta,
        "ankle_pitch_delta_rad": ankle_delta,
        "visible_gate": {
            "pelvis_drop_pass": drop >= VISIBLE_GATE["pelvis_drop_m"],
            "knee_delta_pass": knee_delta >= VISIBLE_GATE["knee_delta_rad"],
            "hip_pitch_delta_pass": hip_delta >= VISIBLE_GATE["hip_pitch_delta_rad"],
        },
    }


def write_summary(result: dict) -> None:
    lines = [
        "# G1 public squat feasibility refresh",
        "",
        "## Verdict",
        "",
        f"- Public feasibility: {result['verdict']['public']}",
        f"- Local static target feasibility: {result['verdict']['local_static']}",
        f"- Dynamic policy status: {result['verdict']['dynamic_policy']}",
        "",
        "## Static probes",
        "",
        "| Drop target | IK max foot error | Knee delta | Hip pitch delta | Visible pose gate |",
        "|---:|---:|---:|---:|---|",
    ]
    for probe in result["static_probes"]:
        gate = probe["visible_gate"]
        gate_text = "PASS" if all(gate.values()) else "PENDING"
        lines.append(
            f"| {probe['drop_m']:.2f}m | {probe['ik_max_foot_error_m']:.4f}m | "
            f"{probe['knee_delta_rad']:.3f}rad | {probe['hip_pitch_delta_rad']:.3f}rad | {gate_text} |"
        )
    lines.extend([
        "",
        "## Interpretation",
        "",
        "The public evidence supports that Unitree G1-class hardware can assume a deep squat posture, and the local MJCF can solve foot-fixed visible squat targets. This does not mean the current learned policy can dynamically squat; prior native rollouts still show shallow stable motion or collapse. The next controller experiment should therefore treat squat as a WBC/contact-force problem, not a joint-range problem.",
    ])
    (VERIFY / "public-squat-feasibility.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    VERIFY.mkdir(parents=True, exist_ok=True)
    probes = [static_drop_probe(drop) for drop in (0.08, 0.12, 0.16)]
    static_pass = all(probe["ik_max_foot_error_m"] <= 0.002 for probe in probes)
    visible_pose_pass = any(all(probe["visible_gate"].values()) for probe in probes)
    result = {
        "visible_gate": VISIBLE_GATE,
        "public_evidence": PUBLIC_EVIDENCE,
        "static_probes": probes,
        "verdict": {
            "public": "SUPPORTED_BY_OFFICIAL_SPECS_AND_PUBLIC_DEEP_SQUAT_EVIDENCE",
            "local_static": "KINEMATICALLY_PLAUSIBLE"
            if static_pass and visible_pose_pass
            else "STATIC_TARGET_PENDING",
            "dynamic_policy": "UNPROVEN_CURRENT_POLICY_NEEDS_WBC_CONTACT_FORCE_CONTROL",
            "next_action": "run_qplite_wbc_before_browser_replay",
        },
    }
    (VERIFY / "public-squat-feasibility.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    write_summary(result)
    print(json.dumps(result["verdict"], indent=2), flush=True)


if __name__ == "__main__":
    main()
