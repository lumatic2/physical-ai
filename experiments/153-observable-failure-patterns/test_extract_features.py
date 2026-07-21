#!/usr/bin/env python3
"""Mutation tests for derived failure trajectory/event features."""

from __future__ import annotations

import copy
import json
import math
import unittest
from pathlib import Path

from extract_features import OUTPUT, FeatureError, validate_feature_index


class FailureFeatureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = json.loads(OUTPUT.read_text(encoding="utf-8"))
        cls.fixtures = json.loads(
            (Path(__file__).parent / "fixtures" / "invalid-feature-mutations.json").read_text(encoding="utf-8")
        )["cases"]

    def test_actual_twenty_seven_feature_rows_pass(self) -> None:
        self.assertIsNone(validate_feature_index(self.report))
        self.assertEqual(self.report["denominator"]["by_policy"], {"openvla-libero": 25, "pi05-libero": 2})
        self.assertEqual(self.report["availability"]["object_relation"], 0)
        self.assertEqual(self.report["availability"]["goal_distance"], 0)

    def test_invalid_feature_mutations_are_rejected(self) -> None:
        for fixture in self.fixtures:
            with self.subTest(fixture=fixture["id"]):
                mutation = copy.deepcopy(self.report)
                row = mutation["features"][0]
                kind = fixture["mutation"]
                if kind == "drop-main-camera":
                    row["camera_evidence"] = [item for item in row["camera_evidence"] if item["role"] != "main"]
                elif kind == "drop-event-source":
                    row["sources"].pop("event")
                elif kind == "eef-unit-radian":
                    row["eef_trajectory"]["unit"] = "radian"
                elif kind == "nan-displacement":
                    row["eef_trajectory"]["net_displacement"] = math.nan
                elif kind == "change-after-hash":
                    first = next(iter(row["raw_integrity"]["after"]))
                    row["raw_integrity"]["after"][first] = "f" * 64
                elif kind == "drop-feature-row":
                    mutation["features"].pop()
                else:
                    self.fail(f"unknown fixture mutation: {kind}")
                with self.assertRaisesRegex(FeatureError, fixture["expected_error"]):
                    validate_feature_index(mutation)

    def test_feature_rows_do_not_contain_pattern_labels(self) -> None:
        self.assertTrue(all("pattern_id" not in row for row in self.report["features"]))


if __name__ == "__main__":
    unittest.main()
