#!/usr/bin/env python3
"""Run Unitree RL Lab G1-29DOF policy -> MuJoCo DDS -> browser candidate gate."""

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
    parser.add_argument("--rl-lab-policy-dir", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--domain-id", type=int, default=92)
    parser.add_argument("--web-port", type=int, default=8148)
    parser.add_argument("--stream-port", type=int, default=8908)
    parser.add_argument("--frames", type=int, default=100)
    parser.add_argument("--publisher-frames", type=int, default=180)
    parser.add_argument("--fps", type=float, default=50.0)
    parser.add_argument("--min-fps", type=float, default=15.0)
    parser.add_argument("--max-height-range", type=float, default=0.08)
    parser.add_argument("--kp", type=float, default=80.0)
    parser.add_argument("--kd", type=float, default=3.0)
    parser.add_argument("--rl-command", nargs=3, type=float, default=[0.0, 0.0, 0.0])
    parser.add_argument("--timeout-s", type=float, default=120.0)
    args = parser.parse_args()

    here = Path(__file__).resolve().parent
    args.out_dir.mkdir(parents=True, exist_ok=True)
    publisher_stdout_path = args.out_dir / "rl_lab_policy_publisher_stdout.txt"
    publisher_stderr_path = args.out_dir / "rl_lab_policy_publisher_stderr.txt"

    candidate_command = [
        sys.executable,
        str(here / "run_external_dds_browser_candidate.py"),
        "--sdk-path",
        str(args.sdk_path),
        "--candidate-kind",
        "unassisted-controller",
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
        "rl-lab-policy",
        "--rl-lab-policy-dir",
        str(args.rl_lab_policy_dir),
        "--kp",
        str(args.kp),
        "--kd",
        str(args.kd),
        "--rl-command",
        *[str(v) for v in args.rl_command],
    ]

    started = time.perf_counter()
    candidate_proc = subprocess.Popen(candidate_command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(1.5)
    publisher_proc = subprocess.Popen(publisher_command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        candidate_stdout, candidate_stderr = candidate_proc.communicate(timeout=args.timeout_s + 10)
        candidate_returncode = candidate_proc.returncode
    except subprocess.TimeoutExpired:
        candidate_proc.kill()
        candidate_stdout, candidate_stderr = candidate_proc.communicate(timeout=5)
        candidate_returncode = 124
    elapsed = time.perf_counter() - started

    try:
        publisher_stdout, publisher_stderr = publisher_proc.communicate(timeout=45)
        publisher_returncode = publisher_proc.returncode
    except subprocess.TimeoutExpired:
        publisher_returncode, publisher_stdout, publisher_stderr = terminate(publisher_proc)
    publisher_stdout_path.write_text(publisher_stdout, encoding="utf-8")
    publisher_stderr_path.write_text(publisher_stderr, encoding="utf-8")

    candidate_summary_path = args.out_dir / "browser_candidate_gate" / "candidate_gate_summary.json"
    candidate_summary = None
    if candidate_summary_path.exists():
        candidate_summary = json.loads(candidate_summary_path.read_text(encoding="utf-8"))
    publisher_summary = parse_last_json(publisher_stdout)

    checks = {
        "candidate_pass": candidate_returncode == 0 and bool(candidate_summary and candidate_summary.get("verdict") == "PASS"),
        "publisher_pass": publisher_returncode == 0,
        "publisher_used_rl_lab_policy": (publisher_summary or {}).get("control_source") == "rl-lab-policy",
        "policy_actions_generated": int((publisher_summary or {}).get("rl_policy_action_count") or 0) > 0,
        "unassisted": not bool((publisher_summary or {}).get("elastic_band")),
    }
    summary = {
        "verdict": "PASS" if all(checks.values()) else "FAIL",
        "contract": "physical-ai-rl-lab-policy-browser-candidate-v0",
        "note": "Unassisted Unitree RL Lab G1-29DOF policy drives official Unitree MuJoCo, publishes DDS state, and is checked in the browser twin.",
        "domain_id": args.domain_id,
        "web_port": args.web_port,
        "stream_port": args.stream_port,
        "frames": args.frames,
        "publisher_frames": args.publisher_frames,
        "fps": args.fps,
        "max_height_range_m": args.max_height_range,
        "kp": args.kp,
        "kd": args.kd,
        "rl_command": args.rl_command,
        "elapsed_s": elapsed,
        "checks": checks,
        "candidate_command": candidate_command,
        "publisher_command": publisher_command,
        "candidate_returncode": candidate_returncode,
        "candidate_stdout": candidate_stdout,
        "candidate_stderr": candidate_stderr,
        "publisher_returncode": publisher_returncode,
        "publisher_stdout": str(publisher_stdout_path),
        "publisher_stderr": str(publisher_stderr_path),
        "candidate_summary": candidate_summary,
        "publisher_summary": publisher_summary,
    }
    summary_path = args.out_dir / "rl_lab_policy_browser_candidate_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (args.out_dir / "candidate_gate_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if summary["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
