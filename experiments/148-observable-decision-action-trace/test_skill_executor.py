from __future__ import annotations

import copy
import unittest

from skill_executor import build_vlm_skill_stream, validate_skill_binding, validate_vlm_skill_trace


class SkillExecutorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.vlm = {
            "model": {"name": "Qwen/Qwen3-VL-4B-Instruct", "revision": "ebb281e", "license": "apache-2.0"},
            "input": {"image_sha256": "a" * 64, "instruction": "pick up the black bowl"},
            "generation": {"latency_ms": 100.0},
            "decision": {
                "scene": {
                    "visible_objects": ["black_bowl", "ramekin", "plate", "robot_gripper"],
                    "target": "black_bowl",
                    "destination": "plate",
                    "spatial_summary": "The bowl is on a ramekin near a plate.",
                },
                "selected_skill": {"name": "pick_and_place", "target": "black_bowl", "destination": "plate"},
                "confidence": 0.9,
            },
        }
        self.execution = {
            "skill": {**self.vlm["decision"]["selected_skill"], "implementation": "canonical_action_replay"},
            "assistance": {"used": True, "source": "scripted_skill"},
            "action_source": {"kind": "canonical_action_replay", "dataset_revision": "777701b", "episode_index": 0},
            "environment": {"name": "libero", "revision": "8f1084e"},
            "actions_requested": 78,
            "actions_executed": 78,
            "outcome": {"success": True, "termination": "success", "reward": 1.0, "measured": True, "latency_ms": 10.0},
        }
        self.sidecar = {"episode": {"revision": "777701b", "index": 0}}
        self.stream = build_vlm_skill_stream(vlm_record=self.vlm, execution=self.execution, sidecar=self.sidecar)

    def test_accepts_allowlisted_skill_and_measured_outcome(self) -> None:
        self.assertEqual(validate_skill_binding(self.vlm["decision"])["implementation"], "canonical_action_replay")
        report = validate_vlm_skill_trace(self.stream, self.execution)
        self.assertTrue(report["valid"], report["errors"])

    def test_rejects_unsupported_valid_binding_before_execution(self) -> None:
        decision = copy.deepcopy(self.vlm["decision"])
        decision["scene"]["target"] = "ramekin"
        decision["selected_skill"]["target"] = "ramekin"
        with self.assertRaisesRegex(ValueError, "unsupported_skill_binding"):
            validate_skill_binding(decision)

    def test_rejects_missing_scripted_assistance(self) -> None:
        stream = copy.deepcopy(self.stream)
        stream["events"][3]["assistance"] = {"used": False, "source": "none"}
        self.assertIn("event[3]:scripted_assistance_missing", validate_vlm_skill_trace(stream, self.execution)["errors"])

    def test_rejects_unmeasured_outcome(self) -> None:
        execution = copy.deepcopy(self.execution)
        execution["outcome"]["measured"] = False
        self.assertIn("outcome_not_measured", validate_vlm_skill_trace(self.stream, execution)["errors"])

    def test_rejects_scripted_outcome_relabel(self) -> None:
        stream = copy.deepcopy(self.stream)
        stream["events"][4]["payload"]["success"] = False
        self.assertIn("skill_outcome_drift", validate_vlm_skill_trace(stream, self.execution)["errors"])


if __name__ == "__main__":
    unittest.main()
