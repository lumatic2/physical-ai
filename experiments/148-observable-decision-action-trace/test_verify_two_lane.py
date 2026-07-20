from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from verify_two_lane import evaluate_two_lane


ROOT = Path(__file__).parent


class TwoLaneEvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.streams = {
            "direct_pass": json.loads((ROOT / "verify/direct-vla/pass-events.json").read_text(encoding="utf-8")),
            "direct_fail": json.loads((ROOT / "verify/direct-vla/fail-events.json").read_text(encoding="utf-8")),
            "vlm_pass": json.loads((ROOT / "verify/vlm-skill/vlm-skill-events.json").read_text(encoding="utf-8")),
            "vlm_fail": json.loads((ROOT / "verify/vlm-skill/vlm-skill-events-fail.json").read_text(encoding="utf-8")),
        }

    def test_accepts_four_actual_source_tagged_traces(self) -> None:
        report = evaluate_two_lane(self.streams)
        self.assertTrue(report["pass"], report["errors"])

    def test_rejects_vlm_event_relabelled_as_vla_thought(self) -> None:
        streams = copy.deepcopy(self.streams)
        streams["vlm_pass"]["events"][1]["source"] = "vla"
        errors = evaluate_two_lane(streams)["errors"]
        self.assertIn("vlm_pass:vlm_source_boundary_broken", errors)

    def test_rejects_scripted_controller_assistance_removed(self) -> None:
        streams = copy.deepcopy(self.streams)
        streams["vlm_pass"]["events"][3]["assistance"] = {"used": False, "source": "none"}
        self.assertTrue(any("scripted_assistance_missing" in error for error in evaluate_two_lane(streams)["errors"]))

    def test_rejects_scripted_outcome_relabelled_as_model_result(self) -> None:
        streams = copy.deepcopy(self.streams)
        event = streams["vlm_pass"]["events"][4]
        event["source"] = "vlm"
        event["assistance"] = {"used": False, "source": "none"}
        self.assertTrue(any("vlm_source_boundary_broken" in error or "source_role_mismatch" in error for error in evaluate_two_lane(streams)["errors"]))

    def test_rejects_hidden_reasoning_field(self) -> None:
        streams = copy.deepcopy(self.streams)
        streams["direct_pass"]["events"][1]["payload"]["reasoning"] = "invented"
        self.assertTrue(any("hidden_reasoning_forbidden" in error for error in evaluate_two_lane(streams)["errors"]))

    def test_rejects_outcome_drift(self) -> None:
        streams = copy.deepcopy(self.streams)
        streams["direct_fail"]["events"][-1]["payload"]["success"] = True
        self.assertIn("direct_fail:outcome_drift", evaluate_two_lane(streams)["errors"])


if __name__ == "__main__":
    unittest.main()
