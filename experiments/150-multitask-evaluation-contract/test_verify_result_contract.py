#!/usr/bin/env python3
"""Unit and negative-fixture tests for the GEN1 run/result contract."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from verify_result_contract import (
    RESULT_INDEX_VERSION,
    apply_mutation,
    canonical_hash,
    make_result,
    validate_denominator,
    validate_result_index,
)
from verify_task_slice import load_json, sha256_repo_text_file


BASE = Path(__file__).resolve().parent


class ResultContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = load_json(BASE / "benchmark-manifest.json")
        cls.states = load_json(BASE / "initial-states.json")
        cls.registry = load_json(BASE / "policy-registry.json")
        cls.denominator = load_json(BASE / "run-denominator.json")
        cls.schema = load_json(BASE / "schemas" / "multitask-run-v1.json")
        cls.specs = load_json(BASE / "fixtures" / "result-case-specs.json")
        cls.sources = {
            "benchmark_manifest": sha256_repo_text_file(BASE / "benchmark-manifest.json"),
            "initial_states": sha256_repo_text_file(BASE / "initial-states.json"),
            "policy_registry": sha256_repo_text_file(BASE / "policy-registry.json"),
        }
        results = [
            make_result(cls.denominator["runs"][case["denominator_index"]], case)
            for case in cls.specs["valid_cases"]
        ]
        cls.valid_index = {
            "schema_version": RESULT_INDEX_VERSION,
            "denominator_sha256": canonical_hash(cls.denominator),
            "coverage": "partial",
            "results": results,
        }

    def test_denominator_is_exactly_120_unique_runs(self) -> None:
        self.assertEqual(
            validate_denominator(
                self.denominator, self.manifest, self.states, self.registry, self.sources
            ),
            [],
        )
        self.assertEqual(len({run["run_key"] for run in self.denominator["runs"]}), 120)

    def test_terminal_statuses_round_trip_losslessly(self) -> None:
        Draft202012Validator.check_schema(self.schema)
        self.assertEqual(validate_result_index(self.valid_index, self.denominator, self.schema), [])
        self.assertEqual(json.loads(json.dumps(self.valid_index)), self.valid_index)

    def test_duplicate_missing_and_evidenceless_results_fail(self) -> None:
        for mutation in self.specs["invalid_mutations"]:
            with self.subTest(mutation=mutation["id"]):
                errors = validate_result_index(
                    apply_mutation(self.valid_index, mutation), self.denominator, self.schema
                )
                self.assertTrue(any(mutation["expected_error"] in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
