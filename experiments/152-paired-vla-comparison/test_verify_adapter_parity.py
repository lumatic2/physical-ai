#!/usr/bin/env python3
"""Adversarial tests for the shared policy adapter contract."""

from __future__ import annotations

import copy
import unittest

from verify_adapter_parity import DEFAULT_CONTRACT
from verify_adapter_parity import GEN1_DIR
from verify_adapter_parity import AdapterParityError
from verify_adapter_parity import load_json
from verify_adapter_parity import validate_adapter_contract


class SharedPolicyAdapterParityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = load_json(DEFAULT_CONTRACT)
        cls.registry = load_json(GEN1_DIR / "policy-registry.json")
        cls.denominator = load_json(GEN1_DIR / "run-denominator.json")

    def validate(self, contract=None, registry=None, denominator=None):
        return validate_adapter_contract(
            contract or self.contract,
            registry or self.registry,
            denominator or self.denominator,
        )

    def test_exact_pair_denominator_and_explicit_policy_differences_pass(self) -> None:
        report = self.validate()
        self.assertEqual(report["denominator"]["paired_keys"], 60)
        self.assertEqual(report["denominator"]["runs"], 120)
        self.assertEqual(len(report["adapters"]), 2)
        self.assertNotEqual(report["adapters"][0]["model_inputs"], report["adapters"][1]["model_inputs"])

    def test_hidden_transform_is_rejected(self) -> None:
        contract = copy.deepcopy(self.contract)
        contract["policies"]["pi05-libero"]["input_transforms"].append("main_camera:secret_crop")
        with self.assertRaisesRegex(AdapterParityError, "hidden input transform"):
            self.validate(contract=contract)

    def test_sign_or_scale_drift_is_rejected(self) -> None:
        contract = copy.deepcopy(self.contract)
        contract["policies"]["openvla-libero"]["controller_transforms"] = ["gripper:invert_for_LIBERO"]
        with self.assertRaisesRegex(AdapterParityError, "sign/scale"):
            self.validate(contract=contract)

    def test_wrist_input_relabel_is_rejected(self) -> None:
        registry = copy.deepcopy(self.registry)
        openvla = next(policy for policy in registry["policies"] if policy["policy_id"] == "openvla-libero")
        openvla["inputs"]["wrist_camera"]["model_input"] = True
        with self.assertRaisesRegex(AdapterParityError, "model input relabel|observer-only relabel"):
            self.validate(registry=registry)

    def test_timing_field_omission_is_rejected(self) -> None:
        contract = copy.deepcopy(self.contract)
        contract["common_result"]["timing_fields"].pop()
        with self.assertRaisesRegex(AdapterParityError, "timing fields incomplete"):
            self.validate(contract=contract)

    def test_unpaired_cell_is_rejected(self) -> None:
        denominator = copy.deepcopy(self.denominator)
        denominator["runs"] = [
            run
            for run in denominator["runs"]
            if not (
                run["policy"]["policy_id"] == "pi05-libero"
                and run["suite"] == "libero_spatial"
                and run["task_key"] == "libero_spatial/task-00"
                and run["state_index"] == 0
            )
        ]
        with self.assertRaisesRegex(AdapterParityError, "unpaired denominator"):
            self.validate(denominator=denominator)


if __name__ == "__main__":
    unittest.main()
