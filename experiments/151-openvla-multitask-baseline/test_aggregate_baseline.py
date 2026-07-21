#!/usr/bin/env python3
"""Aggregate recomputation and adversarial denominator tests."""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from aggregate_baseline import build_report


BASE = Path(__file__).resolve().parent


class BaselineAggregateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.index = json.loads((BASE / "verify/canonical/manifest.json").read_text(encoding="utf-8"))

    def test_canonical_aggregate_recomputes_all_cells(self) -> None:
        report = build_report(self.index, "a" * 64)
        self.assertEqual(report["overall"]["denominator"], 60)
        self.assertEqual(report["overall"]["success"], 35)
        self.assertEqual(report["overall"]["timeout"], 25)
        self.assertEqual(report["traceability"]["cells_with_artifact_ref"], 60)
        self.assertEqual(len(report["tasks"]), 12)
        self.assertEqual(len(report["representative_outcomes"]), 6)

    def test_omitted_timeout_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.index)
        timeout_index = next(index for index, cell in enumerate(mutated["cells"]) if cell["outcome"] == "timeout")
        mutated["cells"].pop(timeout_index)
        with self.assertRaisesRegex(ValueError, "missing execution cell"):
            build_report(mutated, "a" * 64)

    def test_retry_success_cannot_overwrite_or_duplicate_a_run_key(self) -> None:
        mutated = copy.deepcopy(self.index)
        timeout = next(cell for cell in mutated["cells"] if cell["outcome"] == "timeout")
        retry = copy.deepcopy(timeout)
        retry["outcome"] = "success"
        mutated["cells"].append(retry)
        with self.assertRaisesRegex(ValueError, "duplicate execution cell"):
            build_report(mutated, "a" * 64)

    def test_infrastructure_error_cannot_be_policy_failure(self) -> None:
        mutated = copy.deepcopy(self.index)
        mutated["cells"][0]["outcome"] = "error"
        with self.assertRaisesRegex(ValueError, "invalid policy outcome"):
            build_report(mutated, "a" * 64)


if __name__ == "__main__":
    unittest.main()
