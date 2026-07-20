import copy
import json
import unittest
from pathlib import Path

from episode_profile import validate_profile


FIXTURES = Path(__file__).with_name("fixtures")


def load_fixture(name: str):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class EpisodeProfileTests(unittest.TestCase):
    def setUp(self):
        self.info = load_fixture("lerobot-libero-info.json")
        self.provenance = load_fixture("valid-provenance.json")

    def assertRejected(self, report, code):
        self.assertFalse(report["valid"])
        self.assertIn(code, [error["code"] for error in report["errors"]])

    def test_public_lerobot_libero_profile_passes_without_lab_sidecar(self):
        report = validate_profile(self.info)
        self.assertTrue(report["valid"])
        self.assertEqual(len(report["camera_keys"]), 2)

    def test_local_lab_profile_requires_and_accepts_provenance(self):
        report = validate_profile(self.info, self.provenance, require_provenance=True)
        self.assertTrue(report["valid"])

    def test_rejects_single_camera(self):
        report = validate_profile(load_fixture("single-camera-info.json"))
        self.assertRejected(report, "insufficient_cameras")

    def test_rejects_missing_action(self):
        report = validate_profile(load_fixture("missing-action-info.json"))
        self.assertRejected(report, "missing_required_feature")

    def test_rejects_unpinned_policy_revision(self):
        report = validate_profile(
            self.info,
            load_fixture("invalid-revision-provenance.json"),
            require_provenance=True,
        )
        self.assertRejected(report, "invalid_policy_revision")

    def test_rejects_canonical_action_duplicated_in_sidecar(self):
        provenance = copy.deepcopy(self.provenance)
        provenance["action"] = [0.0] * 7
        report = validate_profile(self.info, provenance, require_provenance=True)
        self.assertRejected(report, "canonical_field_duplicated")

    def test_rejects_undeclared_wrist_camera_source(self):
        provenance = copy.deepcopy(self.provenance)
        provenance["camera_roles"].pop("observation.images.image2")
        report = validate_profile(self.info, provenance, require_provenance=True)
        self.assertRejected(report, "undeclared_camera_source")


if __name__ == "__main__":
    unittest.main()

