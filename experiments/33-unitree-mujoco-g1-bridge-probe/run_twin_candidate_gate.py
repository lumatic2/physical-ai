#!/usr/bin/env python3
"""Run the file-level digital twin candidate gate for a Unitree G1 capture.

This is the offline counterpart of the browser stream QA:
capture JSON/JSONL -> normalized LowState -> web trajectory + telemetry sidecar
-> web trajectory contract -> stability gate.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

from bridge_lowstate_trace import convert as bridge_lowstate
from check_web_trajectory_contract import validate_trajectory
from normalize_live_lowstate_capture import load_capture, normalize


DEFAULT_SCENE = "g1/scene_g1_policy.xml"


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def finite_matrix(values: list[list[float]]) -> bool:
    return all(isinstance(v, (int, float)) and math.isfinite(float(v)) for row in values for v in row)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--source", default="candidate-capture")
    parser.add_argument("--scene", default=DEFAULT_SCENE)
    parser.add_argument("--fallback-fps", type=float, default=50.0)
    parser.add_argument("--min-frames", type=int, default=40)
    parser.add_argument("--max-height-range", type=float, default=0.01)
    parser.add_argument("--max-root-height-drop", type=float, default=0.01)
    args = parser.parse_args()

    normalized, normalize_summary = normalize(load_capture(args.capture), args.source, args.fallback_fps)
    trajectory, telemetry, bridge_summary = bridge_lowstate(normalized, args.scene)
    contract_summary = validate_trajectory(trajectory)
    qpos = trajectory["qpos"]
    heights = [float(frame[2]) for frame in qpos]
    height_range = max(heights) - min(heights)
    root_height_drop = heights[0] - min(heights)

    checks = {
        "normalize_pass": str(normalize_summary["verdict"]).startswith("PASS"),
        "bridge_pass": str(bridge_summary["verdict"]).startswith("PASS"),
        "contract_pass": str(contract_summary["verdict"]).startswith("PASS"),
        "finite_pass": finite_matrix(qpos),
        "min_frames_pass": len(qpos) >= args.min_frames,
        "height_range_pass": height_range <= args.max_height_range,
        "root_height_drop_pass": root_height_drop <= args.max_root_height_drop,
    }
    verdict = "PASS" if all(checks.values()) else "FAIL"

    summary = {
        "verdict": verdict,
        "contract": "physical-ai-g1-twin-candidate-gate-v0",
        "capture": str(args.capture),
        "source": args.source,
        "scene": args.scene,
        "thresholds": {
            "min_frames": args.min_frames,
            "max_height_range_m": args.max_height_range,
            "max_root_height_drop_m": args.max_root_height_drop,
        },
        "checks": checks,
        "metrics": {
            "frames": len(qpos),
            "fps": trajectory["fps"],
            "duration_s": len(qpos) / trajectory["fps"],
            "nq": trajectory["nq"],
            "joint_count": telemetry["joint_count"],
            "start_height_m": heights[0],
            "min_height_m": min(heights),
            "max_height_m": max(heights),
            "end_height_m": heights[-1],
            "height_range_m": height_range,
            "root_height_drop_m": root_height_drop,
        },
        "artifacts": {
            "normalized": "normalized_lowstate_trace.json",
            "trajectory": "web_trajectory.json",
            "telemetry": "telemetry_sidecar.json",
            "normalize_summary": "normalize_summary.json",
            "bridge_summary": "bridge_summary.json",
            "contract_summary": "contract_summary.json",
        },
        "next_required_evidence": "For full digital twin completion, run this on live DDS LowState + root pose capture or an unassisted controller trace.",
    }

    write_json(args.out_dir / "normalized_lowstate_trace.json", normalized)
    write_json(args.out_dir / "web_trajectory.json", trajectory)
    write_json(args.out_dir / "telemetry_sidecar.json", telemetry)
    write_json(args.out_dir / "normalize_summary.json", normalize_summary)
    write_json(args.out_dir / "bridge_summary.json", bridge_summary)
    write_json(args.out_dir / "contract_summary.json", contract_summary)
    write_json(args.out_dir / "candidate_gate_summary.json", summary)
    print(json.dumps(summary, indent=2))
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
