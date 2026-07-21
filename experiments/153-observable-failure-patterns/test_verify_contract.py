#!/usr/bin/env python3
"""Mutation tests for observable failure pattern contract."""

from __future__ import annotations

import copy
import unittest

from jsonschema import Draft202012Validator
from verify_contract import (
    CAUSAL_LANGUAGE,
    FIXTURES_PATH,
    SCHEMA_PATH,
    ContractError,
    base_record,
    load_json,
    validate_contract,
    validate_record,
)


class FailurePatternContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = load_json(SCHEMA_PATH)
        cls.fixtures = load_json(FIXTURES_PATH)
        cls.validator = Draft202012Validator(cls.schema)

    def test_canonical_contract_passes(self) -> None:
        report = validate_contract(self.schema, self.fixtures)
        self.assertTrue(report["pass"])
        self.assertEqual(len(report["labels"]), 8)
        self.assertEqual(report["attempt_labels"], ["infrastructure_error"])

    def test_unknown_multiple_and_infrastructure_conditionals_pass(self) -> None:
        for label in ("unknown", "multiple", "infrastructure_error"):
            with self.subTest(label=label):
                self.assertEqual(list(self.validator.iter_errors(base_record(label))), [])

    def test_causal_taxonomy_language_is_rejected(self) -> None:
        mutation = copy.deepcopy(self.schema)
        mutation["x-pattern-definitions"][0]["description"] = "The model did not understand the scene."
        with self.assertRaisesRegex(ContractError, "causal taxonomy"):
            validate_contract(mutation, self.fixtures)
        self.assertIsNotNone(CAUSAL_LANGUAGE.search("bad reasoning"))

    def test_reversed_frame_range_is_semantically_rejected_by_consumer(self) -> None:
        record = base_record()
        record["frame_range"] = {"start": 20, "end": 10}
        self.assertEqual(list(self.validator.iter_errors(record)), [])
        with self.assertRaisesRegex(ContractError, "start exceeds end"):
            validate_record(self.schema, record)


if __name__ == "__main__":
    unittest.main()
