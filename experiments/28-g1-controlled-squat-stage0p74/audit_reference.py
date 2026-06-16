"""Audit whether the staged squat reference is foot-contact preserving."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import mujoco
import numpy as np

from run_controlled_squat import ContactAwareSquat, joint_limit_violation


EXP_DIR = Path(__file__).resolve().parent
STAGE_DIR = EXP_DIR / "verify" / "stage-0p74"


def as_float(value: np.ndarray | float) -> float:
    return float(np.asarray(value).item())


def audit_reference(stage_height: float, sample_stride: int) -> dict:
    env = ContactAwareSquat(stage_height=stage_height, config_overrides={"impl": "jax"})
    model = env.mj_model
    key = model.keyframe("knees_bent")
    foot_site_ids = np.asarray(env._feet_site_id)
    ref_joints = np.asarray(env._ref_joints, dtype=np.float64)
    ref_heights = np.asarray(env._ref_heights, dtype=np.float64)
    raw_ref_heights = np.asarray(env._raw_ref_heights, dtype=np.float64)
    default_lower = key.qpos[7:22].astype(np.float64).copy()

    baseline = mujoco.MjData(model)
    baseline.qpos[:] = key.qpos
    baseline.ctrl[:] = key.qpos[7:]
    mujoco.mj_forward(model, baseline)
    initial_foot_xyz = baseline.site_xpos[foot_site_ids].copy()
    initial_foot_xy = initial_foot_xyz[:, :2]
    initial_foot_z_mean = as_float(np.mean(initial_foot_xyz[:, 2]))
    initial_base_height = as_float(baseline.qpos[2])

    rows = []
    summary = {
        "max_foot_xy_drift_m": 0.0,
        "max_abs_foot_z_error_at_declared_m": 0.0,
        "min_foot_anchored_base_height_m": float("inf"),
        "max_abs_height_delta_if_foot_anchored_m": 0.0,
        "max_joint_limit_violation": 0.0,
        "max_lower_joint_delta_rad": 0.0,
        "min_declared_height_m": float("inf"),
        "min_raw_reference_height_m": float("inf"),
    }

    for idx in range(0, len(ref_heights), sample_stride):
        target = mujoco.MjData(model)
        target.qpos[:] = key.qpos
        target.qpos[2] = ref_heights[idx]
        target.qpos[7:22] = ref_joints[idx]
        target.ctrl[:] = target.qpos[7:]
        mujoco.mj_forward(model, target)

        foot_xyz = target.site_xpos[foot_site_ids].copy()
        foot_xy_drift = float(np.max(np.linalg.norm(foot_xyz[:, :2] - initial_foot_xy, axis=1)))
        foot_z_error = float(np.max(np.abs(foot_xyz[:, 2] - initial_foot_z_mean)))
        joint_violation = joint_limit_violation(model, target)
        lower_joint_delta = float(np.max(np.abs(ref_joints[idx] - default_lower)))

        anchored = mujoco.MjData(model)
        anchored.qpos[:] = target.qpos
        anchored.ctrl[:] = target.ctrl
        anchored.qpos[2] += initial_foot_z_mean - float(np.mean(foot_xyz[:, 2]))
        mujoco.mj_forward(model, anchored)
        anchored_height = as_float(anchored.qpos[2])
        height_delta = anchored_height - float(ref_heights[idx])

        support_center = np.mean(anchored.site_xpos[foot_site_ids, :2], axis=0)
        pelvis_xy = anchored.xpos[model.body("pelvis").id, :2]
        pelvis_support_offset = float(np.linalg.norm(pelvis_xy - support_center))

        summary["max_foot_xy_drift_m"] = max(summary["max_foot_xy_drift_m"], foot_xy_drift)
        summary["max_abs_foot_z_error_at_declared_m"] = max(summary["max_abs_foot_z_error_at_declared_m"], foot_z_error)
        summary["min_foot_anchored_base_height_m"] = min(summary["min_foot_anchored_base_height_m"], anchored_height)
        summary["max_abs_height_delta_if_foot_anchored_m"] = max(
            summary["max_abs_height_delta_if_foot_anchored_m"], abs(height_delta)
        )
        summary["max_joint_limit_violation"] = max(summary["max_joint_limit_violation"], joint_violation)
        summary["max_lower_joint_delta_rad"] = max(summary["max_lower_joint_delta_rad"], lower_joint_delta)
        summary["min_declared_height_m"] = min(summary["min_declared_height_m"], float(ref_heights[idx]))
        summary["min_raw_reference_height_m"] = min(summary["min_raw_reference_height_m"], float(raw_ref_heights[idx]))

        if idx % max(sample_stride, int(0.4 / env.dt)) == 0 or idx == len(ref_heights) - 1:
            rows.append(
                {
                    "index": idx,
                    "t": round(idx * float(env.dt), 3),
                    "raw_reference_height": float(raw_ref_heights[idx]),
                    "declared_stage_height": float(ref_heights[idx]),
                    "foot_anchored_base_height": anchored_height,
                    "height_delta_if_foot_anchored": height_delta,
                    "foot_xy_drift": foot_xy_drift,
                    "foot_z_error_at_declared": foot_z_error,
                    "pelvis_support_offset": pelvis_support_offset,
                    "joint_limit_violation": joint_violation,
                    "max_lower_joint_delta": lower_joint_delta,
                }
            )

    summary["sample_count"] = len(ref_heights)
    summary["sample_stride"] = sample_stride
    summary["initial_base_height_m"] = initial_base_height
    summary["initial_foot_z_mean_m"] = initial_foot_z_mean

    gates = {
        "declared_height_reaches_stage": summary["min_declared_height_m"] <= stage_height + 1e-6,
        "foot_anchored_reaches_stage": summary["min_foot_anchored_base_height_m"] <= stage_height + 0.005,
        "foot_xy_drift_small": summary["max_foot_xy_drift_m"] <= 0.03,
        "foot_z_error_small_at_declared": summary["max_abs_foot_z_error_at_declared_m"] <= 0.03,
        "joint_limits_ok": summary["max_joint_limit_violation"] <= 0.05,
    }
    gates["contact_preserving_reference"] = all(gates.values())
    scale_sweep = []
    for scale in [0.1, 0.25, 0.5, 0.75, 1.0]:
        scale_summary = {
            "scale": scale,
            "min_foot_anchored_base_height_m": float("inf"),
            "max_foot_xy_drift_m": 0.0,
            "max_abs_foot_z_error_at_declared_m": 0.0,
            "max_lower_joint_delta_rad": 0.0,
            "max_joint_limit_violation": 0.0,
        }
        for idx in range(0, len(raw_ref_heights), sample_stride):
            scaled_joints = default_lower + scale * (np.asarray(env._raw_ref_joints[idx], dtype=np.float64) - default_lower)
            data = mujoco.MjData(model)
            data.qpos[:] = key.qpos
            data.qpos[2] = stage_height
            data.qpos[7:22] = scaled_joints
            data.ctrl[:] = data.qpos[7:]
            mujoco.mj_forward(model, data)
            foot_xyz = data.site_xpos[foot_site_ids].copy()
            anchored_height = stage_height + initial_foot_z_mean - float(np.mean(foot_xyz[:, 2]))
            scale_summary["min_foot_anchored_base_height_m"] = min(
                scale_summary["min_foot_anchored_base_height_m"], anchored_height
            )
            scale_summary["max_foot_xy_drift_m"] = max(
                scale_summary["max_foot_xy_drift_m"],
                float(np.max(np.linalg.norm(foot_xyz[:, :2] - initial_foot_xy, axis=1))),
            )
            scale_summary["max_abs_foot_z_error_at_declared_m"] = max(
                scale_summary["max_abs_foot_z_error_at_declared_m"],
                float(np.max(np.abs(foot_xyz[:, 2] - initial_foot_z_mean))),
            )
            scale_summary["max_lower_joint_delta_rad"] = max(
                scale_summary["max_lower_joint_delta_rad"], float(np.max(np.abs(scaled_joints - default_lower)))
            )
            scale_summary["max_joint_limit_violation"] = max(
                scale_summary["max_joint_limit_violation"], joint_limit_violation(model, data)
            )
        scale_sweep.append(scale_summary)

    return {
        "attempt": "attempt-013-reference-audit",
        "stage_height": stage_height,
        "reference_source": "experiments/17-motion-to-policy-loop/verify/g1_squat_reference.compiled.json",
        "env_source": "experiments/25-g1-squat-depth-curriculum/g1_squat_curriculum_env.py",
        "summary": summary,
        "gates": gates,
        "raw_reference_scale_sweep": scale_sweep,
        "samples": rows,
    }


def write_report(result: dict, out_dir: Path) -> None:
    summary = result["summary"]
    gates = result["gates"]
    lines = [
        "# Attempt 013 Reference Audit",
        "",
        f"- stage height: `{result['stage_height']:.3f}`",
        f"- contact-preserving reference: `{gates['contact_preserving_reference']}`",
        "",
        "| Metric | Value | Gate |",
        "|---|---:|---:|",
        f"| min declared height | {summary['min_declared_height_m']:.4f} | <= {result['stage_height']:.3f} |",
        f"| min foot-anchored base height | {summary['min_foot_anchored_base_height_m']:.4f} | <= {result['stage_height'] + 0.005:.3f} |",
        f"| max foot XY drift | {summary['max_foot_xy_drift_m']:.4f} | <= 0.030 |",
        f"| max foot Z error at declared height | {summary['max_abs_foot_z_error_at_declared_m']:.4f} | <= 0.030 |",
        f"| max joint limit violation | {summary['max_joint_limit_violation']:.4f} | <= 0.050 |",
        "",
        "| t | raw h | declared h | foot-anchored h | foot XY drift | foot Z err | joint viol |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in result["samples"]:
        lines.append(
            "| {t:.2f} | {raw_reference_height:.4f} | {declared_stage_height:.4f} | "
            "{foot_anchored_base_height:.4f} | {foot_xy_drift:.4f} | "
            "{foot_z_error_at_declared:.4f} | {joint_limit_violation:.4f} |".format(**row)
        )
    lines.extend(
        [
            "",
            "## Raw Reference Scale Sweep",
            "",
            "| scale | min foot-anchored h | max foot XY drift | max foot Z err | max joint delta | joint viol |",
            "|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in result["raw_reference_scale_sweep"]:
        lines.append(
            "| {scale:.2f} | {min_foot_anchored_base_height_m:.4f} | {max_foot_xy_drift_m:.4f} | "
            "{max_abs_foot_z_error_at_declared_m:.4f} | {max_lower_joint_delta_rad:.4f} | "
            "{max_joint_limit_violation:.4f} |".format(**row)
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `declared h` is the staged target height used by exp28.",
            "- `foot-anchored h` is the base height implied if the same joint target keeps the feet at their initial ground height.",
            "- Large foot XY/Z errors mean the reference is not a clean fixed-feet squat target and should be rebuilt before more PPO.",
        ]
    )
    (out_dir / "reference-audit.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage-height", type=float, default=0.74)
    parser.add_argument("--sample-stride", type=int, default=5)
    parser.add_argument("--out", type=Path, default=STAGE_DIR / "attempts" / "attempt-013-reference-audit")
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    result = audit_reference(args.stage_height, max(1, args.sample_stride))
    (args.out / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    write_report(result, args.out)
    print(json.dumps({"out": str(args.out), "gates": result["gates"], "summary": result["summary"]}, indent=2))


if __name__ == "__main__":
    main()
