#!/usr/bin/env python3
"""Launch the local browser G1 twin demo with DDS bridge and optional sim publisher."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path


def build_commands(args: argparse.Namespace, repo_root: Path) -> dict[str, list[str]]:
    web_dir = repo_root / "experiments" / "03-digital-twin" / "web"
    exp33 = repo_root / "experiments" / "33-unitree-mujoco-g1-bridge-probe"
    commands: dict[str, list[str]] = {
        "web": [sys.executable, "serve_coi.py", str(args.web_port)],
        "dds_bridge": [
            sys.executable,
            str(exp33 / "stream_dds_to_websocket.py"),
            "--sdk-path",
            str(args.sdk_path),
            "--domain-id",
            str(args.domain_id),
            "--port",
            str(args.stream_port),
            "--fps",
            str(args.fps),
        ],
    }
    if args.interface:
        commands["dds_bridge"].extend(["--interface", args.interface])
    if args.publisher == "unitree-mujoco":
        publisher = [
            sys.executable,
            str(exp33 / "publish_unitree_mujoco_g1_dds.py"),
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
            str(args.warmup_s),
        ]
        if args.interface:
            publisher.extend(["--interface", args.interface])
        if args.elastic_band:
            publisher.extend(
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
        commands["publisher"] = publisher
    commands["_web_cwd"] = [str(web_dir)]
    return commands


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sdk-path", required=True, type=Path)
    parser.add_argument("--unitree-root", type=Path)
    parser.add_argument("--publisher", choices=["unitree-mujoco", "external"], default="unitree-mujoco")
    parser.add_argument("--domain-id", type=int, default=41)
    parser.add_argument("--interface", default=None)
    parser.add_argument("--web-port", type=int, default=8140)
    parser.add_argument("--stream-port", type=int, default=8900)
    parser.add_argument("--fps", type=float, default=50.0)
    parser.add_argument("--publisher-frames", type=int, default=1000000)
    parser.add_argument("--warmup-s", type=float, default=0.5)
    parser.add_argument("--elastic-band", action="store_true")
    parser.add_argument("--band-length", type=float, default=0.5)
    parser.add_argument("--band-stiffness", type=float, default=200.0)
    parser.add_argument("--band-damping", type=float, default=100.0)
    parser.add_argument("--exp", default="unitree-g1-elastic-stand")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    if args.publisher == "unitree-mujoco" and not args.unitree_root:
        raise SystemExit("--unitree-root is required when --publisher unitree-mujoco")

    commands = build_commands(args, repo_root)
    url = f"http://127.0.0.1:{args.web_port}/?exp={args.exp}&stream=ws%3A%2F%2F127.0.0.1%3A{args.stream_port}"
    summary = {
        "contract": "physical-ai-live-twin-demo-launcher-v0",
        "url": url,
        "domain_id": args.domain_id,
        "web_port": args.web_port,
        "stream_port": args.stream_port,
        "publisher": args.publisher,
        "elastic_band": args.elastic_band,
        "commands": {key: value for key, value in commands.items() if not key.startswith("_")},
        "note": "Assisted sim publisher is a demo source. Use --publisher external for real robot DDS topics on the same domain.",
    }
    print(json.dumps(summary, indent=2))
    if args.dry_run:
        return 0

    web_dir = Path(commands["_web_cwd"][0])
    processes: list[subprocess.Popen[str]] = []
    try:
        processes.append(subprocess.Popen(commands["web"], cwd=web_dir, text=True))
        processes.append(subprocess.Popen(commands["dds_bridge"], cwd=repo_root, text=True))
        if "publisher" in commands:
            time.sleep(0.5)
            processes.append(subprocess.Popen(commands["publisher"], cwd=repo_root, text=True))
        print(f"\nOpen: {url}\nPress Ctrl+C to stop.")
        while True:
            time.sleep(1.0)
            for proc in processes:
                if proc.poll() is not None:
                    raise RuntimeError(f"process exited early with code {proc.returncode}")
    except KeyboardInterrupt:
        return 0
    finally:
        for proc in processes:
            if proc.poll() is None:
                proc.terminate()


if __name__ == "__main__":
    raise SystemExit(main())
