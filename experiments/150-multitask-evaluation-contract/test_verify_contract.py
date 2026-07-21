#!/usr/bin/env python3
"""Unit and integrated negative-fixture tests for the GEN1 clean gate."""

from __future__ import annotations

import unittest
from pathlib import Path

from verify_contract import apply_mutation, integrated_gate, source_hashes
from verify_result_contract import validate_denominator
from verify_task_slice import load_json


BASE = Path(__file__).resolve().parent
REPO = BASE.parents[1]


class IntegratedContractGateTest(unittest.TestCase):
    def test_local_integrated_gate_passes(self) -> None:
        report = integrated_gate(BASE, REPO)
        self.assertTrue(report["pass"], report["errors"])
        self.assertEqual(report["planned_cell_count"], 120)

    def test_deleted_duplicate_and_revision_drift_fail(self) -> None:
        manifest = load_json(BASE / "benchmark-manifest.json")
        states = load_json(BASE / "initial-states.json")
        registry = load_json(BASE / "policy-registry.json")
        denominator = load_json(BASE / "run-denominator.json")
        for mutation in load_json(BASE / "fixtures" / "integrated-contract-mutations.json"):
            with self.subTest(mutation=mutation["id"]):
                errors = validate_denominator(
                    apply_mutation(denominator, mutation),
                    manifest,
                    states,
                    registry,
                    source_hashes(BASE),
                )
                self.assertTrue(any(mutation["expected_error"] in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
