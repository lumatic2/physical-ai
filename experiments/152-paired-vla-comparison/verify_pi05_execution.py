#!/usr/bin/env python3
"""Recompute every π0.5 sealed episode from the raw execution ledger."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
GEN2_DIR = REPO_ROOT / "experiments" / "151-openvla-multitask-baseline"
if str(GEN2_DIR) not in sys.path:
    sys.path.insert(0, str(GEN2_DIR))

from episode_export import (  # noqa: E402
    dataset_tree_hash,
    sha256_file,
)
from execute_pi05 import (  # noqa: E402
    POLICY_ID,
    load_pi05_contract,
)
from pi05_evidence import validate_pi05_bundle  # noqa: E402
from run_ledger import RunLedger  # noqa: E402

HEX32 = re.compile(r"^[0-9a-f]{32}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
REPORT_VERSION = "physical-ai-gen3-pi05-execution-index-v1"


class Pi05ExecutionVerificationError(ValueError):
    """Raised when tracked evidence cannot be recomputed from raw artifacts."""


def safe_child(root: Path, relative: str) -> Path:
    candidate = Path(relative)
    if candidate.is_absolute():
        raise Pi05ExecutionVerificationError("artifact ref must be relative")
    resolved_root = root.resolve()
    resolved = (root / candidate).resolve()
    if resolved_root not in resolved.parents:
        raise Pi05ExecutionVerificationError("artifact ref escapes root")
    return resolved


def validate_canonical_index(
    rows: list[dict[str, Any]], expected_run_keys: list[str], *, require_complete: bool
) -> None:
    errors = []
    run_keys = [row.get("run_key") for row in rows]
    if len(run_keys) != len(set(run_keys)):
        errors.append("duplicate canonical cell")
    if any(row.get("policy_id") != POLICY_ID for row in rows):
        errors.append("policy/source relabel")
    if any(not HEX32.fullmatch(str(row.get("attempt_id", ""))) for row in rows):
        errors.append("invalid attempt id")
    if any(not HEX64.fullmatch(str(row.get("manifest_sha256", ""))) for row in rows):
        errors.append("invalid manifest hash")
    if any(row.get("status") not in {"success", "timeout"} for row in rows):
        errors.append("invalid policy terminal")
    unexpected = sorted(set(run_keys).difference(expected_run_keys))
    if unexpected:
        errors.append("canonical cell outside denominator")
    if require_complete and set(run_keys) != set(expected_run_keys):
        errors.append(f"missing canonical cells: {len(set(expected_run_keys).difference(run_keys))}")
    if errors:
        raise Pi05ExecutionVerificationError("; ".join(errors))


def verify_execution(artifact_root: Path, ledger_path: Path, *, require_complete: bool) -> dict[str, Any]:
    contract = load_pi05_contract()
    cells = contract["cells"]
    by_key = {cell["run_key"]: cell for cell in cells}
    run_keys = [cell["run_key"] for cell in cells]
    ledger = RunLedger(ledger_path, run_keys, policy_id=POLICY_ID)
    state = ledger.state()
    rows = []
    for run_key in run_keys:
        attempt_id = state.completed.get(run_key)
        if attempt_id is None:
            continue
        attempt = state.attempts[attempt_id]
        artifact = attempt["artifact"]
        attempt_root = safe_child(artifact_root, artifact["ref"])
        manifest_path = attempt_root / "episode-manifest.json"
        if sha256_file(manifest_path) != artifact["sha256"]:
            raise Pi05ExecutionVerificationError(f"ledger/manifest hash mismatch: {run_key}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("run_key") != run_key or manifest.get("status") != "sealed":
            raise Pi05ExecutionVerificationError(f"sealed manifest identity mismatch: {run_key}")
        dataset_root = attempt_root / "dataset"
        sidecar_path = dataset_root / "meta" / "lab_provenance" / "episode_000000.json"
        events_path = attempt_root / "events" / "episode_000000.json"
        info_path = dataset_root / "meta" / "info.json"
        sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
        events = json.loads(events_path.read_text(encoding="utf-8"))
        info = json.loads(info_path.read_text(encoding="utf-8"))
        from pi05_evidence import load_episode_rows

        episode_rows = load_episode_rows(dataset_root)
        validation = validate_pi05_bundle(by_key[run_key], info, sidecar, episode_rows, events)
        if not validation["valid"]:
            raise Pi05ExecutionVerificationError(
                f"raw episode validation failed: {run_key}: {validation['errors']}"
            )
        tree_hash, file_count = dataset_tree_hash(dataset_root)
        evidence = manifest["evidence"]
        expected_evidence = {
            "dataset_tree_sha256": tree_hash,
            "dataset_file_count": file_count,
            "info_sha256": sha256_file(info_path),
            "sidecar_sha256": sha256_file(sidecar_path),
            "events_sha256": sha256_file(events_path),
            "causal_event_count": validation["causal_events"],
        }
        if any(evidence.get(key) != value for key, value in expected_evidence.items()):
            raise Pi05ExecutionVerificationError(f"manifest evidence drift: {run_key}")
        rows.append(
            {
                "run_key": run_key,
                "policy_id": POLICY_ID,
                "suite": by_key[run_key]["suite"],
                "task_id": by_key[run_key]["task_id"],
                "state_index": by_key[run_key]["state_index"],
                "attempt_id": attempt_id,
                "status": validation["result_status"],
                "frames": validation["frames"],
                "request_count": validation["request_count"],
                "artifact_ref": artifact["ref"],
                "manifest_sha256": artifact["sha256"],
            }
        )
    validate_canonical_index(rows, run_keys, require_complete=require_complete)
    return {
        "schema_version": REPORT_VERSION,
        "pass": True,
        "terminal": len(rows),
        "pending": len(run_keys) - len(rows),
        "outcomes": dict(Counter(row["status"] for row in rows)),
        "suites": dict(Counter(row["suite"] for row in rows)),
        "frames": sum(row["frames"] for row in rows),
        "requests": sum(row["request_count"] for row in rows),
        "attempts": sum(len(items) for items in state.run_attempts.values()),
        "infrastructure_error_attempts": sum(len(items) for items in state.infrastructure_errors.values()),
        "cells": rows,
        "claim_boundary": "Actual π0.5 rollout evidence in LIBERO simulation; no OpenVLA comparison or real telemetry.",
    }


def assert_clean_processes() -> None:
    result = subprocess.run(
        ["pgrep", "-af", "execute_pi05.py|serve_policy.py|pi05_client.py"],
        text=True,
        capture_output=True,
        check=False,
    )
    offenders = [line for line in result.stdout.splitlines() if "verify_pi05_execution.py" not in line]
    if offenders:
        raise Pi05ExecutionVerificationError("π0.5 execution processes remain: " + " | ".join(offenders))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=HERE / "verify" / "canonical" / "pi05-manifest.json")
    parser.add_argument(
        "--ledger-output", type=Path, default=HERE / "verify" / "canonical" / "pi05-run-ledger.jsonl"
    )
    parser.add_argument("--allow-partial", action="store_true")
    parser.add_argument("--assert-clean-processes", action="store_true")
    args = parser.parse_args()
    try:
        report = verify_execution(args.artifact_root, args.ledger, require_complete=not args.allow_partial)
        if args.assert_clean_processes:
            assert_clean_processes()
    except (Pi05ExecutionVerificationError, FileNotFoundError, KeyError, TypeError, ValueError) as exc:
        print(f"π0.5 execution gate: FAIL — {exc}")
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.ledger_output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(args.ledger, args.ledger_output)
    print(
        f"π0.5 execution gate: PASS (terminal={report['terminal']}, pending={report['pending']}, "
        f"infra_attempts={report['infrastructure_error_attempts']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
