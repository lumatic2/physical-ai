#!/usr/bin/env python3
"""Run browser QA against an external DDS source and write a completion candidate summary."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sdk-path", required=True, type=Path)
    parser.add_argument("--candidate-kind", choices=["real-robot", "unassisted-controller"], required=True)
    parser.add_argument("--domain-id", type=int, required=True)
    parser.add_argument("--web-port", type=int, default=8142)
    parser.add_argument("--stream-port", type=int, default=8902)
    parser.add_argument("--frames", type=int, default=120)
    parser.add_argument("--min-fps", type=float, default=15.0)
    parser.add_argument("--max-height-range", type=float, default=0.01)
    parser.add_argument("--exp", default="unitree-g1-elastic-stand")
    parser.add_argument("--out-dir", type=Path)
    parser.add_argument("--timeout-s", type=float, default=150.0)
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    web_qa = repo_root / "experiments" / "03-digital-twin" / "web" / "qa" / "dds_stream_check.mjs"
    out_dir = args.out_dir or (
        repo_root
        / "experiments"
        / "33-unitree-mujoco-g1-bridge-probe"
        / "verify"
        / ("real-robot-dds-candidate" if args.candidate_kind == "real-robot" else "unassisted-controller-candidate")
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    label = args.candidate_kind
    command = [
        "node",
        str(web_qa),
        f"--sdk-path={args.sdk_path}",
        "--publisher=external",
        f"--domain-id={args.domain_id}",
        f"--web-port={args.web_port}",
        f"--stream-port={args.stream_port}",
        f"--exp={args.exp}",
        f"--label={label}",
        f"--frames={args.frames}",
        f"--min-fps={args.min_fps}",
        f"--max-height-range={args.max_height_range}",
    ]
    timed_out = False
    try:
        completed = subprocess.run(command, cwd=repo_root, text=True, capture_output=True, timeout=args.timeout_s)
        returncode = completed.returncode
        stdout = completed.stdout
        stderr = completed.stderr
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        returncode = 124
        stdout = exc.stdout if isinstance(exc.stdout, str) else (exc.stdout or b"").decode(errors="replace")
        stderr = exc.stderr if isinstance(exc.stderr, str) else (exc.stderr or b"").decode(errors="replace")
    summary = {
        "verdict": "PASS" if returncode == 0 else "FAIL",
        "contract": "physical-ai-external-dds-browser-candidate-v0",
        "candidate_kind": args.candidate_kind,
        "domain_id": args.domain_id,
        "web_port": args.web_port,
        "stream_port": args.stream_port,
        "frames": args.frames,
        "thresholds": {
            "min_fps": args.min_fps,
            "max_height_range_m": args.max_height_range,
        },
        "command": command,
        "timeout_s": args.timeout_s,
        "timed_out": timed_out,
        "returncode": returncode,
        "stdout": stdout,
        "stderr": stderr,
        "next_step_if_fail": "Start an external Unitree SDK2 DDS publisher on the same domain/topic and rerun this gate.",
    }
    out_path = out_dir / "candidate_gate_summary.json"
    out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if returncode == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
