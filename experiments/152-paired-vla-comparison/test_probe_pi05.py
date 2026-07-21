#!/usr/bin/env python3
"""Contract and failure probes for the GEN3 π0.5 compatibility probe."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
from probe_pi05 import GEN1_DIR
from probe_pi05 import ProbeContractError
from probe_pi05 import input_digest
from probe_pi05 import load_json
from probe_pi05 import validate_action_chunk
from probe_pi05 import validate_checkpoint_materialization
from probe_pi05 import validate_request
from probe_pi05 import validate_runtime_lock


class Pi05CompatibilityProbeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.state = np.zeros(8, dtype=np.float32)
        self.main = np.zeros((224, 224, 3), dtype=np.uint8)
        self.wrist = np.ones((224, 224, 3), dtype=np.uint8)
        self.temp = tempfile.TemporaryDirectory()
        self.norm_stats = Path(self.temp.name) / "norm_stats.json"
        self.norm_stats.write_text("{}", encoding="utf-8")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def request(self, **overrides):
        values = {
            "suite": "libero_spatial",
            "state": self.state,
            "main_image": self.main,
            "wrist_image": self.wrist,
            "prompt": "pick up the black bowl and place it on the plate",
            "norm_stats_path": self.norm_stats,
        }
        values.update(overrides)
        return validate_request(**values)

    def test_runtime_lock_matches_gen1_registry(self) -> None:
        here = Path(__file__).resolve().parent
        policy = validate_runtime_lock(
            load_json(here / "runtime-lock.json"), load_json(GEN1_DIR / "policy-registry.json")
        )
        self.assertEqual(policy["policy_id"], "pi05-libero")

    def test_request_and_action_contract_pass(self) -> None:
        self.assertIsNone(self.request())
        actions = validate_action_chunk(np.zeros((10, 7), dtype=np.float32))
        self.assertEqual(actions.shape, (10, 7))

    def test_wrong_suite_checkpoint_is_rejected(self) -> None:
        here = Path(__file__).resolve().parent
        lock = json.loads((here / "runtime-lock.json").read_text(encoding="utf-8"))
        lock["checkpoint"]["config"] = "pi0_libero"
        with self.assertRaisesRegex(ProbeContractError, "wrong suite checkpoint"):
            validate_runtime_lock(lock, load_json(GEN1_DIR / "policy-registry.json"))

    def test_missing_norm_stats_is_rejected(self) -> None:
        with self.assertRaisesRegex(ProbeContractError, "missing LIBERO norm stats"):
            self.request(norm_stats_path=Path(self.temp.name) / "missing.json")

    def test_action_dimension_and_nonfinite_values_are_rejected(self) -> None:
        with self.assertRaisesRegex(ProbeContractError, "10x7"):
            validate_action_chunk(np.zeros((10, 8), dtype=np.float32))
        actions = np.zeros((10, 7), dtype=np.float32)
        actions[0, 0] = np.nan
        with self.assertRaisesRegex(ProbeContractError, "non-finite"):
            validate_action_chunk(actions)

    def test_input_mapping_digest_is_deterministic_and_sensitive(self) -> None:
        element = {
            "observation/image": self.main,
            "observation/wrist_image": self.wrist,
            "observation/state": self.state,
            "prompt": "do something",
        }
        self.assertEqual(input_digest(element), input_digest(element))
        changed = dict(element)
        changed["observation/image"] = self.main.copy()
        changed["observation/image"][0, 0, 0] = 1
        self.assertNotEqual(input_digest(element), input_digest(changed))

    def test_checkpoint_materialization_drift_is_rejected(self) -> None:
        checkpoint = Path(self.temp.name) / "checkpoint"
        checkpoint.mkdir()
        (checkpoint / "one").write_bytes(b"abc")
        lock = {"checkpoint": {"object_count": 1, "total_bytes": 3}}
        self.assertEqual(validate_checkpoint_materialization(checkpoint, lock), {"object_count": 1, "total_bytes": 3})
        lock["checkpoint"]["total_bytes"] = 4
        with self.assertRaisesRegex(ProbeContractError, "byte count mismatch"):
            validate_checkpoint_materialization(checkpoint, lock)


if __name__ == "__main__":
    unittest.main()
