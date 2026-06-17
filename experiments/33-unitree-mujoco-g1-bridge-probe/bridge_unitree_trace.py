#!/usr/bin/env python3
"""Convert a Unitree-style G1 trace into the current web trajectory contract."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


EXPECTED_G1_NQ = 36
EXPECTED_G1_JOINTS = 29
DEFAULT_SCENE = "g1/scene_g1_policy.xml"


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def assert_number_list(name: str, values: Any, width: int) -> list[float]:
    if not isinstance(values, list) or len(values) != width:
        raise ValueError(f"{name} must be a list of length {width}")
    out: list[float] = []
    for i, value in enumerate(values):
        if not isinstance(value, (int, float)) or not math.isfinite(float(value)):
            raise ValueError(f"{name}[{i}] must be a finite number")
        out.append(float(value))
    return out


def qpos_from_unitree_frame(frame: dict[str, Any]) -> list[float]:
    root_pos = assert_number_list("root_pos", frame.get("root_pos"), 3)
    root_quat = assert_number_list("root_quat", frame.get("root_quat"), 4)
    joint_pos = assert_number_list("joint_pos", frame.get("joint_pos"), EXPECTED_G1_JOINTS)
    return root_pos + root_quat + joint_pos


def convert_trace(source: dict[str, Any], scene: str) -> tuple[dict[str, Any], dict[str, Any]]:
    fps = source.get("fps")
    if not isinstance(fps, (int, float)) or float(fps) <= 0:
        raise ValueError("source.fps must be a positive number")

    frames = source.get("frames")
    if not isinstance(frames, list) or not frames:
        raise ValueError("source.frames must be a non-empty list")

    qpos: list[list[float]] = []
    for idx, frame in enumerate(frames):
        if not isinstance(frame, dict):
            raise ValueError(f"frames[{idx}] must be an object")
        q = qpos_from_unitree_frame(frame)
        if len(q) != EXPECTED_G1_NQ:
            raise ValueError(f"frames[{idx}] converted to nq={len(q)}, expected {EXPECTED_G1_NQ}")
        qpos.append(q)

    heights = [q[2] for q in qpos]
    output = {
        "fps": float(fps),
        "nq": EXPECTED_G1_NQ,
        "scene": scene,
        "note": "Converted from Unitree-style root pose + 29 joint trace.",
        "source_attempt": source.get("source", "unitree-trace-adapter"),
        "qpos": qpos,
    }
    summary = {
        "verdict": "PASS",
        "contract": "physical-ai-web-trajectory-v1",
        "source_format": source.get("format", "unitree-g1-trace-v0"),
        "source_kind": source.get("kind", "mock"),
        "frames": len(qpos),
        "fps": float(fps),
        "duration_s": len(qpos) / float(fps),
        "nq": EXPECTED_G1_NQ,
        "scene": scene,
        "shape_valid": all(len(q) == EXPECTED_G1_NQ for q in qpos),
        "finite_valid": all(math.isfinite(v) for q in qpos for v in q),
        "start_height_m": heights[0],
        "min_height_m": min(heights),
        "max_height_m": max(heights),
        "end_height_m": heights[-1],
        "root_height_drop_m": heights[0] - min(heights),
        "adapter": "bridge_unitree_trace.py",
        "next_required_evidence": "Run the same adapter on a trace exported from unitreerobotics/unitree_mujoco.",
    }
    return output, summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--summary", required=True, type=Path)
    parser.add_argument("--scene", default=DEFAULT_SCENE)
    args = parser.parse_args()

    source = load_json(args.input)
    output, summary = convert_trace(source, args.scene)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    args.summary.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
