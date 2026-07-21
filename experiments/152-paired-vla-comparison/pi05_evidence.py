#!/usr/bin/env python3
"""Build and seal π0.5 causal episode evidence."""

from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pyarrow.parquet as pq

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
LAB1_DIR = REPO_ROOT / "experiments" / "147-camera-action-episode-contract"
LAB2_DIR = REPO_ROOT / "experiments" / "148-observable-decision-action-trace"
GEN2_DIR = REPO_ROOT / "experiments" / "151-openvla-multitask-baseline"
for dependency in (LAB1_DIR, LAB2_DIR, GEN2_DIR):
    if str(dependency) not in sys.path:
        sys.path.insert(0, str(dependency))

from episode_export import (  # noqa: E402
    LOCAL_PATH,
    _walk_strings,
    atomic_write_manifest,
    dataset_tree_hash,
    safe_artifact_ref,
    sha256_file,
)
from episode_profile import validate_profile  # noqa: E402
from event_schema import validate_event_stream  # noqa: E402

MAIN_CAMERA = "observation.images.image"
WRIST_CAMERA = "observation.images.image2"
PI05_REVISION = "11e0f560ebc9ca0f65d26241dd08e2ac07c22ee91455f1789afc2fc5c0378d7b"
MANIFEST_VERSION = "physical-ai-gen3-sealed-episode-v1"
REQUEST_ID = re.compile(r"^request-[0-9]{6}$")


class Pi05EvidenceError(ValueError):
    """Raised before an invalid π0.5 artifact can be sealed."""


def action_hash(action: Any) -> str:
    return hashlib.sha256(np.asarray(action, dtype="<f4").tobytes()).hexdigest()


def load_episode_rows(dataset_root: Path) -> list[dict[str, Any]]:
    rows = []
    for path in sorted((dataset_root / "data").rglob("*.parquet")):
        rows.extend(pq.read_table(path).to_pylist())
    rows.sort(key=lambda row: int(row["frame_index"]))
    return rows


