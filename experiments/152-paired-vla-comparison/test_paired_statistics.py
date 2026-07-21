#!/usr/bin/env python3
"""Mutation tests for recomputable paired policy statistics."""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator
from paired_statistics import (
    GEN1_DENOMINATOR,
    OPENVLA_MANIFEST,
    PI05_MANIFEST,
    PairingError,
    bootstrap_interval,
    build_report,
    load_json,
    validate_report,
)


class PairedStatisticsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.denominator = load_json(GEN1_DENOMINATOR)
        cls.openvla = load_json(OPENVLA_MANIFEST)
        cls.pi05 = load_json(PI05_MANIFEST)
        cls.report = build_report(cls.denominator, cls.openvla, cls.pi05)

    def test_actual_sixty_pair_report_is_recomputable_and_schema_valid(self) -> None:
        self.assertIsNone(validate_report(self.report))
        self.assertEqual(self.report["overall"]["openvla_successes"], 35)
        self.assertEqual(self.report["overall"]["pi05_successes"], 58)
        self.assertEqual(self.report["contingency"], {
            "both_success": 34,
            "pi05_only_success": 24,
            "openvla_only_success": 1,
            "both_non_success": 1,
        })
        schema = json.loads((Path(__file__).parent / "schemas" / "paired-report-v1.json").read_text(encoding="utf-8"))
        self.assertEqual(list(Draft202012Validator(schema).iter_errors(self.report)), [])

    def test_unpaired_cell_is_rejected_against_gen1(self) -> None:
        mutation = copy.deepcopy(self.pi05)
        mutation["cells"].pop()
        with self.assertRaisesRegex(PairingError, "missing canonical"):
            build_report(self.denominator, self.openvla, mutation)

    def test_suite_omission_is_rejected(self) -> None:
        mutation = copy.deepcopy(self.report)
        mutation["suites"] = [row for row in mutation["suites"] if row["suite"] != "libero_goal"]
        with self.assertRaisesRegex(PairingError, "suite omission"):
            validate_report(mutation)

    def test_zero_denominator_is_rejected(self) -> None:
        with self.assertRaisesRegex(PairingError, "zero denominator"):
            bootstrap_interval([])

    def test_rounded_only_metric_is_rejected(self) -> None:
        mutation = copy.deepcopy(self.report)
        del mutation["paired_difference"]["success_numerator"]
        del mutation["paired_difference"]["denominator"]
        with self.assertRaisesRegex(PairingError, "rounded-only"):
            validate_report(mutation)

    def test_bootstrap_interval_is_deterministic(self) -> None:
        differences = [1] * 24 + [-1] + [0] * 35
        first = bootstrap_interval(differences)
        second = bootstrap_interval(differences)
        self.assertEqual(first, second)
        self.assertLessEqual(first["lower"], 23 / 60)
        self.assertGreaterEqual(first["upper"], 23 / 60)


if __name__ == "__main__":
    unittest.main()
