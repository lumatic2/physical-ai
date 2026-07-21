#!/usr/bin/env python3
"""Adversarial probes for GEN4 failure coverage and claim boundaries."""

from __future__ import annotations

import copy
import unittest

from classify_patterns import OUTPUT as PATTERN_INDEX
from coverage_gate import CoverageError, build_report, load_json, validate_report, validate_supported_claim
from extract_features import OUTPUT as FEATURE_INDEX
from reviewer_calibration import REPORT_PATH as REVIEWER_REPORT


class CoverageGateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.features = load_json(FEATURE_INDEX)
        cls.patterns = load_json(PATTERN_INDEX)
        cls.reviewer = load_json(REVIEWER_REPORT)
        cls.report = build_report(cls.features, cls.patterns, cls.reviewer)

    def test_actual_report_accounts_for_all_non_success(self) -> None:
        self.assertEqual(self.report["denominator"], {"non_success": 27, "indexed": 27, "omitted": 0})
        self.assertEqual(self.report["coverage"]["unknown"], 21)

    def test_denominator_omission_is_rejected(self) -> None:
        broken = copy.deepcopy(self.report)
        broken["denominator"]["indexed"] = 26
        broken["denominator"]["omitted"] = 1
        with self.assertRaisesRegex(CoverageError, "denominator omission"):
            validate_report(broken, self.features, self.patterns, self.reviewer)

    def test_hidden_unknown_is_rejected(self) -> None:
        broken = copy.deepcopy(self.report)
        broken["coverage"]["unknown"] = 0
        broken["coverage"]["unknown_rate"] = 0.0
        with self.assertRaisesRegex(CoverageError, "unknown or evidence"):
            validate_report(broken, self.features, self.patterns, self.reviewer)

    def test_root_cause_relabel_is_rejected(self) -> None:
        with self.assertRaisesRegex(CoverageError, "root cause"):
            validate_supported_claim("The root cause was a planning failure.")

    def test_independent_human_and_real_robot_claims_are_rejected(self) -> None:
        for text in ("Independent human reviewers confirmed this.", "This works on a real robot."):
            with self.subTest(text=text), self.assertRaises(CoverageError):
                validate_supported_claim(text)


if __name__ == "__main__":
    unittest.main()
