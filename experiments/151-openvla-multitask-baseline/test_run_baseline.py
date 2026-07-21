#!/usr/bin/env python3
"""Contract and negative tests for the GEN2 manifest-driven runner."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from run_baseline import (
    DEFAULT_CONFIG,
    DEFAULT_REPO_ROOT,
    RunnerContractError,
    dry_run_report,
    load_runner_contract,
    select_cells,
)


class ManifestDrivenRunnerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = load_runner_contract()

    def test_dry_run_is_exactly_sixty_ordered_openvla_cells(self) -> None:
        cells = self.contract["cells"]
        report = dry_run_report(self.contract, cells, "python", 8000)
        self.assertEqual(report["cell_count"], 60)
        self.assertEqual(report["suite_counts"], {"libero_spatial": 20, "libero_object": 20, "libero_goal": 20})
        self.assertEqual(len({cell["run_key"] for cell in cells}), 60)
        self.assertEqual((cells[0]["suite"], cells[0]["task_id"], cells[0]["state_index"]), ("libero_spatial", 0, 0))
        self.assertEqual((cells[-1]["suite"], cells[-1]["task_id"], cells[-1]["state_index"]), ("libero_goal", 9, 4))
        self.assertTrue(all(cell["instruction"] for cell in cells))
        self.assertTrue(all(cell["command"][cell["command"].index("--tasks") + 1] == "1" for cell in report["cells"]))

    def test_manifest_outside_task_or_state_is_rejected(self) -> None:
        with self.assertRaisesRegex(RunnerContractError, "outside the frozen"):
            select_cells(self.contract["cells"], suite="libero_spatial", task_id=2, state_index=0)
        with self.assertRaisesRegex(RunnerContractError, "outside the frozen"):
            select_cells(self.contract["cells"], suite="libero_goal", task_id=9, state_index=5)

    def test_revision_mismatch_is_rejected_before_execution(self) -> None:
        config = json.loads(DEFAULT_CONFIG.read_text(encoding="utf-8"))
        config["sources"]["denominator"]["sha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "runner-config.json"
            path.write_text(json.dumps(config), encoding="utf-8")
            with self.assertRaisesRegex(RunnerContractError, "source revision mismatch: denominator"):
                load_runner_contract(path, DEFAULT_REPO_ROOT)

    def test_checkpoint_revision_mismatch_is_rejected(self) -> None:
        denominator = json.loads(
            (DEFAULT_REPO_ROOT / "experiments/150-multitask-evaluation-contract/run-denominator.json").read_text(
                encoding="utf-8"
            )
        )
        openvla = next(run for run in denominator["runs"] if run["policy"]["policy_id"] == "openvla-libero")
        openvla["policy"]["artifact_revision"] = "0" * 40
        with self.assertRaisesRegex(RunnerContractError, "checkpoint revision mismatch"):
            load_runner_contract(_documents_override={"denominator": denominator})


if __name__ == "__main__":
    unittest.main()
