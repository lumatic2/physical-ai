#!/usr/bin/env python3
"""Focused failure probes for GEN4 reviewer calibration."""

from __future__ import annotations

import copy
import unittest

from classify_patterns import OUTPUT as PATTERN_INDEX
from extract_features import OUTPUT as FEATURE_INDEX
from reviewer_calibration import (
    CLAIM_BOUNDARY,
    REVIEW_KIND,
    ReviewError,
    build_packet,
    build_report,
    load_json,
    validate_packet,
)


class ReviewerCalibrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.features = load_json(FEATURE_INDEX)
        cls.patterns = load_json(PATTERN_INDEX)
        cls.packet = build_packet(cls.features, cls.patterns)

    def valid_decisions(self) -> dict:
        return {
            "schema_version": "physical-ai-gen4-reviewer-decisions-v1",
            "decisions": [
                {
                    "sample_id": sample["sample_id"],
                    "reviewer_id": "fixture-reviewer",
                    "review_kind": REVIEW_KIND,
                    "reviewed_pattern_id": sample["pattern_id"],
                    "source_checks": {
                        "main_camera_observed": True,
                        "wrist_camera_observed": True,
                        "event_source_observed": True,
                    },
                    "reviewed_frame_indices": [
                        sample["frame_range"]["start"],
                        (sample["frame_range"]["start"] + sample["frame_range"]["end"]) // 2,
                        sample["frame_range"]["end"],
                    ],
                    "reviewer_note": "fixture evidence reviewed",
                    "disagreement": None,
                }
                for sample in self.packet["samples"]
            ],
            "claim_boundary": CLAIM_BOUNDARY,
        }

    def test_actual_packet_has_all_seven_observed_strata(self) -> None:
        self.assertEqual(self.packet["sample_count"], 7)
        self.assertIn("unknown", {row["pattern_id"] for row in self.packet["samples"]})
        self.assertTrue(all(row["predicate_check"]["matches_record"] for row in self.packet["samples"]))

    def test_success_only_sample_is_rejected(self) -> None:
        broken = copy.deepcopy(self.packet)
        broken["samples"][0]["outcome"] = "success"
        with self.assertRaisesRegex(ReviewError, "non-success"):
            validate_packet(broken, self.features, self.patterns)

    def test_unknown_exclusion_is_rejected(self) -> None:
        broken = copy.deepcopy(self.packet)
        broken["samples"] = [row for row in broken["samples"] if row["pattern_id"] != "unknown"]
        broken["sample_count"] = len(broken["samples"])
        with self.assertRaisesRegex(ReviewError, "unknown"):
            validate_packet(broken, self.features, self.patterns)

    def test_unrecorded_reviewer_override_is_rejected(self) -> None:
        decisions = self.valid_decisions()
        decisions["decisions"][0]["reviewed_pattern_id"] = "unknown"
        with self.assertRaisesRegex(ReviewError, "auditable disagreement"):
            build_report(self.packet, decisions)

    def test_source_check_omission_is_rejected(self) -> None:
        decisions = self.valid_decisions()
        decisions["decisions"][0]["source_checks"]["wrist_camera_observed"] = False
        with self.assertRaisesRegex(ReviewError, "source check incomplete"):
            build_report(self.packet, decisions)

    def test_valid_decisions_produce_complete_agreement_report(self) -> None:
        report = build_report(self.packet, self.valid_decisions())
        self.assertTrue(report["pass"])
        self.assertEqual(report["agreement"], {"agreed": 7, "disagreed": 0, "rate": 1.0})


if __name__ == "__main__":
    unittest.main()
