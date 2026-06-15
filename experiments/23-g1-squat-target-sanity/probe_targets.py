"""Probe whether G1 squat targets can directly produce native height drop.

This experiment separates target feasibility from PPO reward design. If direct
position targets cannot lower the base or only lower it by falling, another
reward-scale iteration is the wrong next move.
"""

from __future__ import annotations

import json
from pathlib import Path

import mujoco
import numpy as np


EXP_DIR = Path(__file__).resolve().parent
ROOT = EXP_DIR.parents[1]
VERIFY = EXP_DIR / "verify"
REFERENCE = ROOT / "experiments/17-motion-to-policy-loop/verify/g1_squat_reference.compiled.json"
SCENE = ROOT / "experiments/03-digital-twin/web/assets/scenes/g1/scene_g1_policy.xml"


def load_reference() -> tuple[np.ndarray, np.ndarray]:
    compiled = json.loads(REFERENCE.read_text(encoding="utf-8"))
    samples = compiled["trajectory"]["samples"]
    joints = np.asarray([sample["joint_targets"] for sample in samples], dtype=np.float64)
    heights = np.asarray([sample["base_height"] for sample in samples], dtype=np.float64)
    return joints, heights


def joint_limit_violation(model: mujoco.MjModel, data: mujoco.MjData) -> float:
    worst = 0.0
    for jid in range(model.njnt):
        if model.jnt_type[jid] == mujoco.mjtJoint.mjJNT_FREE:
            continue
        qadr = model.jnt_qposadr[jid]
        lo, hi = model.jnt_range[jid]
        q = data.qpos[qadr]
        if q < lo:
            worst = max(worst, float(lo - q))
        elif q > hi:
            worst = max(worst, float(q - hi))
    return worst


def torso_up_z(data: mujoco.MjData) -> float:
    mat = np.empty(9)
    mujoco.mju_quat2Mat(mat, data.qpos[3:7])
    return float(mat.reshape(3, 3)[2, 2])


