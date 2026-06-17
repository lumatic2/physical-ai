#!/usr/bin/env python3
"""Run Unitree MJCF headless runtime -> DDS capture -> candidate gate."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


def run_command(command: list[str], timeout_s: float) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, text=True, capture_output=True, timeout=timeout_s)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sdk-path", required=True, type=Path)
    parser.add_argument("--unitree-root", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--frames", type=int, default=100)
    parser.add_argument("--fps", type=float, default=50.0)
    parser.add_argument("--domain-id", type=int, default=1)
    parser.add_argument("--interface", default=None)
    parser.add_argument("--elastic-band", action="store_true")
    parser.add_argument("--band-length", type=float, default=0.5)
    parser.add_argument("--band-stiffness", type=float, default=200.0)
    parser.add_argument("--band-damping", type=float, default=100.0)
    parser.add_argument("--max-height-range", type=float, default=0.01)
    parser.add_argument("--max-root-height-drop", type=float, default=0.01)
    args = parser.parse_args()

    here = Path(__file__).resolve().parent
    args.out_dir.mkdir(parents=True, exist_ok=True)
    capture_jsonl = args.out_dir / "unitree_mujoco_dds_capture.jsonl"
    publisher_log = args.out_dir / "publisher_stdout.txt"
    publisher_err = args.out_dir / "publisher_stderr.txt"
    capture_log = args.out_dir / "capture_stdout.txt"
    capture_err = args.out_dir / "capture_stderr.txt"
    gate_dir = args.out_dir / "candidate_gate"

    capture_command = [
        sys.executable,
        str(here / "capture_live_lowstate_jsonl.py"),
        "--sdk-path",
        str(args.sdk_path),
        "--output",
        str(capture_jsonl),
        "--frames",
        str(args.frames),
        "--fps",
        str(args.fps),
        "--domain-id",
        str(args.domain_id),
        "--root-pose-source",
        "sportmode",
    ]
    if args.interface:
        capture_command.extend(["--interface", args.interface])

    publisher_command = [
        sys.executable,
        str(here / "publish_unitree_mujoco_g1_dds.py"),
        "--sdk-path",
        str(args.sdk_path),
        "--unitree-root",
        str(args.unitree_root),
        "--frames",
        str(max(args.frames + 20, args.frames)),
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

    capture_proc = subprocess.Popen(capture_command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(0.25)
    publisher_proc = subprocess.Popen(publisher_command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    try:
        publisher_stdout, publisher_stderr = publisher_proc.communicate(timeout=30)
        capture_stdout, capture_stderr = capture_proc.communicate(timeout=30)
    except subprocess.TimeoutExpired:
        publisher_proc.kill()
        capture_proc.kill()
        publisher_stdout, publisher_stderr = publisher_proc.communicate()
        capture_stdout, capture_stderr = capture_proc.communicate()

    publisher_log.write_text(publisher_stdout or "", encoding="utf-8")
    publisher_err.write_text(publisher_stderr or "", encoding="utf-8")
    capture_log.write_text(capture_stdout or "", encoding="utf-8")
    capture_err.write_text(capture_stderr or "", encoding="utf-8")

    gate_summary: dict[str, Any] | None = None
    gate_result: dict[str, Any] = {"ran": False}
    if publisher_proc.returncode == 0 and capture_proc.returncode == 0 and capture_jsonl.exists():
        gate_command = [
            sys.executable,
            str(here / "run_twin_candidate_gate.py"),
            "--capture",
            str(capture_jsonl),
            "--out-dir",
            str(gate_dir),
            "--source",
            "unitree-mujoco-dds-elastic-stand" if args.elastic_band else "unitree-mujoco-dds-pd-hold",
            "--min-frames",
            str(min(40, args.frames)),
            "--max-height-range",
            str(args.max_height_range),
            "--max-root-height-drop",
            str(args.max_root_height_drop),
        ]
        gate_completed = run_command(gate_command, timeout_s=30)
        gate_result = {
            "ran": True,
            "returncode": gate_completed.returncode,
            "stdout": gate_completed.stdout,
            "stderr": gate_completed.stderr,
        }
        summary_path = gate_dir / "candidate_gate_summary.json"
        if summary_path.exists():
            gate_summary = json.loads(summary_path.read_text(encoding="utf-8"))

    summary = {
        "verdict": "PASS" if publisher_proc.returncode == 0 and capture_proc.returncode == 0 and gate_summary and gate_summary.get("verdict") == "PASS" else "FAIL",
        "contract": "physical-ai-unitree-mujoco-dds-capture-smoke-v0",
        "frames": args.frames,
        "fps": args.fps,
        "domain_id": args.domain_id,
        "interface": args.interface or "auto",
        "elastic_band": args.elastic_band,
        "publisher_returncode": publisher_proc.returncode,
        "capture_returncode": capture_proc.returncode,
        "capture_jsonl": str(capture_jsonl),
        "publisher_stdout": str(publisher_log),
        "publisher_stderr": str(publisher_err),
        "capture_stdout": str(capture_log),
        "capture_stderr": str(capture_err),
        "candidate_gate": gate_summary,
        "candidate_gate_process": gate_result,
    }
    summary_path = args.out_dir / "unitree_mujoco_dds_capture_smoke_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if summary["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
