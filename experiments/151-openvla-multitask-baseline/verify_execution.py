#!/usr/bin/env python3
"""Recompute all 60 sealed OpenVLA episodes from the append-only ledger."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from episode_export import dataset_tree_hash, sha256_file
from run_baseline import load_runner_contract
from run_ledger import RunLedger


REPORT_VERSION = "physical-ai-gen2-execution-manifest-v1"
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def tree_size(root: Path) -> tuple[int, int]:
    files = [path for path in root.rglob("*") if path.is_file()]
    return sum(path.stat().st_size for path in files), len(files)


def validate_index(index: dict[str, Any], expected_run_keys: list[str]) -> list[str]:
    errors: list[str] = []
    cells = index.get("cells", [])
    observed = [cell.get("run_key") for cell in cells]
    if len(cells) != len(expected_run_keys):
        errors.append("missing execution cell")
    if len(observed) != len(set(observed)):
        errors.append("duplicate execution cell")
    if set(observed) != set(expected_run_keys):
        errors.append("execution denominator mismatch")
    for cell in cells:
        if not HEX64.fullmatch(str(cell.get("manifest_sha256", ""))):
            errors.append(f"corrupt episode hash: {cell.get('run_key')}")
        if cell.get("outcome") not in {"success", "timeout"}:
            errors.append(f"invalid policy outcome: {cell.get('run_key')}")
        if not isinstance(cell.get("frames"), int) or cell["frames"] < 1:
            errors.append(f"invalid frame count: {cell.get('run_key')}")
    return list(dict.fromkeys(errors))


def build_execution_index(artifact_root: Path, ledger_path: Path, *, assert_clean_processes: bool) -> dict[str, Any]:
    contract = load_runner_contract()
    run_keys = [cell["run_key"] for cell in contract["cells"]]
    cells_by_key = {cell["run_key"]: cell for cell in contract["cells"]}
    ledger = RunLedger(ledger_path, run_keys)
    state = ledger.state()
    errors: list[str] = []
    entries = []
    canonical_bytes = 0
    canonical_files = 0
    for run_key in run_keys:
        attempt_id = state.completed.get(run_key)
        if not attempt_id:
            errors.append(f"missing terminal: {run_key}")
            continue
        terminal = state.attempts[attempt_id]
        artifact = terminal.get("artifact", {})
        attempt_root = artifact_root / str(artifact.get("ref", ""))
        manifest_path = attempt_root / "episode-manifest.json"
        if not manifest_path.is_file():
            errors.append(f"missing sealed manifest: {run_key}")
            continue
        manifest_sha = sha256_file(manifest_path)
        if manifest_sha != artifact.get("sha256"):
            errors.append(f"ledger manifest hash mismatch: {run_key}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("status") != "sealed" or manifest.get("run_key") != run_key:
            errors.append(f"sealed manifest identity mismatch: {run_key}")
        evidence = manifest.get("evidence", {})
        dataset_root = attempt_root / "dataset"
        observed_tree_hash, observed_dataset_files = dataset_tree_hash(dataset_root)
        if observed_tree_hash != evidence.get("dataset_tree_sha256"):
            errors.append(f"dataset tree hash mismatch: {run_key}")
        if observed_dataset_files != evidence.get("dataset_file_count"):
            errors.append(f"dataset file count mismatch: {run_key}")
        sidecars = sorted((dataset_root / "meta/lab_provenance").glob("episode_*.json"))
        event_files = sorted((attempt_root / "events").glob("episode_*.json"))
        if len(sidecars) != 1 or len(event_files) != 1:
            errors.append(f"episode evidence file count mismatch: {run_key}")
            continue
        if sha256_file(sidecars[0]) != evidence.get("sidecar_sha256"):
            errors.append(f"sidecar hash mismatch: {run_key}")
        if sha256_file(event_files[0]) != evidence.get("events_sha256"):
            errors.append(f"event hash mismatch: {run_key}")
        size_bytes, file_count = tree_size(attempt_root)
        canonical_bytes += size_bytes
        canonical_files += file_count
        cell = cells_by_key[run_key]
        entries.append(
            {
                "run_key": run_key,
                "suite": cell["suite"],
                "task_id": cell["task_id"],
                "state_index": cell["state_index"],
                "outcome": manifest.get("outcome", {}).get("status"),
                "frames": manifest.get("outcome", {}).get("frames"),
                "wall_seconds": manifest.get("timing", {}).get("wall_seconds"),
                "attempt_index": terminal.get("attempt_index"),
                "artifact_ref": artifact.get("ref"),
                "manifest_sha256": manifest_sha,
                "dataset_tree_sha256": evidence.get("dataset_tree_sha256"),
                "sidecar_sha256": evidence.get("sidecar_sha256"),
                "events_sha256": evidence.get("events_sha256"),
            }
        )
    process_cleanup = True
    if assert_clean_processes:
        probe = subprocess.run(
            ["bash", "-lc", "pgrep -f '[s]erver.py|[c]lient.py'"], capture_output=True, text=True, check=False
        )
        process_cleanup = probe.returncode != 0
        if not process_cleanup:
            errors.append("OpenVLA server/client process remains")
    suite_outcomes: dict[str, Counter[str]] = defaultdict(Counter)
    for entry in entries:
        suite_outcomes[entry["suite"]][entry["outcome"]] += 1
    index = {
        "schema_version": REPORT_VERSION,
        "pass": False,
        "policy_id": "openvla-libero",
        "planned_cells": len(run_keys),
        "terminal_cells": len(entries),
        "pending_cells": len(run_keys) - len(entries),
        "infrastructure_attempts": sum(len(items) for items in state.infrastructure_errors.values()),
        "ledger": {
            "event_count": len(ledger_path.read_text(encoding="utf-8").splitlines()),
            "sha256": sha256_file(ledger_path),
        },
        "process_cleanup_pass": process_cleanup,
        "canonical_artifacts": {"bytes": canonical_bytes, "files": canonical_files},
        "suite_outcomes": {suite: dict(counts) for suite, counts in suite_outcomes.items()},
        "cells": entries,
        "errors": [],
        "claim_boundary": "60 recorded OpenVLA rollouts in LIBERO simulation; no pi0.5 comparison or real telemetry.",
    }
    errors.extend(validate_index(index, run_keys))
    index["errors"] = list(dict.fromkeys(errors))
    index["pass"] = not index["errors"]
    return index


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--assert-clean-processes", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--ledger-snapshot", type=Path)
    args = parser.parse_args()
    report = build_execution_index(args.artifact_root, args.ledger, assert_clean_processes=args.assert_clean_processes)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.ledger_snapshot:
        args.ledger_snapshot.parent.mkdir(parents=True, exist_ok=True)
        args.ledger_snapshot.write_bytes(args.ledger.read_bytes())
    print(
        json.dumps(
            {key: report[key] for key in ("pass", "planned_cells", "terminal_cells", "pending_cells", "infrastructure_attempts", "process_cleanup_pass", "suite_outcomes", "errors")},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