def reference_index(step: int, ctrl_dt: float, variant: str, ref_len: int) -> int:
    if variant == "reference_slow_2x":
        return min(step // 2, ref_len - 1)
    if variant == "reference_hold_bottom":
        descend_end = min(step, ref_len // 2)
        return min(descend_end, ref_len - 1)
    return min(step, ref_len - 1)


def target_for_variant(
    variant: str,
    step: int,
    ctrl_dt: float,
    default_pose: np.ndarray,
    ref_joints: np.ndarray,
) -> tuple[np.ndarray, int]:
    ref_idx = reference_index(step, ctrl_dt, variant, len(ref_joints))
    target = default_pose.copy()
    target[:15] = ref_joints[ref_idx]
    if variant == "reference_deepened_1p35":
        target[:15] = default_pose[:15] + 1.35 * (target[:15] - default_pose[:15])
    elif variant == "scripted_deep_legs":
        alpha = min(step * ctrl_dt / 2.0, 1.0)
        deep = default_pose.copy()
        for offset in (0, 6):
            deep[offset + 0] = -0.62
            deep[offset + 3] = 1.18
            deep[offset + 4] = -0.58
        deep[14] = 0.18
        target = default_pose * (1.0 - alpha) + deep * alpha
        ref_idx = min(step, len(ref_joints) - 1)
    return target, ref_idx


def run_variant(variant: str, seconds: float = 6.0, ctrl_dt: float = 0.02) -> dict:
    model = mujoco.MjModel.from_xml_path(str(SCENE))
    data = mujoco.MjData(model)
    key = model.keyframe("knees_bent")
    data.qpos[:] = key.qpos
    default_pose = key.qpos[7:].copy()
    data.ctrl[:] = default_pose
    mujoco.mj_forward(model, data)

    ref_joints, ref_heights = load_reference()
    n_substeps = max(1, round(ctrl_dt / float(model.opt.timestep)))
    total_steps = int(seconds / ctrl_dt)
    min_height = float("inf")
    max_joint_violation = 0.0
    max_reference_error = 0.0
    max_height_error = 0.0
    fell_at = None
    samples = []

    for step in range(total_steps):
        target, ref_idx = target_for_variant(variant, step, ctrl_dt, default_pose, ref_joints)
        data.ctrl[:] = target
        for _ in range(n_substeps):
            mujoco.mj_step(model, data)

        height = float(data.qpos[2])
        up_z = torso_up_z(data)
        reference_error = float(np.mean(np.square(data.qpos[7:22] - ref_joints[ref_idx])))
        height_error = float((height - ref_heights[ref_idx]) ** 2)
        max_reference_error = max(max_reference_error, reference_error)
        max_height_error = max(max_height_error, height_error)
        max_joint_violation = max(max_joint_violation, joint_limit_violation(model, data))
        min_height = min(min_height, height)
        fallen = height < 0.45 or up_z < 0.30
        if fallen and fell_at is None:
            fell_at = round(step * ctrl_dt, 3)

        if step % max(1, int(0.2 / ctrl_dt)) == 0:
            samples.append(
                {
                    "t": round(step * ctrl_dt, 3),
                    "base_height": height,
                    "target_height": float(ref_heights[ref_idx]),
                    "up_z": up_z,
                    "reference_error": reference_error,
                    "height_error": height_error,
                    "joint_limit_violation": max_joint_violation,
                    "target_left_hip_pitch": float(target[0]),
                    "target_left_knee": float(target[3]),
                    "target_left_ankle_pitch": float(target[4]),
                }
            )

    depth_reached = min_height < 0.70
    stable = fell_at is None
    if stable and depth_reached:
        verdict = "TARGET_STABLE_DEPTH"
    elif depth_reached:
        verdict = "TARGET_LOWERING_UNSTABLE"
    elif stable:
        verdict = "TARGET_STABLE_SHALLOW"
    else:
        verdict = "TARGET_FAIL_SHALLOW"

    return {
        "variant": variant,
        "seconds": seconds,
        "ctrl_dt": ctrl_dt,
        "sim_dt": float(model.opt.timestep),
        "n_substeps": n_substeps,
        "fell_at": fell_at,
        "min_height": min_height,
        "final_height": float(data.qpos[2]),
        "depth_reached_lt_0p70": depth_reached,
        "stable_no_fall": stable,
        "max_reference_error": max_reference_error,
        "max_height_error": max_height_error,
        "max_joint_limit_violation": max_joint_violation,
        "verdict": verdict,
        "samples": samples,
    }


def overall_verdict(variants: list[dict]) -> str:
    if any(v["verdict"] == "TARGET_STABLE_DEPTH" for v in variants):
        return "TARGET_FEASIBLE"
    if any(v["depth_reached_lt_0p70"] for v in variants):
        return "TARGET_LOWERING_UNSTABLE"
    if any(v["stable_no_fall"] for v in variants):
        return "TARGET_TOO_SHALLOW"
    return "TARGET_FAILS_BEFORE_DEPTH"


def write_report(result: dict) -> None:
    lines = [
        "# G1 Squat Target Sanity Report",
        "",
        f"- Overall verdict: {result['verdict']}",
        f"- Reference: `{result['reference']}`",
        f"- Scene: `{result['scene']}`",
        "",
        "| Variant | Verdict | Min height | Fell at | Max ref err | Joint limit |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for variant in result["variants"]:
        fell = "never" if variant["fell_at"] is None else variant["fell_at"]
        lines.append(
            f"| {variant['variant']} | {variant['verdict']} | "
            f"{variant['min_height']:.3f} | {fell} | "
            f"{variant['max_reference_error']:.5f} | "
            f"{variant['max_joint_limit_violation']:.5f} |"
        )
    lines.extend(
        [
            "",
            "Interpretation:",
            "- Stable depth means the target is viable and PPO/curriculum is the bottleneck.",
            "- Unstable depth means the target lowers the robot but needs a staged controller/curriculum.",
            "- Shallow or pre-depth failure means the pose/reference target should be redesigned before more PPO.",
            "",
        ]
    )
    (VERIFY / "g1-squat-target-sanity.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    VERIFY.mkdir(parents=True, exist_ok=True)
    variants = [
        "reference_direct",
        "reference_slow_2x",
        "reference_deepened_1p35",
        "scripted_deep_legs",
    ]
    results = [run_variant(name) for name in variants]
    result = {
        "reference": "experiments/17-motion-to-policy-loop/verify/g1_squat_reference.compiled.json",
        "scene": "experiments/03-digital-twin/web/assets/scenes/g1/scene_g1_policy.xml",
        "variants": results,
        "verdict": overall_verdict(results),
        "next": "Use depth curriculum/controller redesign if targets lower but fall; redesign pose targets if targets remain shallow.",
    }
    (VERIFY / "g1-squat-target-sanity.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    write_report(result)
    print(result["verdict"])


if __name__ == "__main__":
    main()
