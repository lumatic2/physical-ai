#!/usr/bin/env python3
"""Synthesize a Unitree G1 LowState-like trace from a web qpos trajectory."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


EXPECTED_NQ = 36
EXPECTED_JOINTS = 29


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def finite_vector(name: str, values: Any, width: int) -> list[float]:
    if not isinstance(values, list) or len(values) != width:
        raise ValueError(f"{name} must be a list of length {width}")
    out: list[float] = []
    for i, value in enumerate(values):
        if not isinstance(value, (int, float)) or not math.isfinite(float(value)):
            raise ValueError(f"{name}[{i}] must be a finite number")
        out.append(float(value))
    return out


def synthesize(source: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    fps = source.get("fps")
    if not isinstance(fps, (int, float)) or float(fps) <= 0:
        raise ValueError("source.fps must be a positive number")
    qpos = source.get("qpos")
    if not isinstance(qpos, list) or not qpos:
        raise ValueError("source.qpos must be a non-empty list")

    frames = []
    prev_joint_pos: list[float] | None = None
    for idx, frame in enumerate(qpos):
        q = finite_vector(f"qpos[{idx}]", frame, EXPECTED_NQ)
        joint_pos = q[7:]
        if len(joint_pos) != EXPECTED_JOINTS:
            raise ValueError(f"qpos[{idx}] joint slice must be length {EXPECTED_JOINTS}")
        if prev_joint_pos is None:
            joint_vel = [0.0] * EXPECTED_JOINTS
        else:
            joint_vel = [(joint_pos[i] - prev_joint_pos[i]) * float(fps) for i in range(EXPECTED_JOINTS)]
        prev_joint_pos = joint_pos
        frames.append(
            {
                "t": idx / float(fps),
                "tick": idx,
                "root_pos": q[:3],
                "root_quat": q[3:7],
                "motor_state": [
                    {"q": joint_pos[i], "dq": joint_vel[i], "tau_est": 0.0}
                    for i in range(EXPECTED_JOINTS)
                ],
            }
        )

    heights = [float(frame[2]) for frame in qpos]
    output = {
        "format": "unitree-g1-lowstate-trace-v0",
        "kind": "synthetic_lowstate_from_headless_qpos",
        "source": source.get("source_attempt", source.get("note", "web-qpos-trajectory")),
        "fps": float(fps),
        "joint_count": EXPECTED_JOINTS,
        "frames": frames,
    }
    summary = {
        "verdict": "PASS",
        "format": output["format"],
        "frames": len(frames),
        "fps": float(fps),
        "duration_s": len(frames) / float(fps),
        "joint_count": EXPECTED_JOINTS,
        "start_height_m": heights[0],
        "min_height_m": min(heights),
        "end_height_m": heights[-1],
        "root_height_drop_m": heights[0] - min(heights),
        "note": "Synthetic telemetry-shaped trace. It mirrors qpos evidence and is not a live DDS capture.",
    }
    return output, summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trajectory", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--summary", required=True, type=Path)
    args = parser.parse_args()

    output, summary = synthesize(load_json(args.trajectory))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    args.summary.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