def build_pi05_stream(sidecar: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    episode = sidecar["episode"]
    producer = sidecar["producer"]
    action_events = sidecar["action_events"]
    if len(rows) != len(action_events):
        raise Pi05EvidenceError("row/action-event count mismatch")
    events = []
    for row, action_event in zip(rows, action_events, strict=True):
        frame = int(row["frame_index"])
        timestamp = float(row["timestamp"])
        sensor_id = f"sensor-{frame:06d}"
        proposal_id = f"vla-{frame:06d}"
        controller_id = f"controller-{frame:06d}"
        events.extend(
            [
                {
                    "id": sensor_id,
                    "timestep": frame,
                    "timestamp_sec": timestamp,
                    "source": "sensor",
                    "kind": "model_input_observation",
                    "causal_role": "observation",
                    "parents": [],
                    "model_or_component": producer["environment"],
                    "payload_ref": f"lerobot://episode/{episode['index']}/frame/{frame}/{MAIN_CAMERA}",
                    "payload": {
                        "model_inputs": [MAIN_CAMERA, WRIST_CAMERA, "observation.state", "task"],
                        "observer_only": [],
                        "camera_roles": sidecar["camera_roles"],
                    },
                    "assistance": {"used": False, "source": "none"},
                },
                {
                    "id": proposal_id,
                    "timestep": frame,
                    "timestamp_sec": timestamp,
                    "source": "vla",
                    "kind": "chunk_action_proposal",
                    "causal_role": "proposal",
                    "parents": [sensor_id],
                    "model_or_component": producer["policy"],
                    "payload_ref": f"lab-provenance://episode/{episode['index']}/action_events/{frame}",
                    "payload": {
                        "raw_action": action_event["raw_policy_action"],
                        "request_id": action_event["request_id"],
                        "chunk_index": action_event["chunk_index"],
                        "is_request_step": action_event["is_request_step"],
                        "request_latency_ms": action_event["request_latency_ms"],
                    },
                    "assistance": {"used": False, "source": "none"},
                },
                {
                    "id": controller_id,
                    "timestep": frame,
                    "timestamp_sec": timestamp,
                    "source": "controller",
                    "kind": "action_acceptance",
                    "causal_role": "execution",
                    "parents": [proposal_id],
                    "model_or_component": {
                        "name": "libero-env-step",
                        "revision": producer["environment"]["revision"],
                    },
                    "payload_ref": f"lerobot://episode/{episode['index']}/frame/{frame}/action",
                    "payload": {
                        "accepted": True,
                        "executed_action": row["action"],
                        "executed_action_sha256": action_event["executed_action_sha256"],
                        "postprocess": ["take_first_7_dimensions_only"],
                    },
                    "assistance": {"used": False, "source": "none"},
                },
            ]
        )
    last = rows[-1]
    last_frame = int(last["frame_index"])
    events.append(
        {
            "id": "environment-outcome",
            "timestep": last_frame,
            "timestamp_sec": float(last["timestamp"]),
            "source": "environment",
            "kind": "episode_outcome",
            "causal_role": "result",
            "parents": [f"controller-{last_frame:06d}"],
            "model_or_component": producer["environment"],
            "payload_ref": f"lab-provenance://episode/{sidecar['episode']['index']}/outcome",
            "payload": sidecar["outcome"],
            "assistance": {"used": False, "source": "none"},
        }
    )
    return {
        "schema_version": "physical-ai-causal-events-v1",
        "episode_ref": {
            "dataset_revision": sidecar["episode"]["revision"],
            "episode_index": sidecar["episode"]["index"],
        },
        "lane": "direct_vla",
        "claim_boundary": "Recorded π0.5-LIBERO inference in simulation; no hidden reasoning or real telemetry.",
        "events": events,
    }


def validate_pi05_bundle(
    cell: dict[str, Any],
    info: dict[str, Any],
    sidecar: dict[str, Any],
    rows: list[dict[str, Any]],
    events: dict[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    profile = validate_profile(info, sidecar, require_provenance=True)
    errors.extend(f"profile:{error}" for error in profile["errors"])
    if sidecar.get("producer", {}).get("policy") != {"name": "pi0.5-libero", "revision": PI05_REVISION}:
        errors.append("policy-source-relabel")
    roles = sidecar.get("camera_roles", {})
    for feature, role in ((MAIN_CAMERA, "main"), (WRIST_CAMERA, "wrist")):
        if roles.get(feature, {}).get("role") != role or roles.get(feature, {}).get("model_input") is not True:
            errors.append(f"{role}-camera-role-mismatch")
    interface = sidecar.get("policy_interface", {})
    if interface.get("exposed_chunk_shape") != [10, 7] or interface.get("executed_prefix_steps") != 5:
        errors.append("policy-interface-drift")
    action_events = sidecar.get("action_events", [])
    if len(rows) != len(action_events) or not rows:
        errors.append("row-action-count-mismatch")
    previous_request = None
    expected_chunk_index = 0
    request_count = 0
    for frame, (row, action_event) in enumerate(zip(rows, action_events)):
        request_id = action_event.get("request_id")
        chunk_index = action_event.get("chunk_index")
        request_step = action_event.get("is_request_step")
        latency = action_event.get("request_latency_ms")
        if not REQUEST_ID.fullmatch(str(request_id)):
            errors.append(f"frame-{frame}:invalid-request-id")
        if request_id != previous_request:
            expected_chunk_index = 0
            request_count += 1
        if chunk_index != expected_chunk_index or chunk_index not in range(5):
            errors.append(f"frame-{frame}:chunk-order-drift")
        if request_step is not (chunk_index == 0):
            errors.append(f"frame-{frame}:request-step-drift")
        if not isinstance(latency, (int, float)) or not math.isfinite(latency) or latency < 0:
            errors.append(f"frame-{frame}:invalid-latency")
        if chunk_index != 0 and latency != 0:
            errors.append(f"frame-{frame}:duplicated-request-latency")
        raw = action_event.get("raw_policy_action")
        if not isinstance(raw, list) or len(raw) != 7 or not np.isfinite(np.asarray(raw)).all():
            errors.append(f"frame-{frame}:invalid-action")
        if action_hash(row.get("action")) != action_event.get("executed_action_sha256"):
            errors.append(f"frame-{frame}:action-hash-mismatch")
        previous_request = request_id
        expected_chunk_index += 1
    event_report = validate_event_stream(events)
    errors.extend(f"event-stream:{error}" for error in event_report["errors"])
    by_id = {event.get("id"): event for event in events.get("events", []) if isinstance(event, dict)}
    for frame, action_event in enumerate(action_events):
        sensor = by_id.get(f"sensor-{frame:06d}", {})
        proposal = by_id.get(f"vla-{frame:06d}", {})
        controller = by_id.get(f"controller-{frame:06d}", {})
        if sensor.get("payload", {}).get("model_inputs") != [MAIN_CAMERA, WRIST_CAMERA, "observation.state", "task"]:
            errors.append(f"frame-{frame}:model-input-relabel")
        proposal_request = proposal.get("payload", {}).get("request_id")
        if proposal.get("parents") != [sensor.get("id")] or proposal_request != action_event.get("request_id"):
            errors.append(f"frame-{frame}:proposal-link-drift")
        executed = controller.get("payload", {}).get("executed_action")
        if controller.get("parents") != [proposal.get("id")] or action_hash(executed) != action_event.get(
            "executed_action_sha256"
        ):
            errors.append(f"frame-{frame}:execution-link-drift")
    outcome = sidecar.get("outcome", {})
    if outcome.get("termination") not in {"success", "timeout"}:
        errors.append("invalid-policy-terminal")
    if cell.get("environment_revision") != sidecar.get("producer", {}).get("environment", {}).get("revision"):
        errors.append("environment-revision-drift")
    if any(LOCAL_PATH.search(value) for value in _walk_strings({"sidecar": sidecar, "events": events})):
        errors.append("local-path-leak")
    return {
        "valid": not errors,
        "errors": list(dict.fromkeys(errors)),
        "frames": len(rows),
        "request_count": request_count,
        "causal_events": len(events.get("events", [])),
        "result_status": outcome.get("termination"),
    }


def seal_pi05_episode(
    *, cell: dict[str, Any], dataset_root: Path, sidecar_path: Path, events_path: Path, artifact_ref: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    info_path = dataset_root / "meta" / "info.json"
    info = json.loads(info_path.read_text(encoding="utf-8"))
    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    rows = load_episode_rows(dataset_root)
    stream = build_pi05_stream(sidecar, rows)
    report = validate_pi05_bundle(cell, info, sidecar, rows, stream)
    if not report["valid"]:
        raise Pi05EvidenceError(f"π0.5 episode validation failed: {report['errors']}")
    events_path.parent.mkdir(parents=True, exist_ok=True)
    events_path.write_text(json.dumps(stream, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
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
            "policy_revision": PI05_REVISION,
            "adapter_revision": cell["adapter_revision"],
        },
        "outcome": {
            "status": report["result_status"],
            "frames": report["frames"],
            "request_count": report["request_count"],
        },
        "evidence": {
            "artifact_ref": safe_artifact_ref(artifact_ref),
            "dataset_tree_sha256": tree_hash,
            "dataset_file_count": file_count,
            "info_sha256": sha256_file(info_path),
            "sidecar_sha256": sha256_file(sidecar_path),
            "events_sha256": sha256_file(events_path),
            "causal_event_count": report["causal_events"],
        },
        "claim_boundary": "Recorded π0.5 inference in LIBERO simulation; not real telemetry or policy ranking.",
    }
    if any(LOCAL_PATH.search(value) for value in _walk_strings(manifest)):
        raise Pi05EvidenceError("sealed manifest contains a local path")
    return manifest, report


__all__ = ["Pi05EvidenceError", "atomic_write_manifest", "seal_pi05_episode", "validate_pi05_bundle"]
