#!/usr/bin/env python3
"""Pure command and identity tests for the suite-batched executor."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from execute_baseline import client_command, dataset_revision, server_command
from run_baseline import load_runner_contract


class ExecuteBaselineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = load_runner_contract()
        cls.cell = cls.contract["cells"][0]

    def test_server_uses_exact_suite_checkpoint_once(self) -> None:
        command = server_command(self.cell, "python", 8000)
        self.assertEqual(command[command.index("--ckpt") + 1], self.cell["checkpoint_repo"])
        self.assertEqual(command[command.index("--ckpt-revision") + 1], self.cell["checkpoint_revision"])

    def test_client_is_exactly_one_task_and_state_with_recording(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            command = client_command(self.cell, self.contract, Path(temp_dir), "python", 8000)
        self.assertEqual(command[command.index("--tasks") + 1], "1")
        self.assertEqual(command[command.index("--trials") + 1], "1")
        self.assertEqual(command[command.index("--task-offset") + 1], str(self.cell["task_id"]))
        self.assertEqual(command[command.index("--trial-offset") + 1], str(self.cell["state_index"]))
        self.assertNotIn("--direct-vla-event-dir", command)
        self.assertEqual(len(dataset_revision(self.cell["run_key"])), 64)


if __name__ == "__main__":
    unittest.main()
