#!/usr/bin/env python3
"""Normalize live Unitree-style capture logs into the bridge LowState trace contract.

Accepted input shapes:
- JSON object with a top-level `frames` list.
- JSONL/NDJSON, one frame object per line.

Each frame must contain root pose plus 29 motor states. Root pose may be top-level
`root_pos`/`root_quat` or nested under `pose`. Motor states may be top-level
`motor_state` or nested under `low_state`.
"""

from __future__ import annotations

import argparse
import json
import math
from json import JSONDecodeError
from pathlib import Path
from typing import Any


EXPECTED_JOINTS = 29
OUTPUT_FORMAT = "unitree-g1-lowstate-trace-v0"


def finite_number(name: str, value: Any) -> float:
    if not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise ValueError(f"{name} must be a finite number")
    return float(value)


def finite_vector(name: str, value: Any, width: int) -> list[float]:
    if not isinstance(value, list) or len(value) != width:
        raise ValueError(f"{name} must be a list of length {width}")
    return [finite_number(f"{name}[{i}]", item) for i, item in enumerate(value)]


def load_capture(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError(f"{path} is empty")
    if text[0] == "{":
        try:
            data = json.loads(text)
        except JSONDecodeError:
            frames = [json.loads(line) for line in text.splitlines() if line.strip()]
        else:
            if isinstance(data, dict) and isinstance(data.get("frames"), list):
                frames = data["frames"]
            elif isinstance(data, dict):
                frames = [data]
            else:
                raise ValueError("JSON capture must be an object")
    else:
        frames = [json.loads(line) for line in text.splitlines() if line.strip()]
    if not frames:
        raise ValueError("capture must contain at least one frame")
    if not all(isinstance(frame, dict) for frame in frames):
        raise ValueError("all capture frames must be JSON objects")
    return frames


def extract_pose(frame: dict[str, Any], idx: int) -> tuple[list[float], list[float]]:
    pose = frame.get("pose") if isinstance(frame.get("pose"), dict) else frame
    root_pos = finite_vector(f"frames[{idx}].root_pos", pose.get("root_pos"), 3)
    root_quat = finite_vector(f"frames[{idx}].root_quat", pose.get("root_quat"), 4)
    norm = math.sqrt(sum(v * v for v in root_quat))
    if norm < 1e-9:
        raise ValueError(f"frames[{idx}].root_quat has near-zero norm")
    return root_pos, [v / norm for v in root_quat]


def extract_motor_state(frame: dict[str, Any], idx: int) -> list[dict[str, float]]:
    low_state = frame.get("low_state") if isinstance(frame.get("low_state"), dict) else frame
    motor_state = low_state.get("motor_state")
    if not isinstance(motor_state, list) or len(motor_state) != EXPECTED_JOINTS:
        raise ValueError(f"frames[{idx}].motor_state must contain {EXPECTED_JOINTS} joints")
    out: list[dict[str, float]] = []
    for joint_idx, state in enumerate(motor_state):
        if isinstance(state, dict):
            q = state.get("q")
            dq = state.get("dq", 0.0)
            tau = state.get("tau_est", state.get("tau", 0.0))
        elif isinstance(state, list) and len(state) >= 1:
            q = state[0]
            dq = state[1] if len(state) > 1 else 0.0
            tau = state[2] if len(state) > 2 else 0.0
        else:
            raise ValueError(f"frames[{idx}].motor_state[{joint_idx}] must be object or [q,dq,tau]")
        out.append(
            {
                "q": finite_number(f"frames[{idx}].motor_state[{joint_idx}].q", q),
                "dq": finite_number(f"frames[{idx}].motor_state[{joint_idx}].dq", dq),
                "tau_est": finite_number(f"frames[{idx}].motor_state[{joint_idx}].tau_est", tau),
            }
        )
    return out


def normalize(frames: list[dict[str, Any]], source: str, fallback_fps: float) -> tuple[dict[str, Any], dict[str, Any]]:
    normalized_frames: list[dict[str, Any]] = []
    times: list[float] = []
    last_t: float | None = None
    dropped_time_order = 0
    for idx, frame in enumerate(frames):
        t = finite_number(f"frames[{idx}].t", frame.get("t", idx / fallback_fps))
        if last_t is not None and t <= last_t:
            dropped_time_order += 1
        last_t = t
        root_pos, root_quat = extract_pose(frame, idx)
        normalized_frames.append(
            {
                "t": t,
                "tick": int(frame.get("tick", idx)),
                "root_pos": root_pos,
                "root_quat": root_quat,
                "motor_state": extract_motor_state(frame, idx),
            }
        )
        times.append(t)

    if len(times) >= 2:
        dts = [b - a for a, b in zip(times, times[1:]) if b > a]
        if not dts:
            fps = fallback_fps
            jitter_s = None
        else:
            mean_dt = sum(dts) / len(dts)
            fps = 1.0 / mean_dt
            jitter_s = max(abs(dt - mean_dt) for dt in dts)
    else:
        fps = fallback_fps
        jitter_s = None

    trace = {
        "format": OUTPUT_FORMAT,
        "kind": "live_capture_normalized",
        "source": source,
        "fps": fps,
        "joint_count": EXPECTED_JOINTS,
        "frames": normalized_frames,
        "capture_requirements": {
            "root_pose_required": True,
            "root_pose_note": "LowState joint telemetry alone is not enough for floating-base web replay.",
        },
    }
    summary = {
        "verdict": "PASS" if dropped_time_order == 0 else "WARN_NON_MONOTONIC_TIME",
        "format": OUTPUT_FORMAT,
        "source": source,
        "frames": len(normalized_frames),
        "joint_count": EXPECTED_JOINTS,
        "fps_estimate": fps,
        "duration_s": (times[-1] - times[0]) if len(times) >= 2 else 0.0,
        "time_jitter_s": jitter_s,
        "non_monotonic_time_pairs": dropped_time_order,
        "root_pose_required": True,
        "next_step": "Feed this normalized trace into bridge_lowstate_trace.py.",
    }
    return trace, summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--summary", required=True, type=Path)
    parser.add_argument("--source", default="live-lowstate-capture")
    parser.add_argument("--fallback-fps", type=float, default=50.0)
    args = parser.parse_args()

    trace, summary = normalize(load_capture(args.input), args.source, args.fallback_fps)
    for path, data in ((args.output, trace), (args.summary, summary)):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if summary["verdict"].startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
