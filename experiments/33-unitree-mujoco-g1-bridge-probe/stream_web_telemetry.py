#!/usr/bin/env python3
"""Serve web twin stream frames over WebSocket from trajectory + telemetry sidecar."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

import websockets


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def build_frames(trajectory: dict[str, Any], telemetry: dict[str, Any]) -> list[str]:
    qpos = trajectory.get("qpos")
    telemetry_frames = telemetry.get("frames")
    if not isinstance(qpos, list) or not isinstance(telemetry_frames, list):
        raise ValueError("trajectory.qpos and telemetry.frames must be lists")
    if len(qpos) != len(telemetry_frames):
        raise ValueError(f"frame mismatch: qpos={len(qpos)} telemetry={len(telemetry_frames)}")
    out: list[str] = []
    for idx, (q, t) in enumerate(zip(qpos, telemetry_frames)):
        if not isinstance(q, list):
            raise ValueError(f"qpos[{idx}] must be a list")
        if not isinstance(t, dict):
            raise ValueError(f"telemetry.frames[{idx}] must be an object")
        out.append(
            json.dumps(
                {
                    "format": "physical-ai-stream-frame-v0",
                    "frame": idx,
                    "qpos": q,
                    "telemetry": {
                        "format": telemetry.get("format"),
                        "t": t.get("t", idx / float(trajectory.get("fps", 50.0))),
                        "tick": t.get("tick", idx),
                        "joint_count": telemetry.get("joint_count"),
                        "joint_pos": t.get("joint_pos"),
                        "joint_vel": t.get("joint_vel"),
                        "tau_est": t.get("tau_est"),
                    },
                },
                separators=(",", ":"),
            )
        )
    return out


async def serve(args: argparse.Namespace) -> None:
    frames = build_frames(load_json(args.trajectory), load_json(args.telemetry))
    interval = 1.0 / args.fps
    print(json.dumps({"event": "ready", "host": args.host, "port": args.port, "frames": len(frames), "fps": args.fps}))

    async def handler(websocket):
        await websocket.send(json.dumps({"format": "physical-ai-stream-hello-v0", "frames": len(frames), "fps": args.fps}))
        loops = 0
        while args.loops <= 0 or loops < args.loops:
            for payload in frames:
                await websocket.send(payload)
                await asyncio.sleep(interval)
            loops += 1

    async with websockets.serve(handler, args.host, args.port):
        await asyncio.Future()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trajectory", required=True, type=Path)
    parser.add_argument("--telemetry", required=True, type=Path)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--fps", type=float, default=50.0)
    parser.add_argument("--loops", type=int, default=0, help="0 means loop forever")
    args = parser.parse_args()
    asyncio.run(serve(args))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
