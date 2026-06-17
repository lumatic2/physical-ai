#!/usr/bin/env python3
"""Bridge Unitree SDK2 DDS LowState/SportModeState directly to web stream frames."""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import sys
import threading
import time
from pathlib import Path
from typing import Any

import websockets


EXPECTED_JOINTS = 29
EXPECTED_NQ = 36


def finite(values: list[float]) -> bool:
    return all(math.isfinite(v) for v in values)


def motor_states_from_lowstate(msg: Any) -> tuple[list[float], list[float], list[float]]:
    joint_pos: list[float] = []
    joint_vel: list[float] = []
    tau_est: list[float] = []
    for state in list(msg.motor_state)[:EXPECTED_JOINTS]:
        joint_pos.append(float(state.q))
        joint_vel.append(float(getattr(state, "dq", 0.0)))
        tau_est.append(float(getattr(state, "tau_est", getattr(state, "tau", 0.0))))
    return joint_pos, joint_vel, tau_est


def quat_from_lowstate(msg: Any) -> list[float]:
    quat = getattr(getattr(msg, "imu_state", None), "quaternion", None)
    if quat is None:
        return [1.0, 0.0, 0.0, 0.0]
    values = [float(v) for v in list(quat)[:4]]
    return values if len(values) == 4 and finite(values) else [1.0, 0.0, 0.0, 0.0]


def pos_from_sportmode(msg: Any) -> list[float]:
    position = getattr(msg, "position", None)
    if position is None:
        return [0.0, 0.0, 0.0]
    values = [float(v) for v in list(position)[:3]]
    return values if len(values) == 3 and finite(values) else [0.0, 0.0, 0.0]


class DDSState:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.lowstate_msg: Any | None = None
        self.root_pos: list[float] | None = None
        self.start = time.perf_counter()
        self.lowstate_count = 0
        self.sportmode_count = 0

    def update_lowstate(self, msg: Any) -> None:
        with self.lock:
            self.lowstate_msg = msg
            self.lowstate_count += 1

    def update_sportmode(self, msg: Any) -> None:
        with self.lock:
            self.root_pos = pos_from_sportmode(msg)
            self.sportmode_count += 1

    def frame(self, frame_index: int) -> dict[str, Any] | None:
        with self.lock:
            if self.lowstate_msg is None or self.root_pos is None:
                return None
            lowstate = self.lowstate_msg
            root_pos = list(self.root_pos)
            lowstate_count = self.lowstate_count
            sportmode_count = self.sportmode_count
        joint_pos, joint_vel, tau_est = motor_states_from_lowstate(lowstate)
        root_quat = quat_from_lowstate(lowstate)
        qpos = root_pos + root_quat + joint_pos
        if len(qpos) != EXPECTED_NQ or not finite(qpos):
            return None
        tick = int(getattr(lowstate, "tick", frame_index))
        return {
            "format": "physical-ai-stream-frame-v0",
            "frame": frame_index,
            "qpos": qpos,
            "telemetry": {
                "format": "physical-ai-g1-dds-telemetry-v0",
                "t": time.perf_counter() - self.start,
                "tick": tick,
                "joint_count": EXPECTED_JOINTS,
                "joint_pos": joint_pos,
                "joint_vel": joint_vel,
                "tau_est": tau_est,
                "dds_lowstate_count": lowstate_count,
                "dds_sportmode_count": sportmode_count,
                "stream": True,
            },
        }


def start_dds(args: argparse.Namespace, state: DDSState) -> None:
    if args.sdk_path:
        sys.path.insert(0, str(args.sdk_path))
    from unitree_sdk2py.core.channel import ChannelFactoryInitialize, ChannelSubscriber
    from unitree_sdk2py.idl.unitree_go.msg.dds_ import SportModeState_
    from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowState_

    ChannelFactoryInitialize(args.domain_id, args.interface)
    lowstate_subscriber = ChannelSubscriber(args.topic, LowState_)
    lowstate_subscriber.Init(state.update_lowstate, 10)
    sportmode_subscriber = ChannelSubscriber(args.sportmode_topic, SportModeState_)
    sportmode_subscriber.Init(state.update_sportmode, 10)


async def serve(args: argparse.Namespace) -> None:
    state = DDSState()
    start_dds(args, state)
    interval = 1.0 / args.fps
    print(
        json.dumps(
            {
                "event": "ready",
                "contract": "physical-ai-dds-websocket-bridge-v0",
                "host": args.host,
                "port": args.port,
                "fps": args.fps,
                "domain_id": args.domain_id,
                "interface": args.interface or "auto",
            }
        ),
        flush=True,
    )

    async def handler(websocket):
        await websocket.send(json.dumps({"format": "physical-ai-stream-hello-v0", "frames": None, "fps": args.fps}))
        frame_index = 0
        deadline = time.perf_counter() + args.wait_timeout_s
        while True:
            frame = state.frame(frame_index)
            if frame is None:
                if time.perf_counter() > deadline:
                    await websocket.close(code=1011, reason="DDS frame timeout")
                    return
                await asyncio.sleep(0.005)
                continue
            await websocket.send(json.dumps(frame, separators=(",", ":")))
            frame_index += 1
            await asyncio.sleep(interval)

    async with websockets.serve(handler, args.host, args.port):
        await asyncio.Future()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sdk-path", type=Path)
    parser.add_argument("--domain-id", type=int, default=1)
    parser.add_argument("--interface", default=None)
    parser.add_argument("--topic", default="rt/lowstate")
    parser.add_argument("--sportmode-topic", default="rt/sportmodestate")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--fps", type=float, default=50.0)
    parser.add_argument("--wait-timeout-s", type=float, default=10.0)
    args = parser.parse_args()
    asyncio.run(serve(args))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
