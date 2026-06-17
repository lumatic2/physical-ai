#!/usr/bin/env python3
"""Capture Unitree G1 LowState + root pose as JSONL for the twin candidate gate.

Hardware mode expects `unitree_sdk2py` to be installed and a root-pose source to be
wired in by the operator. Fixture mode emits a capture-shaped JSONL from an
existing normalized trace so the ingest path remains testable without hardware.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Iterable


EXPECTED_JOINTS = 29
DEFAULT_QUAT = [1.0, 0.0, 0.0, 0.0]


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def fixture_frames(path: Path, max_frames: int | None) -> Iterable[dict[str, Any]]:
    data = load_json(path)
    frames = data.get("frames")
    if not isinstance(frames, list) or not frames:
        raise ValueError("fixture trace must contain non-empty frames")
    for frame in frames[:max_frames]:
        yield {
            "t": frame["t"],
            "tick": frame["tick"],
            "pose": {
                "root_pos": frame["root_pos"],
                "root_quat": frame["root_quat"],
                "source": "fixture-root-pose",
            },
            "low_state": {
                "motor_state": frame["motor_state"],
                "source": "fixture-lowstate",
            },
        }


def motor_states_from_lowstate(msg: Any) -> list[dict[str, float]]:
    motor_state = []
    for state in list(msg.motor_state)[:EXPECTED_JOINTS]:
        motor_state.append(
            {
                "q": float(state.q),
                "dq": float(getattr(state, "dq", 0.0)),
                "tau_est": float(getattr(state, "tau_est", getattr(state, "tau", 0.0))),
            }
        )
    return motor_state


def quaternion_from_lowstate(msg: Any) -> list[float]:
    imu_state = getattr(msg, "imu_state", None)
    quat = getattr(imu_state, "quaternion", None)
    if quat is None:
        return DEFAULT_QUAT.copy()
    values = [float(v) for v in list(quat)[:4]]
    if len(values) != 4:
        return DEFAULT_QUAT.copy()
    return values


def position_from_sportmode(msg: Any) -> list[float]:
    position = getattr(msg, "position", None)
    if position is None:
        raise RuntimeError("sportmode root pose source has no position field")
    values = [float(v) for v in list(position)[:3]]
    if len(values) != 3:
        raise RuntimeError("sportmode position must contain 3 values")
    return values


def load_root_pose_jsonl(path: Path, frames: int) -> list[dict[str, Any]]:
    root_pose_frames = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(root_pose_frames) < frames:
        raise RuntimeError("root pose source has fewer frames than requested")
    return root_pose_frames


def sdk_frames(args: argparse.Namespace) -> Iterable[dict[str, Any]]:
    if args.sdk_path:
        sys.path.insert(0, str(args.sdk_path))
    try:
        from unitree_sdk2py.core.channel import ChannelFactoryInitialize, ChannelSubscriber
        from unitree_sdk2py.idl.unitree_go.msg.dds_ import SportModeState_
        from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowState_
    except Exception as exc:  # pragma: no cover - depends on robot SDK install.
        raise RuntimeError("unitree_sdk2py with unitree_hg/unitree_go IDL modules is required for hardware capture") from exc

    if args.root_pose_source == "jsonl" and not args.root_pose_jsonl:
        raise RuntimeError("hardware capture with --root-pose-source jsonl needs --root-pose-jsonl")

    ChannelFactoryInitialize(args.domain_id, args.interface)
    latest_lowstate: dict[str, Any] = {}
    latest_sportmode: dict[str, Any] = {}

    def lowstate_callback(msg: Any) -> None:
        latest_lowstate["msg"] = msg
        latest_lowstate["motor_state"] = motor_states_from_lowstate(msg)
        latest_lowstate["root_quat"] = quaternion_from_lowstate(msg)

    subscriber = ChannelSubscriber(args.topic, LowState_)
    subscriber.Init(lowstate_callback, 10)

    if args.root_pose_source == "sportmode":
        def sportmode_callback(msg: Any) -> None:
            latest_sportmode["msg"] = msg
            latest_sportmode["root_pos"] = position_from_sportmode(msg)

        sport_subscriber = ChannelSubscriber(args.sportmode_topic, SportModeState_)
        sport_subscriber.Init(sportmode_callback, 10)
        root_pose_frames = None
    else:
        root_pose_frames = load_root_pose_jsonl(args.root_pose_jsonl, args.frames)

    start = time.perf_counter()
    tick = 0
    while tick < args.frames:
        if "motor_state" not in latest_lowstate:
            time.sleep(0.001)
            continue
        if args.root_pose_source == "sportmode":
            if "root_pos" not in latest_sportmode:
                time.sleep(0.001)
                continue
            root_pos = latest_sportmode["root_pos"]
            root_quat = latest_lowstate["root_quat"]
            pose_source = f"{args.sportmode_topic}+{args.topic}.imu_state"
        else:
            assert root_pose_frames is not None
            pose = root_pose_frames[tick].get("pose", root_pose_frames[tick])
            root_pos = pose["root_pos"]
            root_quat = pose["root_quat"]
            pose_source = str(args.root_pose_jsonl)
        yield {
            "t": time.perf_counter() - start,
            "tick": tick,
            "pose": {
                "root_pos": root_pos,
                "root_quat": root_quat,
                "source": pose_source,
            },
            "low_state": {
                "motor_state": latest_lowstate["motor_state"],
                "source": args.topic,
            },
        }
        tick += 1
        time.sleep(max(0.0, 1.0 / args.fps))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--frames", type=int, default=100)
    parser.add_argument("--fps", type=float, default=50.0)
    parser.add_argument("--fixture", type=Path, help="Existing unitree-g1-lowstate-trace-v0 JSON for offline fixture capture")
    parser.add_argument("--domain-id", type=int, default=1)
    parser.add_argument("--interface", default=None)
    parser.add_argument("--topic", default="rt/lowstate")
    parser.add_argument("--sportmode-topic", default="rt/sportmodestate")
    parser.add_argument("--root-pose-source", choices=["jsonl", "sportmode"], default="jsonl")
    parser.add_argument("--root-pose-jsonl", type=Path)
    parser.add_argument("--sdk-path", type=Path, help="Local unitree_sdk2_python checkout to add to PYTHONPATH for hardware/DDS capture")
    args = parser.parse_args()

    source = fixture_frames(args.fixture, args.frames) if args.fixture else sdk_frames(args)
    count = 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        for frame in source:
            motor_state = frame.get("low_state", {}).get("motor_state")
            if not isinstance(motor_state, list) or len(motor_state) != EXPECTED_JOINTS:
                raise ValueError(f"frame {count} must contain {EXPECTED_JOINTS} motor states")
            f.write(json.dumps(frame, separators=(",", ":")) + "\n")
            count += 1
    summary = {
        "verdict": "PASS",
        "format": "physical-ai-g1-capture-jsonl-v0",
        "output": str(args.output),
        "frames": count,
        "fps_target": args.fps,
        "mode": "fixture" if args.fixture else "hardware",
        "next_step": "Run run_twin_candidate_gate.py --capture on this JSONL.",
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
