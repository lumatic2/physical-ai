#!/usr/bin/env python3
"""Run LowCmd -> Unitree MuJoCo -> DDS WebSocket -> browser QA."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


def terminate(proc: subprocess.Popen[str]) -> tuple[int | None, str, str]:
    if proc.poll() is None:
        proc.terminate()
        try:
            stdout, stderr = proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout, stderr = proc.communicate(timeout=5)
    else:
        stdout, stderr = proc.communicate(timeout=5)
    return proc.returncode, stdout or "", stderr or ""


def parse_last_json(text: str) -> dict[str, Any] | None:
    start = text.rfind("{")
    while start >= 0:
        try:
            data = json.loads(text[start:])
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            start = text.rfind("{", 0, start)
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sdk-path", required=True, type=Path)
    parser.add_argument("--unitree-root", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--candidate-kind", choices=["real-robot", "unassisted-controller"], default="unassisted-controller")
    parser.add_argument("--domain-id", type=int, default=64)
    parser.add_argument("--web-port", type=int, default=8146)
    parser.add_argument("--stream-port", type=int, default=8906)
    parser.add_argument("--frames", type=int, default=60)
    parser.add_argument("--publisher-frames", type=int, default=220)
    parser.add_argument("--fps", type=float, default=50.0)
    parser.add_argument("--min-fps", type=float, default=15.0)
    parser.add_argument("--max-height-range", type=float, default=0.01)
    parser.add_argument("--kp-scale", type=float, default=1.0)
    parser.add_argument("--kd-scale", type=float, default=1.0)
    parser.add_argument("--timeout-s", type=float, default=90.0)
    parser.add_argument("--elastic-band", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--band-length", type=float, default=0.5)
    parser.add_argument("--band-stiffness", type=float, default=200.0)
    parser.add_argument("--band-damping", type=float, default=100.0)
    args = parser.parse_args()

    here = Path(__file__).resolve().parent
    args.out_dir.mkdir(parents=True, exist_ok=True)
    publisher_stdout_path = args.out_dir / "lowcmd_mujoco_publisher_stdout.txt"
    publisher_stderr_path = args.out_dir / "lowcmd_mujoco_publisher_stderr.txt"
    lowcmd_stdout_path = args.out_dir / "lowcmd_stdout.txt"
    lowcmd_stderr_path = args.out_dir / "lowcmd_stderr.txt"

    candidate_command = [
        sys.executable,
        str(here / "run_external_dds_browser_candidate.py"),
        "--sdk-path",
        str(args.sdk_path),
        "--candidate-kind",
        args.candidate_kind,
        "--domain-id",
        str(args.domain_id),
        "--web-port",
        str(args.web_port),
        "--stream-port",
        str(args.stream_port),
        "--frames",
        str(args.frames),
        "--min-fps",
        str(args.min_fps),
        "--max-height-range",
        str(args.max_height_range),
        "--timeout-s",
        str(args.timeout_s),
        "--out-dir",
        str(args.out_dir / "browser_candidate_gate"),
    ]
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
        "--control-source",
        "dds-lowcmd",
    ]
    lowcmd_command = [
        sys.executable,
        str(here / "run_local_lowcmd_contract_smoke.py"),
        "--sdk-path",
        str(args.sdk_path),
        "--unitree-root",
        str(args.unitree_root),
        "--hold-initial-q",
        "--out",
        str(args.out_dir / "lowcmd_contract_summary.json"),
        "--domain-id",
        str(args.domain_id),
        "--frames",
        str(args.publisher_frames),
        "--fps",
        str(args.fps),
        "--kp-scale",
        str(args.kp_scale),
        "--kd-scale",
        str(args.kd_scale),
    ]
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

    started = time.perf_counter()
    candidate_proc = subprocess.Popen(candidate_command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(1.5)
    publisher_proc = subprocess.Popen(publisher_command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(0.75)
    lowcmd_proc = subprocess.Popen(lowcmd_command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    try:
        candidate_stdout, candidate_stderr = candidate_proc.communicate(timeout=args.timeout_s + 10)
        candidate_returncode = candidate_proc.returncode
    except subprocess.TimeoutExpired:
        candidate_proc.kill()
        candidate_stdout, candidate_stderr = candidate_proc.communicate(timeout=5)
        candidate_returncode = 124
    elapsed = time.perf_counter() - started

    lowcmd_returncode, lowcmd_stdout, lowcmd_stderr = terminate(lowcmd_proc)
    publisher_returncode, publisher_stdout, publisher_stderr = terminate(publisher_proc)
    lowcmd_stdout_path.write_text(lowcmd_stdout, encoding="utf-8")
    lowcmd_stderr_path.write_text(lowcmd_stderr, encoding="utf-8")
    publisher_stdout_path.write_text(publisher_stdout, encoding="utf-8")
    publisher_stderr_path.write_text(publisher_stderr, encoding="utf-8")

    candidate_summary_path = args.out_dir / "browser_candidate_gate" / "candidate_gate_summary.json"
    candidate_summary = None
    if candidate_summary_path.exists():
        candidate_summary = json.loads(candidate_summary_path.read_text(encoding="utf-8"))
    publisher_summary = parse_last_json(publisher_stdout)
    lowcmd_summary = parse_last_json(lowcmd_stdout)
    lowcmd_received_count = int((publisher_summary or {}).get("lowcmd_received_count") or 0)
    checks = {
        "candidate_pass": candidate_returncode == 0 and bool(candidate_summary and candidate_summary.get("verdict") == "PASS"),
        "publisher_pass": publisher_returncode == 0,
        "lowcmd_pass": lowcmd_returncode == 0,
        "publisher_used_dds_lowcmd": (publisher_summary or {}).get("control_source") == "dds-lowcmd",
        "publisher_received_lowcmd": lowcmd_received_count > 0,
    }
    summary = {
        "verdict": "PASS" if all(checks.values()) else "FAIL",
        "contract": "physical-ai-lowcmd-browser-closed-loop-smoke-v0",
        "note": (
            "Assisted simulated LowCmd browser smoke only; do not count as real robot or unassisted completion evidence."
            if args.elastic_band
            else "Unassisted simulated LowCmd browser smoke; PASS would be candidate evidence, FAIL documents controller instability."
        ),
        "candidate_kind": args.candidate_kind,
        "domain_id": args.domain_id,
        "web_port": args.web_port,
        "stream_port": args.stream_port,
        "elastic_band": args.elastic_band,
        "frames": args.frames,
        "publisher_frames": args.publisher_frames,
        "kp_scale": args.kp_scale,
        "kd_scale": args.kd_scale,
        "elapsed_s": elapsed,
        "checks": checks,
        "candidate_command": candidate_command,
        "publisher_command": publisher_command,
        "lowcmd_command": lowcmd_command,
        "candidate_returncode": candidate_returncode,
        "candidate_stdout": candidate_stdout,
        "candidate_stderr": candidate_stderr,
        "publisher_returncode": publisher_returncode,
        "publisher_stdout": str(publisher_stdout_path),
        "publisher_stderr": str(publisher_stderr_path),
        "lowcmd_returncode": lowcmd_returncode,
        "lowcmd_stdout": str(lowcmd_stdout_path),
        "lowcmd_stderr": str(lowcmd_stderr_path),
        "candidate_summary": candidate_summary,
        "publisher_summary": publisher_summary,
        "lowcmd_summary": lowcmd_summary,
    }
    summary_path = args.out_dir / "lowcmd_browser_closed_loop_smoke_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if summary["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
