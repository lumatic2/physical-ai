#!/usr/bin/env python3
"""Adversarial index tests for full π0.5 execution evidence."""

from __future__ import annotations

import copy
import unittest

from verify_pi05_execution import (
    Pi05ExecutionVerificationError,
    validate_canonical_index,
)


def row(run_key: str, *, policy_id: str = "pi05-libero", attempt_id: str = "a" * 32) -> dict:
    return {
        "run_key": run_key,
        "policy_id": policy_id,
        "attempt_id": attempt_id,
        "manifest_sha256": "b" * 64,
        "status": "success",
    }


class Pi05ExecutionIndexTest(unittest.TestCase):
    def setUp(self) -> None:
        self.keys = ["run-a", "run-b", "run-c"]
        self.rows = [row(key, attempt_id=f"{index + 1:032x}") for index, key in enumerate(self.keys)]

    def test_complete_unique_index_passes(self) -> None:
        self.assertIsNone(validate_canonical_index(self.rows, self.keys, require_complete=True))

    def test_missing_and_duplicate_cells_are_rejected(self) -> None:
        with self.assertRaisesRegex(Pi05ExecutionVerificationError, "missing canonical"):
            validate_canonical_index(self.rows[:-1], self.keys, require_complete=True)
        duplicate = self.rows + [copy.deepcopy(self.rows[0])]
        with self.assertRaisesRegex(Pi05ExecutionVerificationError, "duplicate canonical"):
            validate_canonical_index(duplicate, self.keys, require_complete=True)

    def test_policy_source_relabel_is_rejected(self) -> None:
        mutation = copy.deepcopy(self.rows)
        mutation[0]["policy_id"] = "openvla-libero"
        with self.assertRaisesRegex(Pi05ExecutionVerificationError, "policy/source relabel"):
            validate_canonical_index(mutation, self.keys, require_complete=True)

    def test_retry_overwrite_attempt_identity_is_rejected(self) -> None:
        mutation = copy.deepcopy(self.rows)
        mutation[1]["attempt_id"] = "not-an-attempt"
        with self.assertRaisesRegex(Pi05ExecutionVerificationError, "invalid attempt"):
            validate_canonical_index(mutation, self.keys, require_complete=True)


if __name__ == "__main__":
    unittest.main()
