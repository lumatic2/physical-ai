"""Smoke-test the G1 + ball scene and ball-tap metrics."""

from __future__ import annotations

import json
from pathlib import Path

import mujoco
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
SCENE = ROOT / "experiments/03-digital-twin/web/assets/scenes/g1/scene_g1_ball.xml"
SPEC = ROOT / "experiments/14-skill-authoring/verify/g1_ball_tap.compiled.json"
VERIFY = Path(__file__).resolve().parent / "verify"


def main() -> None:
    VERIFY.mkdir(parents=True, exist_ok=True)
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    model = mujoco.MjModel.from_xml_path(str(SCENE))
    data = mujoco.MjData(model)
    key = model.keyframe("knees_bent_ball")
    data.qpos[:] = key.qpos
    data.ctrl[:] = key.ctrl
    mujoco.mj_forward(model, data)

    ball_joint = model.joint("soccer_ball_freejoint")
    ball_qadr = int(ball_joint.qposadr[0])
    ball_vadr = int(ball_joint.dofadr[0])
    initial = data.qpos[ball_qadr:ball_qadr + 3].copy()
    goal = np.array(spec["raw_target"]["goal_direction_xy"], dtype=float)
    goal = goal / np.linalg.norm(goal)

    # Metric smoke: inject a controlled x-directed ball velocity after settle.
    for _ in range(100):
        mujoco.mj_step(model, data)
    data.qvel[ball_vadr:ball_vadr + 3] = np.array([1.2, 0.0, 0.0])
    for _ in range(500):
        mujoco.mj_step(model, data)

    final = data.qpos[ball_qadr:ball_qadr + 3].copy()
    delta_xy = final[:2] - initial[:2]
    distance = float(np.linalg.norm(delta_xy))
    if distance > 1e-9:
        direction = delta_xy / distance
        direction_error = float(np.arccos(np.clip(np.dot(direction, goal), -1.0, 1.0)))
    else:
        direction_error = float("inf")

    result = {
        "scene": "experiments/03-digital-twin/web/assets/scenes/g1/scene_g1_ball.xml",
        "source_spec": "experiments/14-skill-authoring/verify/g1_ball_tap.compiled.json",
        "nq": int(model.nq),
        "nv": int(model.nv),
        "nu": int(model.nu),
        "nsensor": int(model.nsensor),
        "ball_initial_pos": initial.tolist(),
        "ball_final_pos": final.tolist(),
        "ball_distance": distance,
        "ball_direction_error_rad": direction_error,
        "min_required_distance": float(spec["raw_target"]["min_ball_distance_m"]),
        "verdict": "PASS" if distance > 0.1 and direction_error < 0.2 else "FAIL",
        "next": "Use the same ball body and metrics for foot-ball contact reward; this smoke injects velocity and does not test kicking.",
    }
    (VERIFY / "g1-ball-scene-smoke.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    report = [
        "# G1 Ball Scene Smoke",
        "",
        f"- Verdict: {result['verdict']}",
        f"- nq/nv/nu/nsensor: {result['nq']} / {result['nv']} / {result['nu']} / {result['nsensor']}",
        f"- Ball distance: {distance:.3f}m",
        f"- Direction error: {direction_error:.3f} rad",
        "",
        "The ball metric path is live. Kicking is not validated here; this is the M21 scene/metric gate.",
        "",
    ]
    (VERIFY / "g1-ball-scene-smoke.md").write_text("\n".join(report), encoding="utf-8")
    print(result["verdict"], f"distance={distance:.3f}", f"direction_error={direction_error:.3f}")


if __name__ == "__main__":
    main()
