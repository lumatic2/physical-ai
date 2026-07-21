#!/usr/bin/env python3
"""Structural and negative-fixture tests for GEN1 initial states."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from verify_initial_states import apply_mutation, validate_contract
from verify_task_slice import load_json


BASE = Path(__file__).resolve().parent


class InitialStateContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = load_json(BASE / "benchmark-manifest.json")
        cls.contract = load_json(BASE / "initial-states.json")
        cls.mutations = json.loads(
            (BASE / "fixtures" / "invalid-initial-state-mutations.json").read_text(encoding="utf-8")
        )

    def test_contract_is_structurally_valid(self) -> None:
        self.assertEqual(validate_contract(self.contract, self.manifest), [])

    def test_order_seed_and_hash_drift_fail(self) -> None:
        for mutation in self.mutations:
            with self.subTest(mutation=mutation["id"]):
                errors = validate_contract(apply_mutation(self.contract, mutation), self.manifest)
                self.assertTrue(
                    any(mutation["expected_error"] in error for error in errors),
                    f"expected {mutation['expected_error']!r} in {errors}",
                )


if __name__ == "__main__":
    unittest.main()
