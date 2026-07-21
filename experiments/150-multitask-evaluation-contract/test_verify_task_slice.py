#!/usr/bin/env python3
"""Unit and negative-fixture tests for the frozen GEN1 task slice."""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from verify_task_slice import load_json, validate_manifest


BASE = Path(__file__).resolve().parent


def apply_mutation(manifest: dict, mutation: dict) -> dict:
    mutated = copy.deepcopy(manifest)
    if mutation["operation"] == "replace":
        mutated["tasks"][mutation["task_index"]][mutation["field"]] = mutation["value"]
    elif mutation["operation"] == "copy-task":
        mutated["tasks"][mutation["task_index"]] = copy.deepcopy(
            mutated["tasks"][mutation["from_task_index"]]
        )
    else:
        raise AssertionError(f"unknown mutation operation: {mutation['operation']}")
    return mutated


class TaskSliceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = load_json(BASE / "benchmark-manifest.json")
        cls.catalog = load_json(BASE / "official-task-catalog.json")
        cls.mutations = json.loads((BASE / "fixtures" / "invalid-mutations.json").read_text(encoding="utf-8"))

    def test_frozen_manifest_is_structurally_valid(self) -> None:
        self.assertEqual(validate_manifest(self.manifest, self.catalog), [])

    def test_unknown_duplicate_and_suite_relabel_fail(self) -> None:
        for mutation in self.mutations:
            with self.subTest(mutation=mutation["id"]):
                errors = validate_manifest(apply_mutation(self.manifest, mutation), self.catalog)
                self.assertTrue(
                    any(mutation["expected_error"] in error for error in errors),
                    f"expected {mutation['expected_error']!r} in {errors}",
                )


if __name__ == "__main__":
    unittest.main()
