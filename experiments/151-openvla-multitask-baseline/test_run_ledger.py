#!/usr/bin/env python3
"""Fault-injection tests for append-only GEN2 execution state."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator
from run_baseline import load_runner_contract
from run_ledger import EVENT_VERSION, LedgerContractError, RunLedger

SEALED_SHA = "a" * 64


class RunLedgerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.run_keys = [cell["run_key"] for cell in load_runner_contract()["cells"][:3]]
        self.path = Path(self.temp.name) / "run-ledger.jsonl"
        self.ledger = RunLedger(self.path, self.run_keys)
        self.ledger.initialize()

    def test_forced_interruption_resume_skips_completed_and_retries_partial(self) -> None:
        partial = self.ledger.begin_attempt(self.run_keys[0])
        completed = self.ledger.begin_attempt(self.run_keys[1])
        self.ledger.record_policy_terminal(
            self.run_keys[1], completed["attempt_id"], "success", "episodes/b", SEALED_SHA
        )
        summary = self.ledger.resume_summary()
        self.assertEqual(summary["completed_skipped"], 1)
        self.assertEqual(summary["active_partial"], [self.run_keys[0]])
        self.assertEqual(summary["pending"], [self.run_keys[0], self.run_keys[2]])
        retry = self.ledger.begin_attempt(self.run_keys[0], recover_active=True)
        self.assertEqual(retry["retry_of"], partial["attempt_id"])
        self.assertEqual(retry["attempt_index"], 1)
        schema = json.loads(
            (Path(__file__).resolve().parent / "schemas/run-ledger-event-v1.json").read_text(encoding="utf-8")
        )
        validator = Draft202012Validator(schema)
        for line in self.path.read_text(encoding="utf-8").splitlines():
            self.assertEqual(list(validator.iter_errors(json.loads(line))), [])

    def test_duplicate_completion_is_rejected(self) -> None:
        attempt = self.ledger.begin_attempt(self.run_keys[0])
        self.ledger.record_policy_terminal(self.run_keys[0], attempt["attempt_id"], "timeout", "episodes/a", SEALED_SHA)
        with self.assertRaisesRegex(LedgerContractError, "duplicate or non-active"):
            self.ledger.record_policy_terminal(
                self.run_keys[0], attempt["attempt_id"], "timeout", "episodes/a", SEALED_SHA
            )

    def test_partial_artifact_promotion_is_rejected_on_replay(self) -> None:
        attempt = self.ledger.begin_attempt(self.run_keys[0])
        invalid = {
            "schema_version": EVENT_VERSION,
            "event": "attempt_terminal",
            "recorded_at": "2026-07-21T00:00:00Z",
            "run_key": self.run_keys[0],
            "attempt_id": attempt["attempt_id"],
            "result_class": "policy",
            "result_status": "success",
            "artifact": {"status": "partial", "ref": "tmp/a", "sha256": SEALED_SHA},
        }
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(invalid) + "\n")
        with self.assertRaisesRegex(LedgerContractError, "sealed artifact"):
            self.ledger.state()

    def test_hidden_retry_after_valid_policy_result_is_rejected(self) -> None:
        attempt = self.ledger.begin_attempt(self.run_keys[0])
        self.ledger.record_policy_terminal(self.run_keys[0], attempt["attempt_id"], "success", "episodes/a", SEALED_SHA)
        with self.assertRaisesRegex(LedgerContractError, "hidden retry"):
            self.ledger.begin_attempt(self.run_keys[0])

    def test_infrastructure_error_remains_retryable_and_separate(self) -> None:
        attempt = self.ledger.begin_attempt(self.run_keys[0])
        self.ledger.record_infrastructure_error(self.run_keys[0], attempt["attempt_id"], "errors/attempt-0.json")
        retry = self.ledger.begin_attempt(self.run_keys[0])
        self.assertEqual(retry["retry_of"], attempt["attempt_id"])
        self.assertEqual(self.ledger.resume_summary()["infrastructure_error_attempts"], 1)

    def test_policy_id_can_be_explicitly_reused_by_gen3(self) -> None:
        path = Path(self.temp.name) / "pi05-ledger.jsonl"
        ledger = RunLedger(path, self.run_keys, policy_id="pi05-libero")
        ledger.initialize()
        first = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
        self.assertEqual(first["contract"]["policy_id"], "pi05-libero")
        schema = json.loads(
            (Path(__file__).resolve().parent / "schemas/run-ledger-event-v1.json").read_text(encoding="utf-8")
        )
        self.assertEqual(list(Draft202012Validator(schema).iter_errors(first)), [])
        with self.assertRaisesRegex(LedgerContractError, "policy mismatch"):
            RunLedger(path, self.run_keys).state()


if __name__ == "__main__":
    unittest.main()
