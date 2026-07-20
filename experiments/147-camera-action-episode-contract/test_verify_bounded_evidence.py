import json
import tempfile
import unittest
from pathlib import Path

from verify_bounded_evidence import evaluate_evidence


FIXTURES = Path(__file__).with_name("fixtures")
RRD_STATS = """
/observation.images.image: 1
/observation.images.image2: 1
/state: 1
/action: 1
frame_index: 4
timestamp: 4
"""


class BoundedEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "dataset"
        (self.root / "meta" / "lab_provenance").mkdir(parents=True)
        info = json.loads((FIXTURES / "lerobot-libero-info.json").read_text(encoding="utf-8"))
        info["total_frames"] = 1
        self.info_path = self.root / "meta" / "info.json"
        self.info_path.write_text(json.dumps(info), encoding="utf-8")
        sidecar = json.loads((FIXTURES / "valid-provenance.json").read_text(encoding="utf-8"))
        sidecar["action_events"] = [{"frame_index": 0}]
        self.sidecar_path = self.root / "meta" / "lab_provenance" / "episode_000000.json"
        self.sidecar_path.write_text(json.dumps(sidecar), encoding="utf-8")
        self.rrd_path = Path(self.temp.name) / "episode.rrd"
        self.rrd_path.write_bytes(b"valid-rrd-fixture")

    def tearDown(self):
        self.temp.cleanup()

    def evaluate(self, baseline=None, expected_frames=1, stats=RRD_STATS):
        return evaluate_evidence(
            dataset_root=self.root,
            sidecar_path=self.sidecar_path,
            rrd_path=self.rrd_path,
            expected_frames=expected_frames,
            producer_kind="synthetic-smoke",
            rrd_verified=True,
            rrd_stats=stats,
            baseline=baseline,
        )

    def test_accepts_hashed_dual_camera_rerun_evidence(self):
        report = self.evaluate()
        self.assertTrue(report["pass"])
        self.assertFalse(report["producer_claim_ready"])

    def test_rejects_frame_count_mismatch(self):
        report = self.evaluate(expected_frames=2)
        self.assertFalse(report["pass"])
        self.assertTrue(any("frame count mismatch" in error for error in report["errors"]))

    def test_rejects_missing_rerun_entity(self):
        report = self.evaluate(stats=RRD_STATS.replace("/action: 1", ""))
        self.assertFalse(report["pass"])
        self.assertIn("missing Rerun entity: /action", report["errors"])

    def test_rejects_hash_tamper_against_baseline(self):
        baseline = self.evaluate()
        self.rrd_path.write_bytes(b"tampered")
        report = self.evaluate(baseline=baseline)
        self.assertFalse(report["pass"])
        self.assertIn("hash mismatch: rrd_sha256", report["errors"])


if __name__ == "__main__":
    unittest.main()
