#!/usr/bin/env python3
"""Contract tests for the resumable 60-cell π0.5 runner."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from execute_pi05 import POLICY_ID, client_command, load_pi05_contract
from run_ledger import RunLedger


class ExecutePi05Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = load_pi05_contract()

    def test_contract_is_exactly_sixty_ordered_pi05_cells(self) -> None:
        cells = self.contract["cells"]
        self.assertEqual(len(cells), 60)
        self.assertEqual(len({cell["run_key"] for cell in cells}), 60)
        self.assertEqual(
            (cells[0]["suite"], cells[0]["task_id"], cells[0]["state_index"]),
            ("libero_spatial", 0, 0),
        )
        self.assertEqual(
            (cells[-1]["suite"], cells[-1]["task_id"], cells[-1]["state_index"]),
            ("libero_goal", 9, 4),
        )
        self.assertTrue(all(":pi05-libero:" in cell["run_key"] for cell in cells))

    def test_client_command_selects_one_exact_cell_and_records_evidence(self) -> None:
        cell = self.contract["cells"][0]
        command = client_command(cell, self.contract, Path("attempt"), "python", 8010)
        self.assertEqual(command[command.index("--suite") + 1], "libero_spatial")
        self.assertEqual(command[command.index("--task-id") + 1], "0")
        self.assertEqual(command[command.index("--state-index") + 1], "0")
        self.assertEqual(command[command.index("--record-root") + 1], str(Path("attempt") / "dataset"))

    def test_pi05_ledger_keeps_infrastructure_attempt_and_explicit_retry(self) -> None:
        run_keys = [cell["run_key"] for cell in self.contract["cells"][:2]]
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = RunLedger(Path(temp_dir) / "ledger.jsonl", run_keys, policy_id=POLICY_ID)
            ledger.initialize()
            failed = ledger.begin_attempt(run_keys[0])
            ledger.record_infrastructure_error(run_keys[0], failed["attempt_id"], "errors/attempt-0.json")
            retry = ledger.begin_attempt(run_keys[0])
            self.assertEqual(retry["retry_of"], failed["attempt_id"])
            self.assertEqual(retry["attempt_index"], 1)
            self.assertEqual(ledger.resume_summary()["infrastructure_error_attempts"], 1)


if __name__ == "__main__":
    unittest.main()
