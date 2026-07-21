#!/usr/bin/env python3
"""Adversarial tests for deterministic observable pattern classification."""

from __future__ import annotations

import copy
import random
import unittest

from classify_patterns import (
    OUTPUT,
    RULES_PATH,
    ClassifierError,
    build_index,
    classify_feature,
    load_json,
    validate_index,
)
from extract_features import OUTPUT as FEATURE_INDEX
from verify_contract import SCHEMA_PATH


class DeterministicClassifierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.features = load_json(FEATURE_INDEX)
        cls.rules = load_json(RULES_PATH)
        cls.schema = load_json(SCHEMA_PATH)
        cls.index = load_json(OUTPUT)

    def test_actual_index_passes_and_preserves_all_twenty_seven(self) -> None:
        self.assertIsNone(validate_index(self.index, self.features, self.schema))
        self.assertEqual(sum(self.index["counts"].values()), 27)
        self.assertEqual(set(self.index["counts"]), {"no_progress", "unknown"})

    def test_input_and_rule_order_do_not_change_records(self) -> None:
        shuffled_features = copy.deepcopy(self.features)
        random.Random(7).shuffle(shuffled_features["features"])
        reversed_rules = copy.deepcopy(self.rules)
        reversed_rules["rules"].reverse()
        first = build_index(self.features, self.rules, self.schema)
        second = build_index(shuffled_features, reversed_rules, self.schema)
        self.assertEqual(first["records"], second["records"])
        self.assertEqual(first["records_sha256"], second["records_sha256"])

    def test_conflicting_supported_rules_become_sorted_multiple(self) -> None:
        feature = copy.deepcopy(self.features["features"][0])
        feature["eef_trajectory"]["final_window_displacement"] = 0.0
        feature["controller_events"]["rejected_count"] = 1
        feature["controller_events"]["rejected_event_ids"] = ["controller-fixture"]
        record = classify_feature(feature, self.rules, self.schema)
        self.assertEqual(record["pattern_id"], "multiple")
        self.assertEqual(record["components"], ["controller_rejected", "no_progress"])

    def test_unsupported_label_and_missing_pointer_are_rejected(self) -> None:
        mutation = copy.deepcopy(self.rules)
        mutation["rules"][0]["pattern_id"] = "perception_failure"
        with self.assertRaisesRegex(ClassifierError, "unsupported causal"):
            build_index(self.features, mutation, self.schema)
        feature = copy.deepcopy(self.features["features"][0])
        feature["eef_trajectory"]["final_window_displacement"] = 0.0
        feature["sources"].pop("trajectory")
        with self.assertRaisesRegex(ClassifierError, "missing pointer"):
            classify_feature(feature, self.rules, self.schema)

    def test_count_or_evidence_hash_drift_is_rejected(self) -> None:
        mutation = copy.deepcopy(self.index)
        mutation["counts"]["unknown"] -= 1
        with self.assertRaisesRegex(ClassifierError, "count drift"):
            validate_index(mutation, self.features, self.schema)
        mutation = copy.deepcopy(self.index)
        mutation["records_sha256"] = "f" * 64
        with self.assertRaisesRegex(ClassifierError, "record hash drift"):
            validate_index(mutation, self.features, self.schema)


if __name__ == "__main__":
    unittest.main()
