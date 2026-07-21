#!/usr/bin/env python3
"""Verify the existing LAB1/LAB2 PASS episode through the GEN2 seal contract."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

from episode_export import build_sealed_manifest, validate_episode_bundle
from run_baseline import DEFAULT_REPO_ROOT, load_runner_contract, select_cells


def verify() -> dict:
    base = DEFAULT_REPO_ROOT / "experiments/147-camera-action-episode-contract/verify/canonical/pass"
    sidecar_path = base / "dataset/meta/lab_provenance/episode_000000.json"
    events_path = DEFAULT_REPO_ROOT / "experiments/148-observable-decision-action-trace/verify/direct-vla/pass-events.json"
    contract = load_runner_contract()
    cell = select_cells(contract["cells"], suite="libero_spatial", task_id=5, state_index=0)[0]
    manifest, validation = build_sealed_manifest(
        cell=cell,
        dataset_root=base / "dataset",
        sidecar_path=sidecar_path,
        events_path=events_path,
        artifact_ref="episodes/libero-spatial-task-05-state-00",
    )
    info = json.loads((base / "dataset/meta/info.json").read_text(encoding="utf-8"))
    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    events = json.loads(events_path.read_text(encoding="utf-8"))
    rejected = []
    camera_mutation = copy.deepcopy(sidecar)
    camera_mutation["camera_roles"]["observation.images.image2"]["model_input"] = True
    if not validate_episode_bundle(cell, info, camera_mutation, events)["valid"]:
        rejected.append("camera-relabel")
    action_mutation = copy.deepcopy(events)
    action_mutation["events"][2]["payload"].pop("executed_action")
    if not validate_episode_bundle(cell, info, sidecar, action_mutation)["valid"]:
        rejected.append("missing-action-link")
    path_mutation = copy.deepcopy(sidecar)
    path_mutation["debug_path"] = "/home/example/cache"
    if not validate_episode_bundle(cell, info, path_mutation, events)["valid"]:
        rejected.append("local-path-leak")
    return {
        "schema_version": "physical-ai-gen2-episode-export-verification-v1",
        "pass": validation["valid"] and rejected == ["camera-relabel", "missing-action-link", "local-path-leak"],
        "run_key": cell["run_key"],
        "frames": validation["frames"],
        "causal_events": validation["causal_events"],
        "camera_keys": validation["camera_keys"],
        "state_shape": validation["state_shape"],
        "action_shape": validation["action_shape"],
        "result_status": validation["result_status"],
        "sealed_evidence": manifest["evidence"],
        "rejected": rejected,
        "claim_boundary": "Reuses one LAB1/LAB2 recorded PASS as an exporter proof; no new rollout was executed.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = verify()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
