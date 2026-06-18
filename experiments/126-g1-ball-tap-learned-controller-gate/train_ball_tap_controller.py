"""Train and evaluate a low-dimensional G1 ball-tap controller.

This is a trainable controller gate, not a neural RL policy. The harness
optimizes a small open-loop right-leg controller against the same native MuJoCo
metrics used by M21: foot-ball contact, ball distance, direction error, and
fall/no-fall.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

import mujoco
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
SCENE = ROOT / "experiments/03-digital-twin/web/assets/scenes/g1/scene_g1_ball.xml"
SPEC = ROOT / "experiments/14-skill-authoring/verify/g1_ball_tap.compiled.json"
VERIFY = Path(__file__).resolve().parent / "verify"


@dataclass(frozen=True)
class Controller:
    right_hip_pitch: float
    right_hip_roll: float
    right_hip_yaw: float
    right_knee: float
    right_ankle_pitch: float
    swing_start_s: float
    swing_duration_s: float


RIGHT_LEG_QPOS = {
    "right_hip_pitch_joint": 13,
    "right_hip_roll_joint": 14,
    "right_hip_yaw_joint": 15,
    "right_knee_joint": 16,
    "right_ankle_pitch_joint": 17,
}


SEED_CONTROLLERS = [
    # M21-style front tap prior. The optimizer can keep or perturb it.
    Controller(-0.80, 0.00, 0.00, 0.65, -0.40, 0.10, 0.45),
    Controller(-0.85, -0.05, 0.05, 0.60, -0.35, 0.08, 0.42),
    Controller(-0.75, 0.05, -0.05, 0.72, -0.45, 0.12, 0.50),
]


def mj_id(model: mujoco.MjModel, objtype: mujoco.mjtObj, name: str) -> int:
    return mujoco.mj_name2id(model, objtype, name)


def direction_error(delta_xy: np.ndarray, goal_xy: np.ndarray) -> float | None:
    distance = float(np.linalg.norm(delta_xy))
    if distance < 1e-9:
        return None
    direction = delta_xy / distance
    return float(np.arccos(np.clip(direction.dot(goal_xy), -1.0, 1.0)))


def clamp_controller(model: mujoco.MjModel, controller: Controller) -> Controller:
    values = []
    for name, value in zip(RIGHT_LEG_QPOS, asdict(controller).values()):
        if not name.endswith("_joint"):
            continue
        joint_id = mj_id(model, mujoco.mjtObj.mjOBJ_JOINT, name)
        low, high = model.jnt_range[joint_id]
        values.append(float(np.clip(value, low, high)))
    return Controller(
        values[0],
        values[1],
        values[2],
        values[3],
        values[4],
        float(np.clip(controller.swing_start_s, 0.02, 0.40)),
        float(np.clip(controller.swing_duration_s, 0.18, 0.85)),
    )


def controller_pose(base_qpos: np.ndarray, controller: Controller, t: float) -> np.ndarray:
    qpos = base_qpos.copy()
    progress = min(1.0, max(0.0, (t - controller.swing_start_s) / controller.swing_duration_s))
    smooth = progress * progress * (3.0 - 2.0 * progress)
    targets = [
        controller.right_hip_pitch,
        controller.right_hip_roll,
        controller.right_hip_yaw,
        controller.right_knee,
        controller.right_ankle_pitch,
    ]
    for qpos_index, target in zip(RIGHT_LEG_QPOS.values(), targets):
        qpos[qpos_index] = (1.0 - smooth) * qpos[qpos_index] + smooth * target
    return qpos


def evaluate(
    model: mujoco.MjModel,
    spec: dict,
    controller: Controller,
    *,
    capture_trajectory: bool = False,
) -> dict:
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
    ball_geom = mj_id(model, mujoco.mjtObj.mjOBJ_GEOM, "soccer_ball_geom")
    right_foot = mj_id(model, mujoco.mjtObj.mjOBJ_GEOM, "right_foot")
    min_base_height = float(data.qpos[2])
    contact_frames = 0
    first_contact_time = None
    max_contact_force = 0.0
    energy = 0.0
    trajectory = []

    steps = int(float(spec["done_conditions"]["max_time_s"]) / model.opt.timestep)
    sample_every = max(1, int(round((1.0 / 50.0) / model.opt.timestep)))
    for step in range(steps):
        t = step * model.opt.timestep
        robot_qpos = controller_pose(base_qpos, controller, t)
        ball_qpos = data.qpos[ball_qadr:ball_qadr + 7].copy()
        ball_qvel = data.qvel[ball_vadr:ball_vadr + 6].copy()

        data.qpos[:] = robot_qpos
        data.qpos[ball_qadr:ball_qadr + 7] = ball_qpos
        data.qvel[:] = 0.0
        data.qvel[ball_vadr:ball_vadr + 6] = ball_qvel
        data.ctrl[:] = key.ctrl
        mujoco.mj_step(model, data)

        min_base_height = min(min_base_height, float(data.qpos[2]))
        energy += float(np.sum(np.square(np.array(list(asdict(controller).values())[:5]))))

        had_contact = False
        for contact_index in range(data.ncon):
            contact = data.contact[contact_index]
            if {contact.geom1, contact.geom2} == {right_foot, ball_geom}:
                had_contact = True
                force = np.zeros(6)
                mujoco.mj_contactForce(model, data, contact_index, force)
                max_contact_force = max(max_contact_force, float(np.linalg.norm(force[:3])))
        if had_contact:
            contact_frames += 1
            if first_contact_time is None:
                first_contact_time = t
        if capture_trajectory and step % sample_every == 0:
            trajectory.append(
                {
                    "t": float(t),
                    "qpos": data.qpos.copy().tolist(),
                    "ball_pos": data.qpos[ball_qadr:ball_qadr + 3].copy().tolist(),
                }
            )

    final_ball = data.qpos[ball_qadr:ball_qadr + 3].copy()
    delta_xy = final_ball[:2] - initial_ball[:2]
    distance = float(np.linalg.norm(delta_xy))
    goal = np.array(spec["raw_target"]["goal_direction_xy"], dtype=float)
    goal = goal / np.linalg.norm(goal)
    error = direction_error(delta_xy, goal)
    fell = bool(min_base_height < float(spec["done_conditions"]["min_base_height_m"]))
    aligned_distance = 0.0
    if distance > 1e-9:
        aligned_distance = float(delta_xy.dot(goal))
    pass_gate = bool(
        contact_frames > 0
        and distance >= float(spec["raw_target"]["min_ball_distance_m"])
        and error is not None
        and error < 0.20
        and not fell
    )
    reward = (
        2.0 * aligned_distance
        + 0.02 * min(contact_frames, 80)
        - (0.0 if error is None else 0.25 * error)
        - (4.0 if fell else 0.0)
        - 1e-5 * energy
    )
    result = {
        "controller": asdict(controller),
        "contact_frames": contact_frames,
        "first_contact_time_s": first_contact_time,
        "max_contact_force": max_contact_force,
        "ball_initial_pos": initial_ball.tolist(),
        "ball_final_pos": final_ball.tolist(),
        "ball_distance_m": distance,
        "aligned_ball_distance_m": aligned_distance,
        "ball_direction_error_rad": error,
        "min_base_height_m": min_base_height,
        "fell": fell,
        "energy_proxy": energy,
        "reward": reward,
        "pass": pass_gate,
    }
    if capture_trajectory:
        result["trajectory"] = trajectory
    return result


def mutate(rng: np.random.Generator, model: mujoco.MjModel, parent: Controller, scale: float) -> Controller:
    values = np.array(list(asdict(parent).values()), dtype=float)
    noise = np.array([0.18, 0.10, 0.12, 0.16, 0.08, 0.04, 0.08]) * scale
    candidate = Controller(*(values + rng.normal(0.0, noise)))
    return clamp_controller(model, candidate)


def train(model: mujoco.MjModel, spec: dict) -> dict:
    rng = np.random.default_rng(25)
    population = [clamp_controller(model, controller) for controller in SEED_CONTROLLERS]
    trace = []
    best_result = None
    best_controller = population[0]

    for generation in range(5):
        if generation > 0:
            elite = [Controller(**entry) for entry in trace[-1]["elite"]]
            population = elite[:]
            while len(population) < 30:
                parent = elite[int(rng.integers(0, len(elite)))]
                population.append(mutate(rng, model, parent, scale=1.0 / generation))

        evaluated = [evaluate(model, spec, controller) for controller in population]
        evaluated.sort(key=lambda item: item["reward"], reverse=True)
        if best_result is None or evaluated[0]["reward"] > best_result["reward"]:
            best_result = evaluated[0]
            best_controller = Controller(**best_result["controller"])
        trace.append(
            {
                "generation": generation,
                "population": len(population),
                "best_reward": evaluated[0]["reward"],
                "best_pass": evaluated[0]["pass"],
                "best_distance_m": evaluated[0]["ball_distance_m"],
                "best_direction_error_rad": evaluated[0]["ball_direction_error_rad"],
                "best_contact_frames": evaluated[0]["contact_frames"],
                "elite": [item["controller"] for item in evaluated[:5]],
            }
        )

    assert best_result is not None
    final_eval = evaluate(model, spec, best_controller, capture_trajectory=True)
    return {
        "seed": 25,
        "optimizer": "seeded random search over 7 controller parameters",
        "generations": trace,
        "best_controller": asdict(best_controller),
        "final_eval": final_eval,
    }


def main() -> None:
    VERIFY.mkdir(parents=True, exist_ok=True)
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    model = mujoco.MjModel.from_xml_path(str(SCENE))
    training = train(model, spec)
    final_eval = training["final_eval"]
    trajectory = final_eval.pop("trajectory")

    result = {
        "schema_version": "0.1",
        "scene": "experiments/03-digital-twin/web/assets/scenes/g1/scene_g1_ball.xml",
        "source_spec": "experiments/14-skill-authoring/verify/g1_ball_tap.compiled.json",
        "method": "trainable low-dimensional open-loop controller optimized by seeded random search",
        "thresholds": {
            "min_contact_frames": 1,
            "min_ball_distance_m": float(spec["raw_target"]["min_ball_distance_m"]),
            "max_direction_error_rad": 0.20,
            "min_base_height_m": float(spec["done_conditions"]["min_base_height_m"]),
        },
        "training": training,
        "verdict": "PASS" if final_eval["pass"] else "FAIL",
        "limitations": [
            "This is a trainable controller gate, not a neural policy or full RL result.",
            "The base pose is scripted; learned dynamic balance remains a future controller problem.",
        ],
    }

    json_path = VERIFY / "g1-ball-tap-learned-controller-gate.json"
    json_path.write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf-8")
    trajectory_path = VERIFY / "g1-ball-tap-learned-controller-trajectory.json"
    trajectory_path.write_text(
        json.dumps(
            {
                "fps": 50,
                "nq": int(model.nq),
                "frames": trajectory,
                "controller": training["best_controller"],
            },
            indent=2,
            allow_nan=False,
        ),
        encoding="utf-8",
    )
    report = [
        "# G1 Ball Tap Learned Controller Gate",
        "",
        f"- Verdict: {result['verdict']}",
        f"- Optimizer: {training['optimizer']}",
        f"- Contact frames: {final_eval['contact_frames']}",
        f"- Ball distance: {final_eval['ball_distance_m']:.3f}m",
        f"- Direction error: {final_eval['ball_direction_error_rad']:.3f} rad",
        f"- Min base height: {final_eval['min_base_height_m']:.3f}m",
        f"- Fell: {final_eval['fell']}",
        f"- Reward: {final_eval['reward']:.3f}",
        "",
        "This closes M25 as a trainable-controller gate. It does not claim a full neural RL policy.",
        "",
    ]
    (VERIFY / "g1-ball-tap-learned-controller-gate.md").write_text("\n".join(report), encoding="utf-8")
    print(
        result["verdict"],
        f"contact_frames={final_eval['contact_frames']}",
        f"distance={final_eval['ball_distance_m']:.3f}",
        f"direction_error={final_eval['ball_direction_error_rad']:.3f}",
        f"fell={final_eval['fell']}",
    )


if __name__ == "__main__":
    main()
