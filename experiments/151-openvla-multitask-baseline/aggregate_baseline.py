#!/usr/bin/env python3
"""Recompute the GEN2 OpenVLA baseline only from the canonical 60-cell index."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from run_baseline import load_runner_contract
from verify_execution import validate_index


REPORT_VERSION = "physical-ai-gen2-baseline-report-v1"


def canonical_text_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def metric(values: list[float]) -> dict[str, float]:
    ordered = sorted(values)
    p95_index = max(0, math.ceil(len(ordered) * 0.95) - 1)
    return {
        "min": round(ordered[0], 3),
        "median": round(statistics.median(ordered), 3),
        "mean": round(statistics.fmean(ordered), 3),
        "p95": round(ordered[p95_index], 3),
        "max": round(ordered[-1], 3),
    }


def outcome_summary(cells: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter(cell["outcome"] for cell in cells)
    return {
        "denominator": len(cells),
        "success": counts["success"],
        "timeout": counts["timeout"],
        "success_rate": round(counts["success"] / len(cells), 6),
        "frames": metric([float(cell["frames"]) for cell in cells]),
        "wall_seconds": metric([float(cell["wall_seconds"]) for cell in cells]),
    }


def representative(cell: dict[str, Any]) -> dict[str, Any]:
    return {
        key: cell[key]
        for key in (
            "run_key",
            "suite",
            "task_id",
            "state_index",
            "outcome",
            "frames",
            "artifact_ref",
            "manifest_sha256",
        )
    }


def build_report(index: dict[str, Any], source_sha256: str) -> dict[str, Any]:
    expected = [cell["run_key"] for cell in load_runner_contract()["cells"]]
    errors = validate_index(index, expected)
    cells = index.get("cells", [])
    if index.get("pending_cells") != 0 or index.get("terminal_cells") != 60:
        errors.append("aggregate requires 60 terminal and zero pending cells")
    if any(cell.get("outcome") not in {"success", "timeout"} for cell in cells):
        errors.append("infrastructure result relabelled as policy outcome")
    if errors:
        raise ValueError("; ".join(dict.fromkeys(errors)))
    suites: dict[str, list[dict[str, Any]]] = defaultdict(list)
    tasks: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for cell in cells:
        suites[cell["suite"]].append(cell)
        tasks[(cell["suite"], int(cell["task_id"]))].append(cell)
    representatives = []
    for suite in ("libero_spatial", "libero_object", "libero_goal"):
        suite_cells = suites[suite]
        for outcome in ("success", "timeout"):
            matches = [cell for cell in suite_cells if cell["outcome"] == outcome]
            if matches:
                representatives.append(representative(matches[0]))
    return {
        "schema_version": REPORT_VERSION,
        "pass": True,
        "source": {
            "execution_manifest_sha256": source_sha256,
            "policy_id": index["policy_id"],
            "infrastructure_attempts_excluded": index["infrastructure_attempts"],
        },
        "overall": outcome_summary(cells),
        "suites": {suite: outcome_summary(suites[suite]) for suite in ("libero_spatial", "libero_object", "libero_goal")},
        "tasks": [
            {"suite": suite, "task_id": task_id, **outcome_summary(tasks[(suite, task_id)])}
            for suite, task_id in sorted(tasks)
        ],
        "representative_outcomes": representatives,
        "traceability": {
            "cells_with_artifact_ref": sum(bool(cell.get("artifact_ref")) for cell in cells),
            "cells_with_manifest_hash": sum(bool(cell.get("manifest_sha256")) for cell in cells),
            "first_valid_attempt_rule": True,
        },
        "claim_boundary": "OpenVLA-only LIBERO simulation baseline; no pi0.5 ranking, causal root-cause claim, or real telemetry.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path(__file__).resolve().parent / "verify/canonical/manifest.json")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    index = json.loads(args.input.read_text(encoding="utf-8"))
    try:
        report = build_report(index, canonical_text_hash(args.input))
    except ValueError as exc:
        parser.error(str(exc))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"pass": report["pass"], "overall": report["overall"], "suites": report["suites"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
