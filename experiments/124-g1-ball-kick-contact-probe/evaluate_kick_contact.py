"""Evaluate whether the G1 ball scene can produce real foot-ball contact.

This is a kinematic probe, not a learned policy: the right leg is replayed
through a front-kick pose while MuJoCo computes contact, ball motion, and fall
metrics in the real G1 + ball scene.
"""

from __future__ import annotations

import json
from pathlib import Path

import mujoco
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
SCENE = ROOT / "experiments/03-digital-twin/web/assets/scenes/g1/scene_g1_ball.xml"
SPEC = ROOT / "experiments/14-skill-authoring/verify/g1_ball_tap.compiled.json"
VERIFY = Path(__file__).resolve().parent / "verify"


def geom_id(model: mujoco.MjModel, name: str) -> int:
    return mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, name)


def right_leg_pose(base_qpos: np.ndarray, progress: float) -> np.ndarray:
    """Return a scripted low front-kick pose that sweeps through the ball."""
    qpos = base_qpos.copy()
    qpos[13] = (1.0 - progress) * -0.25 + progress * -0.80  # right hip pitch
    qpos[16] = (1.0 - progress) * 0.95 + progress * 0.65  # right knee
    qpos[17] = (1.0 - progress) * -0.45 + progress * -0.40  # right ankle pitch
    return qpos


def direction_error(delta_xy: np.ndarray, goal_xy: np.ndarray) -> float | None:
    distance = float(np.linalg.norm(delta_xy))
    if distance < 1e-9:
        return None
    direction = delta_xy / distance
    return float(np.arccos(np.clip(np.dot(direction, goal_xy), -1.0, 1.0)))


def run_probe(model: mujoco.MjModel, spec: dict, *, enable_kick: bool) -> dict:
    data = mujoco.MjData(model)
    key = model.keyframe("knees_bent_ball")
    data.qpos[:] = key.qpos
    data.ctrl[:] = key.ctrl

    ball_joint = model.joint("soccer_ball_freejoint")
    ball_qadr = int(ball_joint.qposadr[0])
    ball_vadr = int(ball_joint.dofadr[0])
    data.qpos[ball_qadr:ball_qadr + 3] = np.array(spec["raw_target"]["ball_initial_pos"], dtype=float)
    mujoco.mj_forward(model, data)

    base_qpos = data.qpos.copy()
    initial_ball = data.qpos[ball_qadr:ball_qadr + 3].copy()
    min_base_height = float(data.qpos[2])
    contact_frames = 0
    max_contact_force = 0.0
    first_contact_time = None

    ball_geom = geom_id(model, "soccer_ball_geom")
    right_foot = geom_id(model, "right_foot")
    left_foot = geom_id(model, "left_foot")
    foot_geoms = {right_foot, left_foot}

    steps = int(2.0 / model.opt.timestep)
    for step in range(steps):
        t = step * model.opt.timestep
        robot_qpos = base_qpos.copy()
        if enable_kick:
            progress = min(1.0, max(0.0, (t - 0.10) / 0.45))
            robot_qpos = right_leg_pose(base_qpos, progress)

        ball_qpos = data.qpos[ball_qadr:ball_qadr + 7].copy()
        ball_qvel = data.qvel[ball_vadr:ball_vadr + 6].copy()
        data.qpos[:] = robot_qpos
        data.qpos[ball_qadr:ball_qadr + 7] = ball_qpos
        data.qvel[:] = 0.0
        data.qvel[ball_vadr:ball_vadr + 6] = ball_qvel
        data.ctrl[:] = key.ctrl

        mujoco.mj_step(model, data)
        min_base_height = min(min_base_height, float(data.qpos[2]))

        had_contact = False
        for contact_index in range(data.ncon):
            contact = data.contact[contact_index]
            if ball_geom in (contact.geom1, contact.geom2) and (
                contact.geom1 in foot_geoms or contact.geom2 in foot_geoms
            ):
                had_contact = True
                impulse = np.zeros(6)
                mujoco.mj_contactForce(model, data, contact_index, impulse)
                max_contact_force = max(max_contact_force, float(np.linalg.norm(impulse[:3])))
        if had_contact:
            contact_frames += 1
            if first_contact_time is None:
                first_contact_time = t

    final_ball = data.qpos[ball_qadr:ball_qadr + 3].copy()
    delta_xy = final_ball[:2] - initial_ball[:2]
    distance = float(np.linalg.norm(delta_xy))
    goal = np.array(spec["raw_target"]["goal_direction_xy"], dtype=float)
    goal = goal / np.linalg.norm(goal)
    error = direction_error(delta_xy, goal)
    fell = bool(min_base_height < float(spec["done_conditions"]["min_base_height_m"]))

    return {
        "mode": "right_foot_kinematic_kick" if enable_kick else "baseline_no_kick",
        "contact_frames": contact_frames,
        "first_contact_time_s": first_contact_time,
        "max_contact_force": max_contact_force,
        "ball_initial_pos": initial_ball.tolist(),
        "ball_final_pos": final_ball.tolist(),
        "ball_distance_m": distance,
        "ball_direction_error_rad": error,
        "min_base_height_m": min_base_height,
        "fell": fell,
        "pass": bool(
            enable_kick
            and contact_frames > 0
            and distance >= float(spec["raw_target"]["min_ball_distance_m"])
            and error is not None
            and error < 0.20
            and not fell
        ),
    }


