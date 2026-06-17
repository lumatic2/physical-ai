#!/usr/bin/env python3
"""Convert Unitree G1 LowState-like telemetry into web trajectory + sidecar telemetry."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


EXPECTED_JOINTS = 29
EXPECTED_NQ = 36
DEFAULT_SCENE = "g1/scene_g1_policy.xml"


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def finite_number(name: str, value: Any) -> float:
    if not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise ValueError(f"{name} must be a finite number")
    return float(value)


def finite_vector(name: str, values: Any, width: int) -> list[float]:
    if not isinstance(values, list) or len(values) != width:
        raise ValueError(f"{name} must be a list of length {width}")
    return [finite_number(f"{name}[{i}]", value) for i, value in enumerate(values)]


def parse_motor_state(frame_index: int, value: Any) -> tuple[list[float], list[float], list[float]]:
    if not isinstance(value, list) or len(value) != EXPECTED_JOINTS:
        raise ValueError(f"frames[{frame_index}].motor_state must be a list of length {EXPECTED_JOINTS}")
    q: list[float] = []
    dq: list[float] = []
    tau: list[float] = []
    for i, state in enumerate(value):
        if not isinstance(state, dict):
            raise ValueError(f"frames[{frame_index}].motor_state[{i}] must be an object")
        q.append(finite_number(f"frames[{frame_index}].motor_state[{i}].q", state.get("q")))
        dq.append(finite_number(f"frames[{frame_index}].motor_state[{i}].dq", state.get("dq", 0.0)))
        tau.append(finite_number(f"frames[{frame_index}].motor_state[{i}].tau_est", state.get("tau_est", 0.0)))
    return q, dq, tau


def convert(source: dict[str, Any], scene: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    fps = finite_number("fps", source.get("fps"))
    if fps <= 0:
        raise ValueError("fps must be positive")
    frames = source.get("frames")
    if not isinstance(frames, list) or not frames:
        raise ValueError("frames must be a non-empty list")

    qpos: list[list[float]] = []
    telemetry_frames: list[dict[str, Any]] = []
    for idx, frame in enumerate(frames):
        if not isinstance(frame, dict):
            raise ValueError(f"frames[{idx}] must be an object")
        root_pos = finite_vector(f"frames[{idx}].root_pos", frame.get("root_pos"), 3)
        root_quat = finite_vector(f"frames[{idx}].root_quat", frame.get("root_quat"), 4)
        joint_pos, joint_vel, tau_est = parse_motor_state(idx, frame.get("motor_state"))
        q = root_pos + root_quat + joint_pos
        if len(q) != EXPECTED_NQ:
            raise ValueError(f"frames[{idx}] converted to nq={len(q)}, expected {EXPECTED_NQ}")
        qpos.append(q)
        telemetry_frames.append(
            {
                "t": finite_number(f"frames[{idx}].t", frame.get("t", idx / fps)),
                "tick": int(frame.get("tick", idx)),
                "joint_pos": joint_pos,
                "joint_vel": joint_vel,
                "tau_est": tau_est,
            }
        )

    heights = [q[2] for q in qpos]
    trajectory = {
        "fps": fps,
        "nq": EXPECTED_NQ,
        "scene": scene,
        "note": "Converted from Unitree G1 LowState-like telemetry trace.",
        "source_attempt": source.get("source", "unitree-lowstate-telemetry"),
        "qpos": qpos,
    }
    telemetry = {
        "format": "physical-ai-g1-telemetry-sidecar-v0",
        "source_format": source.get("format", "unitree-g1-lowstate-trace-v0"),
        "fps": fps,
        "joint_count": EXPECTED_JOINTS,
        "frames": telemetry_frames,
    }
    summary = {
        "verdict": "PASS",
        "source_format": source.get("format", "unitree-g1-lowstate-trace-v0"),
        "source_kind": source.get("kind", "unknown"),
        "contract": "physical-ai-web-trajectory-v1",
        "telemetry_sidecar": telemetry["format"],
        "frames": len(qpos),
        "fps": fps,
        "duration_s": len(qpos) / fps,
        "nq": EXPECTED_NQ,
        "joint_count": EXPECTED_JOINTS,
        "scene": scene,
        "finite_valid": all(math.isfinite(v) for q in qpos for v in q),
        "start_height_m": heights[0],
        "min_height_m": min(heights),
        "end_height_m": heights[-1],
        "root_height_drop_m": heights[0] - min(heights),
        "next_required_evidence": "Replace synthetic frames with live DDS LowState/pose capture and rerun the same adapter.",
    }
    return trajectory, telemetry, summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--trajectory", required=True, type=Path)
    parser.add_argument("--telemetry", required=True, type=Path)
    parser.add_argument("--summary", required=True, type=Path)
    parser.add_argument("--scene", default=DEFAULT_SCENE)
    args = parser.parse_args()

    trajectory, telemetry, summary = convert(load_json(args.input), args.scene)
    for path, data in (
        (args.trajectory, trajectory),
        (args.telemetry, telemetry),
        (args.summary, summary),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
