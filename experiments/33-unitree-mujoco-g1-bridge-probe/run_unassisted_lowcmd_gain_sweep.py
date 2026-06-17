#!/usr/bin/env python3
"""Sweep LowCmd gains for unassisted browser closed-loop stability."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def load_summary(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else None


def nested_json_stdout(summary: dict[str, Any] | None) -> dict[str, Any] | None:
    if not summary:
        return None
    candidate = summary.get("candidate_summary")
    if not isinstance(candidate, dict):
        return None
    stdout = candidate.get("stdout")
    if not isinstance(stdout, str):
        return None
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def metrics_from(summary: dict[str, Any] | None) -> dict[str, Any]:
    browser = nested_json_stdout(summary)
    stream = browser.get("stream") if isinstance(browser, dict) else None
    publisher = summary.get("publisher_summary") if isinstance(summary, dict) else None
    return {
        "browser_verdict": browser.get("verdict") if isinstance(browser, dict) else None,
        "received": stream.get("received") if isinstance(stream, dict) else None,
        "measured_fps": stream.get("measuredFps") if isinstance(stream, dict) else None,
        "height_range_m": stream.get("heightRange") if isinstance(stream, dict) else None,
        "height_m": stream.get("height") if isinstance(stream, dict) else None,
        "publisher_root_height_drop_m": publisher.get("root_height_drop_m") if isinstance(publisher, dict) else None,
        "lowcmd_received_count": publisher.get("lowcmd_received_count") if isinstance(publisher, dict) else None,
    }


def score(result: dict[str, Any]) -> float:
    metrics = result.get("metrics") or {}
    height_range = metrics.get("height_range_m")
    root_drop = metrics.get("publisher_root_height_drop_m")
    if height_range is None and root_drop is None:
        return float("inf")
    return float(height_range or 0.0) + float(root_drop or 0.0)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sdk-path", required=True, type=Path)
    parser.add_argument("--unitree-root", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--domain-start", type=int, default=70)
    parser.add_argument("--web-port-start", type=int, default=8150)
    parser.add_argument("--stream-port-start", type=int, default=8910)
    parser.add_argument("--frames", type=int, default=45)
    parser.add_argument("--publisher-frames", type=int, default=170)
    parser.add_argument("--timeout-s", type=float, default=75.0)
    parser.add_argument(
        "--candidate",
        action="append",
        default=[],
        help="Gain candidate as kp_scale,kd_scale. Can be repeated.",
    )
    args = parser.parse_args()

    candidates = args.candidate or ["0.5,1.0", "1.0,1.0", "1.5,1.5", "2.0,2.0", "1.0,3.0"]
    parsed: list[tuple[float, float]] = []
    for candidate in candidates:
        kp_s, kd_s = candidate.split(",", 1)
        parsed.append((float(kp_s), float(kd_s)))

    here = Path(__file__).resolve().parent
    args.out_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    for idx, (kp_scale, kd_scale) in enumerate(parsed):
        run_dir = args.out_dir / f"kp{kp_scale:g}_kd{kd_scale:g}".replace(".", "p")
        command = [
            sys.executable,
            str(here / "run_lowcmd_browser_closed_loop_smoke.py"),
            "--sdk-path",
            str(args.sdk_path),
            "--unitree-root",
            str(args.unitree_root),
            "--out-dir",
            str(run_dir),
            "--domain-id",
            str(args.domain_start + idx),
            "--web-port",
            str(args.web_port_start + idx),
            "--stream-port",
            str(args.stream_port_start + idx),
            "--frames",
            str(args.frames),
            "--publisher-frames",
            str(args.publisher_frames),
            "--timeout-s",
            str(args.timeout_s),
            "--kp-scale",
            str(kp_scale),
            "--kd-scale",
            str(kd_scale),
            "--no-elastic-band",
        ]
        completed = subprocess.run(command, text=True, capture_output=True, timeout=args.timeout_s + 20)
        summary_path = run_dir / "lowcmd_browser_closed_loop_smoke_summary.json"
        summary = load_summary(summary_path)
        result = {
            "kp_scale": kp_scale,
            "kd_scale": kd_scale,
            "returncode": completed.returncode,
            "summary_path": str(summary_path),
            "verdict": summary.get("verdict") if summary else "MISSING",
            "metrics": metrics_from(summary),
        }
        results.append(result)

    best = min(results, key=score) if results else None
    passing = [r for r in results if r.get("verdict") == "PASS"]
    summary = {
        "verdict": "PASS" if passing else "FAIL_EXPECTED",
        "contract": "physical-ai-unassisted-lowcmd-gain-sweep-v0",
        "interpretation": (
            "Searches for an unassisted LowCmd browser closed-loop candidate. "
            "A PASS candidate could be promoted to unassisted completion evidence; otherwise failures document controller instability."
        ),
        "candidates": results,
        "best_by_height_score": best,
        "passing_candidates": passing,
    }
    out_path = args.out_dir / "unassisted_lowcmd_gain_sweep_summary.json"
    out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if passing else 1


if __name__ == "__main__":
    raise SystemExit(main())
