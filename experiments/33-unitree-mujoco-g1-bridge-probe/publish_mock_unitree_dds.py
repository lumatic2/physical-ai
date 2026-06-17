#!/usr/bin/env python3
"""Publish a LowState trace over local Unitree SDK2 DDS topics."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any


EXPECTED_JOINTS = 29


def load_trace(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    frames = data.get("frames")
    if not isinstance(frames, list) or not frames:
        raise ValueError("trace must contain non-empty frames")
    return frames


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace", required=True, type=Path)
    parser.add_argument("--frames", type=int, default=100)
    parser.add_argument("--fps", type=float, default=50.0)
    parser.add_argument("--domain-id", type=int, default=1)
    parser.add_argument("--interface", default=None)
    parser.add_argument("--topic", default="rt/lowstate")
    parser.add_argument("--sportmode-topic", default="rt/sportmodestate")
    parser.add_argument("--sdk-path", type=Path)
    parser.add_argument("--warmup-s", type=float, default=0.5)
    args = parser.parse_args()

    if args.sdk_path:
        sys.path.insert(0, str(args.sdk_path))

    from unitree_sdk2py.core.channel import ChannelFactoryInitialize, ChannelPublisher
    from unitree_sdk2py.idl.default import unitree_go_msg_dds__SportModeState_
    from unitree_sdk2py.idl.default import unitree_hg_msg_dds__LowState_
    from unitree_sdk2py.idl.unitree_go.msg.dds_ import SportModeState_
    from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowState_

    frames = load_trace(args.trace)[: args.frames]
    ChannelFactoryInitialize(args.domain_id, args.interface)
    lowstate_publisher = ChannelPublisher(args.topic, LowState_)
    lowstate_publisher.Init()
    sportmode_publisher = ChannelPublisher(args.sportmode_topic, SportModeState_)
    sportmode_publisher.Init()

    time.sleep(args.warmup_s)
    dt = 1.0 / args.fps
    start = time.perf_counter()
    for tick, frame in enumerate(frames):
        low_state = unitree_hg_msg_dds__LowState_()
        sport_state = unitree_go_msg_dds__SportModeState_()
        low_state.tick = int(frame.get("tick", tick))
        root_quat = frame["root_quat"]
        for i in range(4):
            low_state.imu_state.quaternion[i] = float(root_quat[i])
        root_pos = frame["root_pos"]
        for i in range(3):
            sport_state.position[i] = float(root_pos[i])
        motor_state = frame["motor_state"]
        if len(motor_state) < EXPECTED_JOINTS:
            raise ValueError(f"frame {tick} has fewer than {EXPECTED_JOINTS} motor states")
        for i in range(EXPECTED_JOINTS):
            low_state.motor_state[i].q = float(motor_state[i].get("q", 0.0))
            low_state.motor_state[i].dq = float(motor_state[i].get("dq", 0.0))
            low_state.motor_state[i].tau_est = float(motor_state[i].get("tau_est", 0.0))
        lowstate_publisher.Write(low_state)
        sportmode_publisher.Write(sport_state)
        target = start + (tick + 1) * dt
        sleep_s = target - time.perf_counter()
        if sleep_s > 0:
            time.sleep(sleep_s)

    print(
        json.dumps(
            {
                "verdict": "PASS",
                "contract": "physical-ai-local-dds-lowstate-publisher-v0",
                "trace": str(args.trace),
                "frames": len(frames),
                "fps_target": args.fps,
                "lowstate_topic": args.topic,
                "sportmode_topic": args.sportmode_topic,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