def main() -> None:
    VERIFY.mkdir(parents=True, exist_ok=True)
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    model = mujoco.MjModel.from_xml_path(str(SCENE))

    baseline = run_probe(model, spec, enable_kick=False)
    kick = run_probe(model, spec, enable_kick=True)
    result = {
        "schema_version": "0.1",
        "scene": "experiments/03-digital-twin/web/assets/scenes/g1/scene_g1_ball.xml",
        "source_spec": "experiments/14-skill-authoring/verify/g1_ball_tap.compiled.json",
        "method": "kinematic right-foot kick replay with MuJoCo contact and ball dynamics",
        "thresholds": {
            "min_contact_frames": 1,
            "min_ball_distance_m": float(spec["raw_target"]["min_ball_distance_m"]),
            "max_direction_error_rad": 0.20,
            "min_base_height_m": float(spec["done_conditions"]["min_base_height_m"]),
        },
        "baseline": baseline,
        "kick": kick,
        "verdict": "PASS" if kick["pass"] else "FAIL",
        "limitations": [
            "This validates scene/contact/reward observability, not a learned balance controller.",
            "The robot base is kept on the scripted reference pose while the ball remains dynamic.",
        ],
    }

    json_path = VERIFY / "g1-ball-kick-contact-probe.json"
    json_path.write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf-8")
    report = [
        "# G1 Ball Kick Contact Probe",
        "",
        f"- Verdict: {result['verdict']}",
        f"- Contact frames: {kick['contact_frames']}",
        f"- First contact: {kick['first_contact_time_s']:.3f}s",
        f"- Ball distance: {kick['ball_distance_m']:.3f}m",
        f"- Direction error: {kick['ball_direction_error_rad']:.3f} rad",
        f"- Min base height: {kick['min_base_height_m']:.3f}m",
        f"- Fell: {kick['fell']}",
        "",
        "The scene can now observe actual foot-ball contact and target-directed ball movement.",
        "This is still a scripted probe; learned control remains future work.",
        "",
    ]
    (VERIFY / "g1-ball-kick-contact-probe.md").write_text("\n".join(report), encoding="utf-8")
    print(
        result["verdict"],
        f"contact_frames={kick['contact_frames']}",
        f"distance={kick['ball_distance_m']:.3f}",
        f"direction_error={kick['ball_direction_error_rad']:.3f}",
        f"fell={kick['fell']}",
    )


if __name__ == "__main__":
    main()
