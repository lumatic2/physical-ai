#!/usr/bin/env python3
"""Negative index fixtures for the 60-cell execution verifier."""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from run_baseline import load_runner_contract
from verify_execution import validate_index


BASE = Path(__file__).resolve().parent


class ExecutionIndexTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.index = json.loads((BASE / "verify/canonical/manifest.json").read_text(encoding="utf-8"))
        cls.run_keys = [cell["run_key"] for cell in load_runner_contract()["cells"]]

    def test_canonical_index_is_complete(self) -> None:
        self.assertEqual(validate_index(self.index, self.run_keys), [])

    def test_missing_and_duplicate_cells_are_rejected(self) -> None:
        missing = copy.deepcopy(self.index)
        missing["cells"].pop()
        self.assertIn("missing execution cell", validate_index(missing, self.run_keys))
        duplicate = copy.deepcopy(self.index)
        duplicate["cells"][-1] = copy.deepcopy(duplicate["cells"][0])
        self.assertIn("duplicate execution cell", validate_index(duplicate, self.run_keys))

    def test_corrupt_manifest_hash_is_rejected(self) -> None:
        corrupt = copy.deepcopy(self.index)
        corrupt["cells"][0]["manifest_sha256"] = "not-a-hash"
        self.assertTrue(any(error.startswith("corrupt episode hash") for error in validate_index(corrupt, self.run_keys)))


if __name__ == "__main__":
    unittest.main()
