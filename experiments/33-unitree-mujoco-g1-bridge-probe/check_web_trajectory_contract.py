#!/usr/bin/env python3
"""Validate a web trajectory against physical-ai-web-trajectory-v1."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def validate_trajectory(data: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    fps = data.get("fps")
    nq = data.get("nq")
    scene = data.get("scene")
    qpos = data.get("qpos")

    if not isinstance(fps, (int, float)) or float(fps) <= 0:
        errors.append("fps must be a positive number")
    if not isinstance(nq, int) or nq <= 0:
        errors.append("nq must be a positive integer")
    if not isinstance(scene, str) or not scene:
        errors.append("scene must be a non-empty string")
    if not isinstance(qpos, list) or not qpos:
        errors.append("qpos must be a non-empty list")

    frames = len(qpos) if isinstance(qpos, list) else 0
    finite_valid = True
    shape_valid = True
    heights: list[float] = []
    if isinstance(qpos, list) and isinstance(nq, int):
        for fi, frame in enumerate(qpos):
            if not isinstance(frame, list) or len(frame) != nq:
                shape_valid = False
                errors.append(f"qpos[{fi}] length mismatch")
                continue
            for vi, value in enumerate(frame):
                if not isinstance(value, (int, float)) or not math.isfinite(float(value)):
                    finite_valid = False
                    errors.append(f"qpos[{fi}][{vi}] is not finite")
            if len(frame) >= 3 and isinstance(frame[2], (int, float)):
                heights.append(float(frame[2]))

    if not shape_valid:
        errors.append("shape_valid is false")
    if not finite_valid:
        errors.append("finite_valid is false")

    fps_value = float(fps) if isinstance(fps, (int, float)) and float(fps) > 0 else 0.0
    summary = {
        "verdict": "PASS" if not errors else "FAIL",
        "contract": "physical-ai-web-trajectory-v1",
        "frames": frames,
        "fps": fps_value,
        "duration_s": frames / fps_value if fps_value else None,
        "nq": nq,
        "scene": scene,
        "shape_valid": shape_valid,
        "finite_valid": finite_valid,
        "start_height_m": heights[0] if heights else None,
        "min_height_m": min(heights) if heights else None,
        "max_height_m": max(heights) if heights else None,
        "end_height_m": heights[-1] if heights else None,
        "root_height_drop_m": (heights[0] - min(heights)) if heights else None,
        "errors": errors,
    }
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trajectory", required=True, type=Path)
    parser.add_argument("--summary", required=True, type=Path)
    args = parser.parse_args()

    data = load_json(args.trajectory)
    summary = validate_trajectory(data)
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if summary["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
