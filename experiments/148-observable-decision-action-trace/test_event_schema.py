from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from event_schema import validate_event_stream


FIXTURES = Path(__file__).with_name("fixtures")


class EventSchemaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.valid = json.loads((FIXTURES / "valid-direct-vla-events.json").read_text(encoding="utf-8"))

    def test_accepts_valid_direct_vla_chain(self) -> None:
        report = validate_event_stream(self.valid)
        self.assertTrue(report["valid"], report["errors"])
        self.assertEqual(report["event_count"], 4)

    def test_rejects_unknown_source(self) -> None:
        document = copy.deepcopy(self.valid)
        document["events"][1]["source"] = "assistant"
        self.assertIn("event[1]:unknown_source", validate_event_stream(document)["errors"])

    def test_rejects_hidden_reasoning_anywhere(self) -> None:
        document = copy.deepcopy(self.valid)
        document["events"][1]["payload"]["chain_of_thought"] = "invented"
        self.assertIn("event[1]:hidden_reasoning_forbidden", validate_event_stream(document)["errors"])

    def test_rejects_missing_parent(self) -> None:
        document = copy.deepcopy(self.valid)
        document["events"][2]["parents"] = ["missing-vla-event"]
        self.assertIn("event[2]:missing_or_forward_parent:missing-vla-event", validate_event_stream(document)["errors"])

    def test_rejects_cyclic_or_forward_parent(self) -> None:
        document = copy.deepcopy(self.valid)
        document["events"][0]["parents"] = ["environment-000000"]
        self.assertIn("event[0]:missing_or_forward_parent:environment-000000", validate_event_stream(document)["errors"])

    def test_rejects_unmarked_assistance(self) -> None:
        document = copy.deepcopy(self.valid)
        del document["events"][2]["assistance"]
        self.assertIn("event[2]:unmarked_assistance", validate_event_stream(document)["errors"])

    def test_rejects_temporal_adjacency_relabelled_as_cause(self) -> None:
        document = copy.deepcopy(self.valid)
        document["events"][2]["parents"] = []
        self.assertIn("event[2]:causal_event_requires_parent", validate_event_stream(document)["errors"])

    def test_rejects_source_role_mismatch(self) -> None:
        document = copy.deepcopy(self.valid)
        document["events"][1]["causal_role"] = "decision"
        self.assertIn("event[1]:source_role_mismatch", validate_event_stream(document)["errors"])

    def test_rejects_unpinned_component_revision(self) -> None:
        document = copy.deepcopy(self.valid)
        document["events"][1]["model_or_component"]["revision"] = "latest"
        self.assertIn("event[1]:invalid_component_revision", validate_event_stream(document)["errors"])


if __name__ == "__main__":
    unittest.main()
