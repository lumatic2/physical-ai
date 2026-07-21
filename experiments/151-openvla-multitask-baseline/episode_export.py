#!/usr/bin/env python3
"""Validate LAB1/LAB2 artifacts, atomically seal them, then complete one ledger attempt."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import re
import sys
from pathlib import Path
from typing import Any

import numpy as np

from run_baseline import DEFAULT_REPO_ROOT, load_runner_contract, select_cells
from run_ledger import RunLedger


LAB1_DIR = DEFAULT_REPO_ROOT / "experiments" / "147-camera-action-episode-contract"
LAB2_DIR = DEFAULT_REPO_ROOT / "experiments" / "148-observable-decision-action-trace"
for dependency in (LAB1_DIR, LAB2_DIR):
    if str(dependency) not in sys.path:
        sys.path.insert(0, str(dependency))

from episode_profile import validate_profile  # noqa: E402
from event_schema import validate_event_stream  # noqa: E402
from verify_bounded_evidence import dataset_tree_hash, sha256_file  # noqa: E402


MANIFEST_VERSION = "physical-ai-gen2-sealed-episode-v1"
MAIN_CAMERA = "observation.images.image"
WRIST_CAMERA = "observation.images.image2"
HEX64 = re.compile(r"^[0-9a-f]{64}$")
LOCAL_PATH = re.compile(r"(?:[A-Za-z]:[/\\]Users[/\\]|/home/|/Users/|AppData)", re.I)


class EpisodeExportError(ValueError):
    """Raised before a partial artifact can be promoted to sealed evidence."""


def _action_hash(action: Any) -> str:
    return hashlib.sha256(np.asarray(action, dtype="<f4").tobytes()).hexdigest()


def _walk_strings(value: Any) -> list[str]:
    if isinstance(value, dict):
        return [item for child in value.values() for item in _walk_strings(child)]
    if isinstance(value, list):
        return [item for child in value for item in _walk_strings(child)]
    return [value] if isinstance(value, str) else []


def safe_artifact_ref(value: str) -> str:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or LOCAL_PATH.search(value):
        raise EpisodeExportError("artifact ref must be relative and path-scrubbed")
    normalized = path.as_posix()
    if not normalized or normalized == ".":
        raise EpisodeExportError("artifact ref is required")
    return normalized


def validate_episode_bundle(
    cell: dict[str, Any], info: dict[str, Any], sidecar: dict[str, Any], events: dict[str, Any]
) -> dict[str, Any]:
    errors: list[str] = []
    profile = validate_profile(info, sidecar, require_provenance=True)
    errors.extend(f"profile:{error['code']}" for error in profile["errors"])
    rollout = sidecar.get("rollout", {})
    producer = sidecar.get("producer", {})
    if rollout.get("suite") != cell["suite"] or int(rollout.get("task_id", -1)) != cell["task_id"]:
        errors.append("run-key-task-mismatch")
    if int(rollout.get("init_state_index", -1)) != cell["state_index"]:
        errors.append("run-key-state-mismatch")
    if producer.get("environment", {}).get("revision") != cell["environment_revision"]:
        errors.append("environment-revision-mismatch")
    if producer.get("policy", {}).get("revision") != cell["checkpoint_revision"]:
        errors.append("policy-revision-mismatch")
    roles = sidecar.get("camera_roles", {})
    if roles.get(MAIN_CAMERA, {}).get("role") != "main" or roles.get(MAIN_CAMERA, {}).get("model_input") is not True:
        errors.append("main-camera-role-mismatch")
    if roles.get(WRIST_CAMERA, {}).get("role") != "wrist" or roles.get(WRIST_CAMERA, {}).get("model_input") is not False:
        errors.append("wrist-camera-role-mismatch")

    action_events = sidecar.get("action_events", [])
    if not action_events:
        errors.append("missing-action-events")
    timestamps = []
    for frame, action in enumerate(action_events):
        if action.get("frame_index") != frame:
            errors.append(f"frame-{frame}:non-contiguous-action")
        timestamp = action.get("timestamp_seconds")
        if not isinstance(timestamp, (int, float)) or not math.isfinite(timestamp):
            errors.append(f"frame-{frame}:invalid-timestamp")
        else:
            timestamps.append(float(timestamp))
        raw = action.get("raw_policy_action")
        if not isinstance(raw, list) or len(raw) != 7:
            errors.append(f"frame-{frame}:invalid-raw-action")
        if not HEX64.fullmatch(str(action.get("executed_action_sha256", ""))):
            errors.append(f"frame-{frame}:missing-executed-action-link")
    if timestamps != sorted(timestamps) or len(timestamps) != len(set(timestamps)):
        errors.append("timestamps-not-strictly-increasing")
    if info.get("total_frames") != len(action_events):
        errors.append("info-sidecar-frame-count-mismatch")

    event_report = validate_event_stream(events)
    errors.extend(f"event-stream:{error}" for error in event_report["errors"])
    if events.get("lane") != "direct_vla":
        errors.append("event-lane-mismatch")
    by_id = {event.get("id"): event for event in events.get("events", []) if isinstance(event, dict)}
    for frame, action in enumerate(action_events):
        sensor = by_id.get(f"sensor-{frame:06d}", {})
        proposal = by_id.get(f"vla-{frame:06d}", {})
        controller = by_id.get(f"controller-{frame:06d}", {})
        if not (
            isinstance(sensor.get("timestamp_sec"), (int, float))
            and isinstance(action.get("timestamp_seconds"), (int, float))
            and math.isclose(
                float(sensor["timestamp_sec"]), float(action["timestamp_seconds"]), rel_tol=0.0, abs_tol=1e-6
            )
        ):
            errors.append(f"frame-{frame}:sensor-timestamp-drift")
        payload = sensor.get("payload", {})
        if MAIN_CAMERA not in payload.get("model_inputs", []) or WRIST_CAMERA in payload.get("model_inputs", []):
            errors.append(f"frame-{frame}:camera-relabel")
        if WRIST_CAMERA not in payload.get("observer_only", []):
            errors.append(f"frame-{frame}:wrist-observer-link-missing")
        if proposal.get("parents") != [sensor.get("id")] or proposal.get("payload", {}).get("raw_action") != action.get(
            "raw_policy_action"
        ):
            errors.append(f"frame-{frame}:raw-action-link-missing")
        executed = controller.get("payload", {}).get("executed_action")
        if controller.get("parents") != [proposal.get("id")] or executed is None:
            errors.append(f"frame-{frame}:executed-action-link-missing")
        elif _action_hash(executed) != action.get("executed_action_sha256"):
            errors.append(f"frame-{frame}:executed-action-hash-mismatch")
    outcome = sidecar.get("outcome", {})
    outcome_event = by_id.get("environment-outcome", {})
    if outcome_event.get("payload") != outcome:
        errors.append("outcome-link-mismatch")
    if outcome.get("termination") not in {"success", "timeout"}:
        errors.append("episode-is-not-valid-policy-terminal")
    if any(LOCAL_PATH.search(value) for value in _walk_strings({"sidecar": sidecar, "events": events})):
        errors.append("local-path-leak")
    return {
        "valid": not errors,
        "errors": list(dict.fromkeys(errors)),
        "frames": len(action_events),
        "causal_events": len(events.get("events", [])),
        "camera_keys": profile["camera_keys"],
        "state_shape": profile["state_shape"],
        "action_shape": profile["action_shape"],
        "result_status": outcome.get("termination"),
    }


def build_sealed_manifest(
    *,
    cell: dict[str, Any],
    dataset_root: Path,
    sidecar_path: Path,
    events_path: Path,
    artifact_ref: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    info_path = dataset_root / "meta" / "info.json"
    info = json.loads(info_path.read_text(encoding="utf-8"))
    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    events = json.loads(events_path.read_text(encoding="utf-8"))
    report = validate_episode_bundle(cell, info, sidecar, events)
    if not report["valid"]:
        raise EpisodeExportError(f"episode bundle validation failed: {report['errors']}")
    tree_hash, file_count = dataset_tree_hash(dataset_root)
    manifest = {
        "schema_version": MANIFEST_VERSION,
        "status": "sealed",
        "run_key": cell["run_key"],
        "identity": {
            "suite": cell["suite"],
            "task_id": cell["task_id"],
            "state_index": cell["state_index"],
            "environment_revision": cell["environment_revision"],
            "policy_revision": cell["checkpoint_revision"],
            "adapter_revision": cell["adapter_revision"],
        },
        "outcome": {"status": report["result_status"], "frames": report["frames"]},
        "evidence": {
            "artifact_ref": safe_artifact_ref(artifact_ref),
            "dataset_tree_sha256": tree_hash,
            "dataset_file_count": file_count,
            "info_sha256": sha256_file(info_path),
            "sidecar_sha256": sha256_file(sidecar_path),
            "events_sha256": sha256_file(events_path),
            "causal_event_count": report["causal_events"],
        },
        "claim_boundary": "recorded OpenVLA inference in LIBERO simulation; not live inference or real telemetry",
    }
    if any(LOCAL_PATH.search(value) for value in _walk_strings(manifest)):
        raise EpisodeExportError("sealed manifest contains a local path")
    return manifest, report


def atomic_write_manifest(path: Path, manifest: dict[str, Any]) -> str:
    rendered = (json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")
    digest = hashlib.sha256(rendered).hexdigest()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".partial")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        if os.write(descriptor, rendered) != len(rendered):
            raise OSError("short sealed-manifest write")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    os.replace(temporary, path)
    return digest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-key", required=True)
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--sidecar", type=Path, required=True)
    parser.add_argument("--events", type=Path, required=True)
    parser.add_argument("--artifact-ref", required=True)
    parser.add_argument("--manifest-output", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--attempt-id", required=True)
    args = parser.parse_args()
    contract = load_runner_contract()
    cell = select_cells(contract["cells"], run_key=args.run_key)[0]
    try:
        manifest, report = build_sealed_manifest(
            cell=cell,
            dataset_root=args.dataset_root,
            sidecar_path=args.sidecar,
            events_path=args.events,
            artifact_ref=args.artifact_ref,
        )
        manifest_sha = atomic_write_manifest(args.manifest_output, manifest)
        ledger = RunLedger(args.ledger, [item["run_key"] for item in contract["cells"]])
        ledger.record_policy_terminal(
            cell["run_key"], args.attempt_id, report["result_status"], safe_artifact_ref(args.artifact_ref), manifest_sha
        )
    except (EpisodeExportError, OSError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps({"pass": True, "manifest_sha256": manifest_sha, **report}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
