"""Evaluate crossing-leg kick feasibility for the G1 ball scene.

This is a kinematic feasibility probe, not a learned rabona policy. It checks
whether the right foot can cross the body midline, avoid foot-foot contact,
touch the ball, move the ball toward the target direction, and remain above the
fall-height threshold in the existing MuJoCo scene.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import mujoco
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
SCENE = ROOT / "experiments/03-digital-twin/web/assets/scenes/g1/scene_g1_ball.xml"
VERIFY = Path(__file__).resolve().parent / "verify"


@dataclass(frozen=True)
class Candidate:
    name: str
    target: tuple[float, float, float, float, float]
    ball_pos: tuple[float, float, float]


CANDIDATES = [
    Candidate("high_cross", (-0.45, 0.90, 0.80, 0.45, -0.40), (0.20, 0.25, 0.06)),
    Candidate("mid_cross", (-0.45, 0.75, 0.80, 0.45, -0.40), (0.23, 0.17, 0.06)),
    Candidate("low_cross", (-0.45, 0.60, 0.40, 0.35, -0.40), (0.21, 0.165, 0.06)),
    Candidate("back_cross", (-0.60, 0.30, -0.40, 0.65, -0.40), (0.20, 0.153, 0.06)),
]


RIGHT_LEG_QPOS = {
    "right_hip_pitch_joint": 13,
    "right_hip_roll_joint": 14,
    "right_hip_yaw_joint": 15,
    "right_knee_joint": 16,
    "right_ankle_pitch_joint": 17,
}


def mj_id(model: mujoco.MjModel, objtype: mujoco.mjtObj, name: str) -> int:
    return mujoco.mj_name2id(model, objtype, name)


def direction_error(delta_xy: np.ndarray) -> float | None:
    distance = float(np.linalg.norm(delta_xy))
    if distance < 1e-9:
        return None
    direction = delta_xy / distance
    return float(np.arccos(np.clip(direction.dot(np.array([1.0, 0.0])), -1.0, 1.0)))


def joint_limit_report(model: mujoco.MjModel, candidate: Candidate) -> dict:
    names = list(RIGHT_LEG_QPOS)
    values = candidate.target
    margins = {}
    violations = []
    for name, value in zip(names, values):
        joint_id = mj_id(model, mujoco.mjtObj.mjOBJ_JOINT, name)
        low, high = model.jnt_range[joint_id]
        margin = min(value - low, high - value)
        margins[name] = float(margin)
        if value < low or value > high:
            violations.append(name)
    return {
        "violations": violations,
        "min_margin_rad": min(margins.values()),
        "margins_rad": margins,
    }


def crossing_pose(base_qpos: np.ndarray, candidate: Candidate, progress: float) -> np.ndarray:
    qpos = base_qpos.copy()
    for qpos_index, target in zip(RIGHT_LEG_QPOS.values(), candidate.target):
        qpos[qpos_index] = (1.0 - progress) * qpos[qpos_index] + progress * target
    return qpos


def evaluate_candidate(model: mujoco.MjModel, candidate: Candidate) -> dict:
    data = mujoco.MjData(model)
    key = model.keyframe("knees_bent_ball")
    data.qpos[:] = key.qpos
    data.ctrl[:] = key.ctrl

    ball_joint = model.joint("soccer_ball_freejoint")
    ball_qadr = int(ball_joint.qposadr[0])
    ball_vadr = int(ball_joint.dofadr[0])
    data.qpos[ball_qadr:ball_qadr + 3] = np.array(candidate.ball_pos, dtype=float)
    mujoco.mj_forward(model, data)

    base_qpos = data.qpos.copy()
    initial_ball = data.qpos[ball_qadr:ball_qadr + 3].copy()
    ball_geom = mj_id(model, mujoco.mjtObj.mjOBJ_GEOM, "soccer_ball_geom")
    right_foot = mj_id(model, mujoco.mjtObj.mjOBJ_GEOM, "right_foot")
    left_foot = mj_id(model, mujoco.mjtObj.mjOBJ_GEOM, "left_foot")

    contact_frames = 0
    foot_foot_contact_frames = 0
    first_contact_time = None
    max_right_foot_y = float(data.geom_xpos[right_foot][1])
    min_base_height = float(data.qpos[2])
    max_contact_force = 0.0

    steps = int(2.0 / model.opt.timestep)
    for step in range(steps):
        t = step * model.opt.timestep
        progress = min(1.0, max(0.0, (t - 0.10) / 0.45))
        robot_qpos = crossing_pose(base_qpos, candidate, progress)

        ball_qpos = data.qpos[ball_qadr:ball_qadr + 7].copy()
        ball_qvel = data.qvel[ball_vadr:ball_vadr + 6].copy()
        data.qpos[:] = robot_qpos
        data.qpos[ball_qadr:ball_qadr + 7] = ball_qpos
        data.qvel[:] = 0.0
        data.qvel[ball_vadr:ball_vadr + 6] = ball_qvel
        data.ctrl[:] = key.ctrl

        mujoco.mj_step(model, data)
        max_right_foot_y = max(max_right_foot_y, float(data.geom_xpos[right_foot][1]))
        min_base_height = min(min_base_height, float(data.qpos[2]))

        had_ball_contact = False
        had_foot_contact = False
        for contact_index in range(data.ncon):
            contact = data.contact[contact_index]
            geoms = {contact.geom1, contact.geom2}
            if geoms == {right_foot, ball_geom}:
                had_ball_contact = True
                force = np.zeros(6)
                mujoco.mj_contactForce(model, data, contact_index, force)
                max_contact_force = max(max_contact_force, float(np.linalg.norm(force[:3])))
            if geoms == {right_foot, left_foot}:
                had_foot_contact = True
        if had_ball_contact:
            contact_frames += 1
            if first_contact_time is None:
                first_contact_time = t
        if had_foot_contact:
            foot_foot_contact_frames += 1

    final_ball = data.qpos[ball_qadr:ball_qadr + 3].copy()
    delta_xy = final_ball[:2] - initial_ball[:2]
    distance = float(np.linalg.norm(delta_xy))
    error = direction_error(delta_xy)
    limits = joint_limit_report(model, candidate)
    fell = bool(min_base_height < 0.58)
    pass_gate = bool(
        max_right_foot_y > 0.05
        and contact_frames > 0
        and foot_foot_contact_frames == 0
        and distance >= 0.60
        and error is not None
        and error < 0.20
        and not fell
        and not limits["violations"]
    )

    return {
        "name": candidate.name,
        "target_right_leg": {
            "right_hip_pitch": candidate.target[0],
            "right_hip_roll": candidate.target[1],
            "right_hip_yaw": candidate.target[2],
            "right_knee": candidate.target[3],
            "right_ankle_pitch": candidate.target[4],
        },
        "ball_initial_pos": initial_ball.tolist(),
        "ball_final_pos": final_ball.tolist(),
        "crossing": {
            "max_right_foot_y_m": max_right_foot_y,
            "crossed_midline": bool(max_right_foot_y > 0.0),
        },
        "contact_frames": contact_frames,
        "first_contact_time_s": first_contact_time,
        "max_contact_force": max_contact_force,
        "foot_foot_contact_frames": foot_foot_contact_frames,
        "ball_distance_m": distance,
        "ball_direction_error_rad": error,
        "min_base_height_m": min_base_height,
        "fell": fell,
        "joint_limits": limits,
        "pass": pass_gate,
    }


def main() -> None:
    VERIFY.mkdir(parents=True, exist_ok=True)
    model = mujoco.MjModel.from_xml_path(str(SCENE))
    candidates = [evaluate_candidate(model, candidate) for candidate in CANDIDATES]
    passing = [candidate for candidate in candidates if candidate["pass"]]
    best = max(
        candidates,
        key=lambda candidate: (
            candidate["pass"],
            -candidate["foot_foot_contact_frames"],
            candidate["ball_distance_m"],
            candidate["crossing"]["max_right_foot_y_m"],
        ),
    )
    result = {
        "schema_version": "0.1",
        "scene": "experiments/03-digital-twin/web/assets/scenes/g1/scene_g1_ball.xml",
        "method": "scripted right-leg crossing sweep with MuJoCo ball/contact dynamics",
        "thresholds": {
            "min_crossing_y_m": 0.05,
            "min_contact_frames": 1,
            "max_foot_foot_contact_frames": 0,
            "min_ball_distance_m": 0.60,
            "max_direction_error_rad": 0.20,
            "min_base_height_m": 0.58,
        },
        "verdict": "PASS" if passing else "FAIL",
        "best_candidate": best["name"],
        "candidates": candidates,
        "limitations": [
            "This validates kinematic feasibility and scene observability, not a learned rabona controller.",
            "The base pose is scripted; dynamic balance under policy control remains separate future work.",
        ],
    }
    json_path = VERIFY / "g1-crossing-leg-kick-feasibility.json"
    json_path.write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf-8")

    report = [
        "# G1 Crossing-Leg Kick Feasibility",
        "",
        f"- Verdict: {result['verdict']}",
        f"- Best candidate: {best['name']}",
        f"- Max right-foot crossing y: {best['crossing']['max_right_foot_y_m']:.3f}m",
        f"- Foot-ball contact frames: {best['contact_frames']}",
        f"- Foot-foot contact frames: {best['foot_foot_contact_frames']}",
        f"- Ball distance: {best['ball_distance_m']:.3f}m",
        f"- Direction error: {best['ball_direction_error_rad']:.3f} rad",
        f"- Min base height: {best['min_base_height_m']:.3f}m",
        f"- Fell: {best['fell']}",
        "",
        "The crossing-leg pose is feasible in the current scene as a scripted probe.",
        "This should be treated as permission to define a future learned external-object task, not proof of a learned rabona skill.",
        "",
    ]
    (VERIFY / "g1-crossing-leg-kick-feasibility.md").write_text("\n".join(report), encoding="utf-8")
    print(
        result["verdict"],
        f"best={best['name']}",
        f"cross_y={best['crossing']['max_right_foot_y_m']:.3f}",
        f"contact_frames={best['contact_frames']}",
        f"footfoot={best['foot_foot_contact_frames']}",
        f"distance={best['ball_distance_m']:.3f}",
        f"direction_error={best['ball_direction_error_rad']:.3f}",
        f"fell={best['fell']}",
    )


if __name__ == "__main__":
    main()
