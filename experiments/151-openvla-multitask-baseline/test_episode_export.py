#!/usr/bin/env python3
"""Canonical episode seal and adversarial provenance tests."""

from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from episode_export import atomic_write_manifest, build_sealed_manifest, validate_episode_bundle
from run_baseline import DEFAULT_REPO_ROOT, load_runner_contract, select_cells
from run_ledger import RunLedger


BASE = DEFAULT_REPO_ROOT / "experiments/147-camera-action-episode-contract/verify/canonical/pass"
SIDECAR = BASE / "dataset/meta/lab_provenance/episode_000000.json"
EVENTS = DEFAULT_REPO_ROOT / "experiments/148-observable-decision-action-trace/verify/direct-vla/pass-events.json"


class EpisodeExportTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        contract = load_runner_contract()
        cls.cell = select_cells(contract["cells"], suite="libero_spatial", task_id=5, state_index=0)[0]
        cls.info = json.loads((BASE / "dataset/meta/info.json").read_text(encoding="utf-8"))
        cls.sidecar = json.loads(SIDECAR.read_text(encoding="utf-8"))
        cls.events = json.loads(EVENTS.read_text(encoding="utf-8"))

    def test_canonical_bundle_seals_without_local_paths(self) -> None:
        manifest, report = build_sealed_manifest(
            cell=self.cell,
            dataset_root=BASE / "dataset",
            sidecar_path=SIDECAR,
            events_path=EVENTS,
            artifact_ref="episodes/libero-spatial-task-05-state-00",
        )
        self.assertTrue(report["valid"])
        self.assertEqual(report["frames"], 78)
        self.assertEqual(report["causal_events"], 235)
        self.assertEqual(manifest["status"], "sealed")
        self.assertNotIn(str(DEFAULT_REPO_ROOT), json.dumps(manifest))

    def test_atomic_seal_promotes_the_matching_ledger_attempt(self) -> None:
        contract = load_runner_contract()
        manifest, report = build_sealed_manifest(
            cell=self.cell,
            dataset_root=BASE / "dataset",
            sidecar_path=SIDECAR,
            events_path=EVENTS,
            artifact_ref="episodes/libero-spatial-task-05-state-00",
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            ledger = RunLedger(root / "runs.jsonl", [cell["run_key"] for cell in contract["cells"]])
            ledger.initialize()
            attempt = ledger.begin_attempt(self.cell["run_key"])
            manifest_path = root / "episode-manifest.json"
            manifest_sha = atomic_write_manifest(manifest_path, manifest)
            ledger.record_policy_terminal(
                self.cell["run_key"], attempt["attempt_id"], report["result_status"], manifest["evidence"]["artifact_ref"], manifest_sha
            )
            self.assertEqual(ledger.state().completed[self.cell["run_key"]], attempt["attempt_id"])
            self.assertTrue(manifest_path.is_file())
            self.assertFalse(manifest_path.with_suffix(".json.partial").exists())

    def test_camera_relabel_is_rejected(self) -> None:
        sidecar = copy.deepcopy(self.sidecar)
        sidecar["camera_roles"]["observation.images.image2"]["model_input"] = True
        report = validate_episode_bundle(self.cell, self.info, sidecar, self.events)
        self.assertFalse(report["valid"])
        self.assertIn("wrist-camera-role-mismatch", report["errors"])

    def test_missing_action_link_is_rejected(self) -> None:
        events = copy.deepcopy(self.events)
        events["events"][2]["payload"].pop("executed_action")
        report = validate_episode_bundle(self.cell, self.info, self.sidecar, events)
        self.assertFalse(report["valid"])
        self.assertIn("frame-0:executed-action-link-missing", report["errors"])

    def test_local_path_leak_is_rejected(self) -> None:
        sidecar = copy.deepcopy(self.sidecar)
        sidecar["debug_path"] = "C:/Users/example/cache"
        report = validate_episode_bundle(self.cell, self.info, sidecar, self.events)
        self.assertFalse(report["valid"])
        self.assertIn("local-path-leak", report["errors"])


if __name__ == "__main__":
    unittest.main()
