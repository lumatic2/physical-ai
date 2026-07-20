from __future__ import annotations

import unittest

from vlm_runner import parse_structured_output, validate_vlm_decision


VALID = {
    "scene": {
        "visible_objects": ["black_bowl", "ramekin", "plate", "robot_gripper"],
        "target": "black_bowl",
        "destination": "plate",
        "spatial_summary": "A black bowl rests on the ramekin near a plate.",
    },
    "selected_skill": {"name": "pick_and_place", "target": "black_bowl", "destination": "plate"},
    "confidence": 0.9,
}


class VlmRunnerTests(unittest.TestCase):
    def test_accepts_bounded_decision(self) -> None:
        self.assertTrue(validate_vlm_decision(VALID)["valid"])

    def test_rejects_malformed_or_wrapped_json(self) -> None:
        with self.assertRaisesRegex(ValueError, "bare JSON"):
            parse_structured_output("```json\n{}\n```")
        with self.assertRaisesRegex(ValueError, "malformed JSON"):
            parse_structured_output("{bad}")

    def test_rejects_unknown_object(self) -> None:
        value = {**VALID, "scene": {**VALID["scene"], "visible_objects": ["mystery_cube"]}}
        self.assertIn("unknown_visible_object", validate_vlm_decision(value)["errors"])

    def test_rejects_non_allowlisted_skill(self) -> None:
        value = {**VALID, "selected_skill": {**VALID["selected_skill"], "name": "free_form_agent"}}
        self.assertIn("skill_not_allowlisted", validate_vlm_decision(value)["errors"])

    def test_rejects_invalid_target(self) -> None:
        value = {**VALID, "selected_skill": {**VALID["selected_skill"], "target": "plate", "destination": "plate"}}
        errors = validate_vlm_decision(value)["errors"]
        self.assertIn("invalid_pick_target", errors)
        self.assertIn("scene_skill_object_mismatch", errors)


if __name__ == "__main__":
    unittest.main()
