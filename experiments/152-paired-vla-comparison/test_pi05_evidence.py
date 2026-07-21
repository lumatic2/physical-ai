#!/usr/bin/env python3
"""Mutation tests for π0.5 sidecar, chunk, and causal evidence."""

from __future__ import annotations

import copy
import json
import unittest

from pi05_evidence import (
    MAIN_CAMERA,
    PI05_REVISION,
    WRIST_CAMERA,
    build_pi05_stream,
    load_episode_rows,
    validate_pi05_bundle,
)


class Pi05EvidenceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from pathlib import Path

        base = (
            Path(__file__).resolve().parents[1]
            / "147-camera-action-episode-contract"
            / "verify"
            / "canonical"
            / "pass"
            / "dataset"
        )
        cls.info = json.loads((base / "meta" / "info.json").read_text(encoding="utf-8"))
        cls.rows = load_episode_rows(base)
        sidecar = json.loads(
            (base / "meta" / "lab_provenance" / "episode_000000.json").read_text(encoding="utf-8")
        )
        sidecar["producer"]["policy"] = {"name": "pi0.5-libero", "revision": PI05_REVISION}
        sidecar["camera_roles"][MAIN_CAMERA]["model_input"] = True
        sidecar["camera_roles"][WRIST_CAMERA]["model_input"] = True
        sidecar["policy_interface"] = {
            "config": "pi05_libero",
            "raw_chunk_shape": [10, 32],
            "exposed_chunk_shape": [10, 7],
            "executed_prefix_steps": 5,
            "gripper_transform": "none_after_checkpoint_denormalization",
        }
        for frame, action_event in enumerate(sidecar["action_events"]):
            chunk_index = frame % 5
            action_event.update(
                {
                    "request_id": f"request-{frame // 5:06d}",
                    "chunk_index": chunk_index,
                    "is_request_step": chunk_index == 0,
                    "predicted_chunk_length": 10,
                }
            )
            if chunk_index:
                action_event["request_latency_ms"] = 0.0
        cls.sidecar = sidecar
        cls.cell = {"environment_revision": sidecar["producer"]["environment"]["revision"]}

    def validate(self, sidecar=None):
        candidate = sidecar or self.sidecar
        stream = build_pi05_stream(candidate, self.rows)
        return validate_pi05_bundle(self.cell, self.info, candidate, self.rows, stream)

    def test_valid_chunked_pi05_evidence_passes(self) -> None:
        report = self.validate()
        self.assertTrue(report["valid"], report["errors"])
        self.assertEqual(report["causal_events"], len(self.rows) * 3 + 1)

    def test_policy_source_relabel_is_rejected(self) -> None:
        sidecar = copy.deepcopy(self.sidecar)
        sidecar["producer"]["policy"]["name"] = "openvla"
        report = self.validate(sidecar)
        self.assertIn("policy-source-relabel", report["errors"])

    def test_wrist_model_input_relabel_is_rejected(self) -> None:
        sidecar = copy.deepcopy(self.sidecar)
        sidecar["camera_roles"][WRIST_CAMERA]["model_input"] = False
        report = self.validate(sidecar)
        self.assertIn("wrist-camera-role-mismatch", report["errors"])

    def test_chunk_order_and_duplicated_latency_are_rejected(self) -> None:
        sidecar = copy.deepcopy(self.sidecar)
        sidecar["action_events"][1]["chunk_index"] = 0
        sidecar["action_events"][2]["request_latency_ms"] = 1.0
        report = self.validate(sidecar)
        self.assertIn("frame-1:chunk-order-drift", report["errors"])
        self.assertIn("frame-2:duplicated-request-latency", report["errors"])


if __name__ == "__main__":
    unittest.main()
