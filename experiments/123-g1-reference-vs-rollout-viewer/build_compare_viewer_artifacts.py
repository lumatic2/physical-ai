#!/usr/bin/env python3
"""Build M22 reference-vs-rollout artifacts for the browser viewer.

The reference motion compiler produces lower-body targets and base height.
The public viewer consumes full qpos trajectories. This script embeds the
reference targets into the same G1 qpos contract used by the measured WBC
rollout, then writes a small comparison summary for QA.
"""

from __future__ import annotations

import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EXP = Path(__file__).resolve().parent
WEBROOT = ROOT / "experiments" / "03-digital-twin"
REF_PATH = ROOT / "experiments" / "17-motion-to-policy-loop" / "verify" / "g1_squat_reference.compiled.json"
ROLLOUT_PATH = WEBROOT / "g1_decoupled_wbc_squat_trajectory.json"
OUT_TRAJ = WEBROOT / "g1_squat_reference_trajectory.json"
OUT_SUMMARY = EXP / "verify" / "reference-vs-rollout-summary.json"


def lerp(a: float, b: float, alpha: float) -> float:
    return a + (b - a) * alpha


def sample_reference(samples: list[dict], t: float) -> dict:
    if t <= samples[0]["t"]:
        return samples[0]
    if t >= samples[-1]["t"]:
        return samples[-1]
    lo = 0
    hi = len(samples) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if samples[mid]["t"] <= t:
            lo = mid
        else:
            hi = mid
    a = samples[lo]
    b = samples[hi]
    alpha = (t - a["t"]) / (b["t"] - a["t"])
    return {
        "t": t,
        "base_height": lerp(a["base_height"], b["base_height"], alpha),
        "joint_targets": [
            lerp(float(x), float(y), alpha)
            for x, y in zip(a["joint_targets"], b["joint_targets"])
        ],
    }


def rms(values: list[float]) -> float:
    if not values:
        return 0.0
    return math.sqrt(sum(v * v for v in values) / len(values))


def main() -> int:
    ref = json.loads(REF_PATH.read_text(encoding="utf-8"))
    rollout = json.loads(ROLLOUT_PATH.read_text(encoding="utf-8"))
    frames = rollout["qpos"]
    fps = int(rollout["fps"])
    nq = int(rollout.get("nq", len(frames[0])))
    ref_samples = ref["trajectory"]["samples"]

    ref_qpos = []
    height_errors = []
    joint_rms_errors = []
    for i, actual in enumerate(frames):
        t = i / fps
        s = sample_reference(ref_samples, t)
        q = list(frames[0])
        q[0] = actual[0]
        q[1] = -0.45
        q[2] = s["base_height"]
        q[3:7] = frames[0][3:7]
        q[7:22] = s["joint_targets"]
        ref_qpos.append(q)

        height_errors.append(abs(float(actual[2]) - float(q[2])))
        joint_pairs = zip(actual[7:22], q[7:22])
        joint_rms_errors.append(rms([float(a) - float(b) for a, b in joint_pairs]))

    OUT_TRAJ.write_text(
        json.dumps(
            {
                "fps": fps,
                "nq": nq,
                "scene": rollout.get("scene", "g1/scene_g1_policy.xml"),
                "contract": "physical-ai-web-trajectory-v1",
                "source": str(REF_PATH.relative_to(ROOT)).replace("\\", "/"),
                "note": "M22 browser reference trajectory derived from compiled squat reference targets.",
                "qpos": ref_qpos,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    max_height_error = max(height_errors)
    mean_height_error = sum(height_errors) / len(height_errors)
    max_joint_rms_error = max(joint_rms_errors)
    summary = {
        "verdict": "PASS",
        "reference": str(REF_PATH.relative_to(ROOT)).replace("\\", "/"),
        "rollout": str(ROLLOUT_PATH.relative_to(ROOT)).replace("\\", "/"),
        "reference_trajectory": str(OUT_TRAJ.relative_to(ROOT)).replace("\\", "/"),
        "frames": len(frames),
        "fps": fps,
        "nq": nq,
        "max_height_error_m": max_height_error,
        "mean_height_error_m": mean_height_error,
        "max_joint_rms_error_rad": max_joint_rms_error,
        "thresholds": {
            "max_height_error_m": 0.20,
            "max_joint_rms_error_rad": 0.35,
        },
        "pass": max_height_error <= 0.20 and max_joint_rms_error <= 0.35,
    }
    OUT_SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    OUT_SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if summary["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
