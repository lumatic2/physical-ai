"""Compile and probe a reference motion trajectory."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parent
EXAMPLE = ROOT / "examples/g1_squat_reference.json"
VERIFY = ROOT / "verify"


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate(motion: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if motion.get("schema_version") != "0.1":
        errors.append("schema_version must be 0.1")
    if motion.get("embodiment") != "g1":
        errors.append("only g1 is supported in this probe")
    joints = motion.get("joints", [])
    if not joints:
        errors.append("joints must be non-empty")
    last_t = -1.0
    for index, frame in enumerate(motion.get("frames", [])):
        if frame["t"] <= last_t:
            errors.append(f"frame {index} time is not strictly increasing")
        last_t = frame["t"]
        if len(frame.get("joint_targets", [])) != len(joints):
            errors.append(f"frame {index} joint target length mismatch")
    return errors


def interpolate(motion: dict[str, Any]) -> dict[str, Any]:
    fps = float(motion["fps"])
    frames = motion["frames"]
    times = np.array([frame["t"] for frame in frames], dtype=float)
    targets = np.array([frame["joint_targets"] for frame in frames], dtype=float)
    heights = np.array([frame["base_height"] for frame in frames], dtype=float)
    sample_times = np.arange(times[0], times[-1] + 1e-9, 1.0 / fps)

    interp_targets = np.vstack([
        np.interp(sample_times, times, targets[:, joint_index])
        for joint_index in range(targets.shape[1])
    ]).T
    interp_heights = np.interp(sample_times, times, heights)
    velocity = np.diff(interp_targets, axis=0) * fps
    accel = np.diff(velocity, axis=0) * fps
    smoothness_cost = float(np.mean(np.square(accel))) if len(accel) else 0.0
    return {
        "sample_count": int(len(sample_times)),
        "duration_s": float(times[-1] - times[0]),
        "mean_base_height": float(np.mean(interp_heights)),
        "min_base_height": float(np.min(interp_heights)),
        "max_joint_delta": float(np.max(np.abs(interp_targets - interp_targets[0]))),
        "smoothness_cost": smoothness_cost,
        "samples": [
            {
                "t": float(sample_times[i]),
                "base_height": float(interp_heights[i]),
                "joint_targets": interp_targets[i].tolist(),
            }
            for i in range(len(sample_times))
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("motion", nargs="?", type=Path, default=EXAMPLE)
    parser.add_argument("--out", type=Path, default=VERIFY)
    args = parser.parse_args()

    motion = load(args.motion)
    errors = validate(motion)
    args.out.mkdir(parents=True, exist_ok=True)
    if errors:
        (args.out / "reference-compile-errors.json").write_text(json.dumps({"errors": errors}, indent=2), encoding="utf-8")
        raise SystemExit(1)

    compiled = {
        "source": args.motion.relative_to(ROOT).as_posix(),
        "id": motion["id"],
        "embodiment": motion["embodiment"],
        "joints": motion["joints"],
        "metrics": motion["metrics"],
        "trajectory": interpolate(motion),
        "reward_terms": ["reference_tracking_error", "base_height_error", "smoothness_penalty", "fall_penalty"],
        "next": "Use trajectory.samples as reference targets for motion-tracking reward; this probe does not train a policy.",
    }
    out_path = args.out / f"{motion['id']}.compiled.json"
    out_path.write_text(json.dumps(compiled, indent=2), encoding="utf-8")
    report = [
        "# Reference Motion Compile Probe",
        "",
        f"- Motion: {motion['id']}",
        f"- Samples: {compiled['trajectory']['sample_count']}",
        f"- Duration: {compiled['trajectory']['duration_s']:.2f}s",
        f"- Min base height: {compiled['trajectory']['min_base_height']:.3f}m",
        f"- Max joint delta: {compiled['trajectory']['max_joint_delta']:.3f}rad",
        f"- Smoothness cost: {compiled['trajectory']['smoothness_cost']:.6f}",
        "",
        "Reference format and interpolation path are live. Policy imitation/tracking remains future work.",
        "",
    ]
    (args.out / "reference-motion-compile.md").write_text("\n".join(report), encoding="utf-8")
    print("PASS", f"samples={compiled['trajectory']['sample_count']}", f"duration={compiled['trajectory']['duration_s']:.2f}s")


if __name__ == "__main__":
    main()
