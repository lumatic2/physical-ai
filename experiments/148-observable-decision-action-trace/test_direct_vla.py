from __future__ import annotations

import copy
import hashlib
import unittest

import numpy as np

from direct_vla import build_direct_vla_stream, validate_direct_vla_trace


def action_hash(action):
    return hashlib.sha256(np.asarray(action, dtype="<f4").tobytes()).hexdigest()


class DirectVlaTests(unittest.TestCase):
    def setUp(self) -> None:
        actions = [[0.1, 0.2, 0.3, 0.0, 0.0, 0.0, -1.0], [0.2, 0.1, 0.0, 0.0, 0.0, 0.0, 1.0]]
        self.rows = [
            {"frame_index": index, "timestamp": index * 0.1, "episode_index": 0, "action": action}
            for index, action in enumerate(actions)
        ]
        self.sidecar = {
            "episode": {"revision": "777701b", "index": 0},
            "producer": {
                "environment": {"name": "libero", "revision": "8f1084e"},
                "policy": {"name": "openvla", "revision": "962318c"},
            },
            "camera_roles": {
                "observation.images.image": {"role": "main", "model_input": True},
                "observation.images.image2": {"role": "wrist", "model_input": False},
            },
            "action_events": [
                {
                    "frame_index": index,
                    "raw_policy_action": action[:-1] + [0.99],
                    "request_latency_ms": 10.0 + index,
                    "executed_action_sha256": action_hash(action),
                }
                for index, action in enumerate(actions)
            ],
            "outcome": {"success": True, "termination": "success", "reward": 1.0, "error_code": None},
        }
        self.stream = build_direct_vla_stream(self.sidecar, self.rows)

    def test_accepts_every_executed_action_linked_to_one_proposal(self) -> None:
        report = validate_direct_vla_trace(self.stream, self.sidecar, self.rows)
        self.assertTrue(report["valid"], report["errors"])
        self.assertEqual(report["executed_actions_linked"], 2)
        self.assertEqual(report["events"], 7)

    def test_rejects_observer_wrist_relabelled_as_model_input(self) -> None:
        stream = copy.deepcopy(self.stream)
        stream["events"][0]["payload"]["model_inputs"].append("observation.images.image2")
        self.assertIn(
            "frame[0]:observer_wrist_relabelled_as_model_input",
            validate_direct_vla_trace(stream, self.sidecar, self.rows)["errors"],
        )

    def test_rejects_raw_action_drift(self) -> None:
        stream = copy.deepcopy(self.stream)
        stream["events"][1]["payload"]["raw_action"][0] = 9.0
        self.assertIn("frame[0]:raw_action_drift", validate_direct_vla_trace(stream, self.sidecar, self.rows)["errors"])

    def test_rejects_executed_action_hash_drift(self) -> None:
        stream = copy.deepcopy(self.stream)
        stream["events"][2]["payload"]["executed_action"][0] = 9.0
        errors = validate_direct_vla_trace(stream, self.sidecar, self.rows)["errors"]
        self.assertIn("frame[0]:executed_action_drift", errors)
        self.assertIn("frame[0]:executed_action_hash_mismatch", errors)

    def test_rejects_unexecuted_proposal(self) -> None:
        stream = copy.deepcopy(self.stream)
        stream["events"][2]["payload"]["accepted"] = False
        self.assertIn("frame[0]:proposal_not_executed", validate_direct_vla_trace(stream, self.sidecar, self.rows)["errors"])

    def test_rejects_outcome_relabel(self) -> None:
        stream = copy.deepcopy(self.stream)
        stream["events"][-1]["payload"]["success"] = False
        self.assertIn("outcome_drift", validate_direct_vla_trace(stream, self.sidecar, self.rows)["errors"])


if __name__ == "__main__":
    unittest.main()
