#!/usr/bin/env python3
"""Adversarial tests for GEN3 fairness disclosures and claims."""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from fairness_gate import (
    ADAPTER_REPORT,
    CLAIM_CONTRACT,
    OPENVLA_MANIFEST,
    PAIRED_REPORT,
    PI05_MANIFEST,
    REGISTRY,
    FairnessError,
    build_report,
    load_json,
    set_path,
    validate_report,
)


class FairnessGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = load_json(CLAIM_CONTRACT)
        cls.report = build_report(
            load_json(REGISTRY),
            load_json(ADAPTER_REPORT),
            load_json(OPENVLA_MANIFEST),
            load_json(PI05_MANIFEST),
            load_json(PAIRED_REPORT),
            cls.contract,
        )
        cls.fixtures = json.loads(
            (Path(__file__).parent / "fixtures" / "invalid-fairness-claims.json").read_text(encoding="utf-8")
        )["cases"]

    def test_actual_fairness_report_passes(self) -> None:
        self.assertIsNone(validate_report(self.report))
        self.assertEqual(self.report["denominator"]["included_pairs"], 60)
        self.assertEqual(self.report["policies"]["openvla-libero"]["attempts"]["total"], 61)
        self.assertEqual(self.report["policies"]["pi05-libero"]["attempts"]["total"], 62)

    def test_invalid_claim_and_state_fixtures_are_rejected(self) -> None:
        for fixture in self.fixtures:
            with self.subTest(fixture=fixture["id"]):
                mutation = copy.deepcopy(self.report)
                if fixture["kind"] == "claim":
                    mutation["allowed_claims"].append(
                        {"id": fixture["id"], "text": fixture["value"], "evidence": "fixture"}
                    )
                else:
                    set_path(mutation, fixture["path"], fixture["value"])
                with self.assertRaisesRegex(FairnessError, fixture["expected_error"]):
                    validate_report(mutation)

    def test_checkpoint_and_input_topology_are_not_equalized(self) -> None:
        open_policy = self.report["policies"]["openvla-libero"]
        pi_policy = self.report["policies"]["pi05-libero"]
        self.assertEqual(open_policy["checkpoint_topology"], "suite-specific")
        self.assertEqual(pi_policy["checkpoint_topology"], "single-shared-checkpoint")
        self.assertNotEqual(open_policy["model_inputs"], pi_policy["model_inputs"])
        self.assertNotEqual(open_policy["executed_chunk_shape"], pi_policy["executed_chunk_shape"])

    def test_missing_disclosure_and_claim_evidence_are_rejected(self) -> None:
        mutation = copy.deepcopy(self.report)
        mutation["disclosures"].pop()
        with self.assertRaisesRegex(FairnessError, "disclosure"):
            validate_report(mutation)
        mutation = copy.deepcopy(self.report)
        mutation["allowed_claims"][0]["evidence"] = ""
        with self.assertRaisesRegex(FairnessError, "without evidence"):
            validate_report(mutation)


if __name__ == "__main__":
    unittest.main()
