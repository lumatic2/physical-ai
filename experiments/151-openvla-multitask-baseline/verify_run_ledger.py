#!/usr/bin/env python3
"""Run a bounded interruption/resume proof and emit a path-free report."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from run_baseline import load_runner_contract
from run_ledger import EVENT_VERSION, LedgerContractError, RunLedger


def verify() -> dict:
    run_keys = [cell["run_key"] for cell in load_runner_contract()["cells"][:3]]
    rejected = []
    with tempfile.TemporaryDirectory() as temp_dir:
        ledger = RunLedger(Path(temp_dir) / "fault-injection.jsonl", run_keys)
        ledger.initialize()
        partial_attempt = ledger.begin_attempt(run_keys[0])
        complete = ledger.begin_attempt(run_keys[1])
        ledger.record_policy_terminal(run_keys[1], complete["attempt_id"], "success", "episodes/cell-1", "a" * 64)
        before = ledger.resume_summary()
        retry = ledger.begin_attempt(run_keys[0], recover_active=True)
        ledger.record_policy_terminal(run_keys[0], retry["attempt_id"], "timeout", "episodes/cell-0", "b" * 64)
        try:
            ledger.begin_attempt(run_keys[1])
        except LedgerContractError:
            rejected.append("hidden-retry-after-valid-result")
        try:
            ledger.record_policy_terminal(run_keys[0], retry["attempt_id"], "timeout", "episodes/cell-0", "b" * 64)
        except LedgerContractError:
            rejected.append("duplicate-completion")
        after = ledger.resume_summary()
        partial_artifact_attempt = ledger.begin_attempt(run_keys[2])
        invalid_partial = {
            "schema_version": EVENT_VERSION,
            "event": "attempt_terminal",
            "recorded_at": "2026-07-21T00:00:00Z",
            "run_key": run_keys[2],
            "attempt_id": partial_artifact_attempt["attempt_id"],
            "result_class": "policy",
            "result_status": "success",
            "artifact": {"status": "partial", "ref": "tmp/cell-2", "sha256": "c" * 64},
        }
        with ledger.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(invalid_partial) + "\n")
        try:
            ledger.state()
        except LedgerContractError:
            rejected.append("partial-artifact-promotion")
    return {
        "schema_version": "physical-ai-gen2-ledger-fault-injection-v1",
        "pass": (
            before["completed_skipped"] == 1
            and before["active_partial"] == [run_keys[0]]
            and retry["retry_of"] == partial_attempt["attempt_id"]
            and after["completed_skipped"] == 2
            and rejected
            == ["hidden-retry-after-valid-result", "duplicate-completion", "partial-artifact-promotion"]
        ),
        "fixture_cell_count": 3,
        "completed_skipped_before_resume": before["completed_skipped"],
        "partial_retried": retry["retry_of"] == partial_attempt["attempt_id"],
        "completed_after_resume": after["completed_skipped"],
        "remaining_after_resume": len(after["pending"]),
        "rejected": rejected,
        "claim_boundary": "This is a bounded ledger fault injection; it is not a policy rollout.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = verify()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
