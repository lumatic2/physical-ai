#!/usr/bin/env python3
"""Structural and negative-fixture tests for the GEN1 policy registry."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from verify_policy_registry import apply_mutation, validate_registry
from verify_task_slice import load_json


BASE = Path(__file__).resolve().parent
REPO = BASE.parents[1]


class PolicyRegistryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = load_json(BASE / "policy-registry.json")
        cls.manifest = load_json(BASE / "benchmark-manifest.json")
        cls.metadata = load_json(BASE / "pi05-checkpoint-metadata.json")
        cls.mutations = json.loads(
            (BASE / "fixtures" / "invalid-policy-mutations.json").read_text(encoding="utf-8")
        )

    def test_registry_expands_to_24_resolved_pairs(self) -> None:
        errors, matrix = validate_registry(self.registry, self.manifest, self.metadata, REPO)
        self.assertEqual(errors, [])
        self.assertEqual(len(matrix), 24)

    def test_action_camera_and_checkpoint_drift_fail(self) -> None:
        for mutation in self.mutations:
            with self.subTest(mutation=mutation["id"]):
                errors, _ = validate_registry(
                    apply_mutation(self.registry, mutation), self.manifest, self.metadata, REPO
                )
                self.assertTrue(any(mutation["expected_error"] in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
