#!/usr/bin/env python3
"""Run Unitree MJCF DDS publisher -> DDS WebSocket bridge smoke."""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import websockets


def finite(values: list[float]) -> bool:
    return all(math.isfinite(v) for v in values)


async def collect_frames(uri: str, target_frames: int, timeout_s: float) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    frames: list[dict[str, Any]] = []
    control: list[dict[str, Any]] = []
    async with websockets.connect(uri) as ws:
        deadline = time.perf_counter() + timeout_s
        while len(frames) < target_frames:
            remaining = deadline - time.perf_counter()
            if remaining <= 0:
                raise TimeoutError(f"timed out after receiving {len(frames)} frames")
            msg = await asyncio.wait_for(ws.recv(), timeout=remaining)
            data = json.loads(msg)
            if data.get("format") == "physical-ai-stream-frame-v0":
                frames.append(data)
            else:
                control.append(data)
    return frames, control


def run_websocket_collect(uri: str, target_frames: int, timeout_s: float) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    return asyncio.run(collect_frames(uri, target_frames, timeout_s))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sdk-path", required=True, type=Path)
    parser.add_argument("--unitree-root", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--frames", type=int, default=75)
    parser.add_argument("--publisher-frames", type=int, default=140)
    parser.add_argument("--fps", type=float, default=50.0)
    parser.add_argument("--domain-id", type=int, default=1)
    parser.add_argument("--interface", default=None)
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--elastic-band", action="store_true")
    parser.add_argument("--band-length", type=float, default=0.5)
    parser.add_argument("--band-stiffness", type=float, default=200.0)
    parser.add_argument("--band-damping", type=float, default=100.0)
    parser.add_argument("--min-fps", type=float, default=20.0)
    parser.add_argument("--max-height-range", type=float, default=0.01)
    args = parser.parse_args()

    here = Path(__file__).resolve().parent
    args.out_dir.mkdir(parents=True, exist_ok=True)
    bridge_stdout_path = args.out_dir / "bridge_stdout.txt"
    bridge_stderr_path = args.out_dir / "bridge_stderr.txt"
    publisher_stdout_path = args.out_dir / "publisher_stdout.txt"
    publisher_stderr_path = args.out_dir / "publisher_stderr.txt"

    bridge_command = [
        sys.executable,
        str(here / "stream_dds_to_websocket.py"),
        "--sdk-path",
        str(args.sdk_path),
        "--domain-id",
        str(args.domain_id),
        "--port",
        str(args.port),
        "--fps",
        str(args.fps),
    ]
    if args.interface:
        bridge_command.extend(["--interface", args.interface])

    publisher_command = [
        sys.executable,
        str(here / "publish_unitree_mujoco_g1_dds.py"),
        "--sdk-path",
        str(args.sdk_path),
        "--unitree-root",
        str(args.unitree_root),
        "--frames",
        str(args.publisher_frames),
        "--fps",
        str(args.fps),
        "--domain-id",
        str(args.domain_id),
        "--warmup-s",
        "0.5",
    ]
    if args.interface:
        publisher_command.extend(["--interface", args.interface])
    if args.elastic_band:
        publisher_command.extend(
            [
                "--elastic-band",
                "--band-length",
                str(args.band_length),
                "--band-stiffness",
                str(args.band_stiffness),
                "--band-damping",
                str(args.band_damping),
            ]
        )

    bridge_proc = subprocess.Popen(bridge_command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(0.5)
    publisher_proc = subprocess.Popen(publisher_command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    frames: list[dict[str, Any]] = []
    control: list[dict[str, Any]] = []
    collect_error: str | None = None
    started = time.perf_counter()
    try:
        frames, control = run_websocket_collect(f"ws://127.0.0.1:{args.port}", args.frames, timeout_s=20)
    except Exception as exc:
        collect_error = f"{type(exc).__name__}: {exc}"

    elapsed = time.perf_counter() - started
    publisher_stdout, publisher_stderr = publisher_proc.communicate(timeout=30)
    bridge_stopped_by_runner = True
    bridge_proc.kill()
    bridge_stdout, bridge_stderr = bridge_proc.communicate(timeout=5)

    publisher_stdout_path.write_text(publisher_stdout or "", encoding="utf-8")
    publisher_stderr_path.write_text(publisher_stderr or "", encoding="utf-8")
    bridge_stdout_path.write_text(bridge_stdout or "", encoding="utf-8")
    bridge_stderr_path.write_text(bridge_stderr or "", encoding="utf-8")

    heights = [float(frame["qpos"][2]) for frame in frames if isinstance(frame.get("qpos"), list) and len(frame["qpos"]) == 36]
    qpos_valid = all(isinstance(frame.get("qpos"), list) and len(frame["qpos"]) == 36 and finite([float(v) for v in frame["qpos"]]) for frame in frames)
    ordered = all(int(frames[i]["frame"]) > int(frames[i - 1]["frame"]) for i in range(1, len(frames)))
    measured_fps = (len(frames) / elapsed) if elapsed > 0 else 0.0
    height_range = (max(heights) - min(heights)) if heights else None
    pass_checks = {
        "collector_pass": collect_error is None,
        "publisher_pass": publisher_proc.returncode == 0,
        "received_frames_pass": len(frames) >= args.frames,
        "qpos_valid_pass": qpos_valid,
        "ordered_pass": ordered,
        "fps_pass": measured_fps >= args.min_fps,
        "height_range_pass": height_range is not None and height_range <= args.max_height_range,
    }
    summary = {
        "verdict": "PASS" if all(pass_checks.values()) else "FAIL",
        "contract": "physical-ai-unitree-mujoco-dds-websocket-smoke-v0",
        "frames_requested": args.frames,
        "frames_received": len(frames),
        "control_messages": control,
        "fps_target": args.fps,
        "measured_fps": measured_fps,
        "domain_id": args.domain_id,
        "interface": args.interface or "auto",
        "elastic_band": args.elastic_band,
        "height_range_m": height_range,
        "start_height_m": heights[0] if heights else None,
        "end_height_m": heights[-1] if heights else None,
        "checks": pass_checks,
        "collect_error": collect_error,
        "publisher_returncode": publisher_proc.returncode,
        "bridge_returncode": bridge_proc.returncode,
        "bridge_stopped_by_runner": bridge_stopped_by_runner,
        "publisher_stdout": str(publisher_stdout_path),
        "publisher_stderr": str(publisher_stderr_path),
        "bridge_stdout": str(bridge_stdout_path),
        "bridge_stderr": str(bridge_stderr_path),
        "sample_last_frame": frames[-1] if frames else None,
    }
    summary_path = args.out_dir / "unitree_mujoco_dds_websocket_smoke_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if summary["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
