#!/usr/bin/env python3
"""Compare two web trajectory JSON files frame-by-frame."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected", required=True, type=Path)
    parser.add_argument("--actual", required=True, type=Path)
    parser.add_argument("--summary", required=True, type=Path)
    parser.add_argument("--tolerance", type=float, default=1e-9)
    args = parser.parse_args()

    expected = load_json(args.expected)
    actual = load_json(args.actual)
    expected_qpos = expected.get("qpos")
    actual_qpos = actual.get("qpos")
    errors: list[str] = []

    if not isinstance(expected_qpos, list) or not isinstance(actual_qpos, list):
        errors.append("both files must contain qpos lists")
        expected_qpos = expected_qpos if isinstance(expected_qpos, list) else []
        actual_qpos = actual_qpos if isinstance(actual_qpos, list) else []

    if len(expected_qpos) != len(actual_qpos):
        errors.append(f"frame count mismatch: {len(expected_qpos)} vs {len(actual_qpos)}")

    max_abs_diff = 0.0
    max_abs_diff_at = None
    compared_values = 0

    for frame_idx, (expected_frame, actual_frame) in enumerate(zip(expected_qpos, actual_qpos)):
        if not isinstance(expected_frame, list) or not isinstance(actual_frame, list):
            errors.append(f"frame {frame_idx} is not a list in both files")
            continue
        if len(expected_frame) != len(actual_frame):
            errors.append(f"frame {frame_idx} width mismatch: {len(expected_frame)} vs {len(actual_frame)}")
            continue
        for col_idx, (expected_value, actual_value) in enumerate(zip(expected_frame, actual_frame)):
            if not isinstance(expected_value, (int, float)) or not isinstance(actual_value, (int, float)):
                errors.append(f"non-numeric value at frame {frame_idx}, column {col_idx}")
                continue
            if not math.isfinite(expected_value) or not math.isfinite(actual_value):
                errors.append(f"non-finite value at frame {frame_idx}, column {col_idx}")
                continue
            diff = abs(float(expected_value) - float(actual_value))
            compared_values += 1
            if diff > max_abs_diff:
                max_abs_diff = diff
                max_abs_diff_at = {"frame": frame_idx, "column": col_idx}

    if max_abs_diff > args.tolerance:
        errors.append(f"max_abs_diff {max_abs_diff} exceeds tolerance {args.tolerance}")

    summary = {
        "verdict": "PASS" if not errors else "FAIL",
        "expected": str(args.expected),
        "actual": str(args.actual),
        "frames_compared": min(len(expected_qpos), len(actual_qpos)),
        "values_compared": compared_values,
        "max_abs_diff": max_abs_diff,
        "max_abs_diff_at": max_abs_diff_at,
        "tolerance": args.tolerance,
        "errors": errors,
    }

    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if summary["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
