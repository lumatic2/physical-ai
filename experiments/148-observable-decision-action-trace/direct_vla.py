#!/usr/bin/env python3
"""Derive and verify direct-VLA causal events from a LAB1 LeRobot episode."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pyarrow.parquet as pq

from event_schema import validate_event_stream


MAIN_CAMERA = "observation.images.image"
WRIST_CAMERA = "observation.images.image2"


def _action_hash(action: Any) -> str:
    return hashlib.sha256(np.asarray(action, dtype="<f4").tobytes()).hexdigest()


def load_episode_rows(dataset_root: Path, episode_index: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for parquet_path in sorted((dataset_root / "data").rglob("*.parquet")):
        for row in pq.read_table(parquet_path).to_pylist():
            if int(row["episode_index"]) == episode_index:
                rows.append(row)
    rows.sort(key=lambda row: int(row["frame_index"]))
    return rows


def build_direct_vla_stream(sidecar: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    episode = sidecar["episode"]
    producer = sidecar["producer"]
    camera_roles = sidecar["camera_roles"]
    action_events = sidecar["action_events"]
    if len(rows) != len(action_events):
        raise ValueError("row/action-event count mismatch")

    events: list[dict[str, Any]] = []
    for row, action_event in zip(rows, action_events, strict=True):
        frame = int(row["frame_index"])
        timestamp = float(row["timestamp"])
        if frame != int(action_event["frame_index"]):
            raise ValueError(f"frame mismatch at {frame}")
        sensor_id = f"sensor-{frame:06d}"
        vla_id = f"vla-{frame:06d}"
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
                    "payload": {"model_inputs": [MAIN_CAMERA, "task"], "observer_only": [WRIST_CAMERA], "camera_roles": camera_roles},
                    "assistance": {"used": False, "source": "none"},
                },
                {
                    "id": vla_id,
                    "timestep": frame,
                    "timestamp_sec": timestamp,
                    "source": "vla",
                    "kind": "action_proposal",
                    "causal_role": "proposal",
                    "parents": [sensor_id],
                    "model_or_component": producer["policy"],
                    "payload_ref": f"lab-provenance://episode/{episode['index']}/action_events/{frame}/raw_policy_action",
                    "payload": {"raw_action": action_event["raw_policy_action"], "latency_ms": action_event["request_latency_ms"]},
                    "assistance": {"used": False, "source": "none"},
                },
                {
                    "id": controller_id,
                    "timestep": frame,
                    "timestamp_sec": timestamp,
                    "source": "controller",
                    "kind": "action_acceptance",
                    "causal_role": "execution",
                    "parents": [vla_id],
                    "model_or_component": {"name": "libero-env-step", "revision": producer["environment"]["revision"]},
                    "payload_ref": f"lerobot://episode/{episode['index']}/frame/{frame}/action",
                    "payload": {
                        "accepted": True,
                        "executed_action": row["action"],
                        "executed_action_sha256": action_event["executed_action_sha256"],
                        "postprocess": ["normalize_gripper", "invert_gripper"],
                    },
                    "assistance": {"used": False, "source": "none"},
                },
            ]
        )

    last_frame = int(rows[-1]["frame_index"])
    events.append(
        {
            "id": "environment-outcome",
            "timestep": last_frame,
            "timestamp_sec": float(rows[-1]["timestamp"]),
            "source": "environment",
            "kind": "episode_outcome",
            "causal_role": "result",
            "parents": [f"controller-{last_frame:06d}"],
            "model_or_component": producer["environment"],
            "payload_ref": f"lab-provenance://episode/{episode['index']}/outcome",
            "payload": sidecar["outcome"],
            "assistance": {"used": False, "source": "none"},
        }
    )
    return {
        "schema_version": "physical-ai-causal-events-v1",
        "episode_ref": {"dataset_revision": episode["revision"], "episode_index": episode["index"]},
        "lane": "direct_vla",
        "claim_boundary": "recorded direct OpenVLA inference in LIBERO simulation; no language reasoning or real telemetry",
        "events": events,
    }


def validate_direct_vla_trace(stream: dict[str, Any], sidecar: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    base = validate_event_stream(stream)
    errors = list(base["errors"])
    if stream.get("lane") != "direct_vla":
        errors.append("lane_not_direct_vla")
    action_events = sidecar.get("action_events", [])
    if len(rows) != len(action_events):
        errors.append("row_action_event_count_mismatch")
    if len(stream.get("events", [])) != len(rows) * 3 + 1:
        errors.append("event_count_mismatch")

    events_by_id = {event.get("id"): event for event in stream.get("events", []) if isinstance(event, dict)}
    for index, (row, action_event) in enumerate(zip(rows, action_events)):
        sensor = events_by_id.get(f"sensor-{index:06d}", {})
        proposal = events_by_id.get(f"vla-{index:06d}", {})
        controller = events_by_id.get(f"controller-{index:06d}", {})
        sensor_payload = sensor.get("payload", {})
        if MAIN_CAMERA not in sensor_payload.get("model_inputs", []):
            errors.append(f"frame[{index}]:main_camera_not_model_input")
        if WRIST_CAMERA in sensor_payload.get("model_inputs", []):
            errors.append(f"frame[{index}]:observer_wrist_relabelled_as_model_input")
        if WRIST_CAMERA not in sensor_payload.get("observer_only", []):
            errors.append(f"frame[{index}]:wrist_observer_role_missing")
        if proposal.get("parents") != [sensor.get("id")]:
            errors.append(f"frame[{index}]:proposal_parent_mismatch")
        if proposal.get("payload", {}).get("raw_action") != action_event.get("raw_policy_action"):
            errors.append(f"frame[{index}]:raw_action_drift")
        if controller.get("parents") != [proposal.get("id")]:
            errors.append(f"frame[{index}]:controller_parent_mismatch")
        executed = controller.get("payload", {}).get("executed_action")
        if executed is None or not np.array_equal(np.asarray(executed, dtype="<f4"), np.asarray(row["action"], dtype="<f4")):
            errors.append(f"frame[{index}]:executed_action_drift")
        expected_hash = action_event.get("executed_action_sha256")
        if executed is None or _action_hash(executed) != expected_hash:
            errors.append(f"frame[{index}]:executed_action_hash_mismatch")
        if controller.get("payload", {}).get("accepted") is not True:
            errors.append(f"frame[{index}]:proposal_not_executed")

    outcome = events_by_id.get("environment-outcome", {})
    if rows and outcome.get("parents") != [f"controller-{len(rows) - 1:06d}"]:
        errors.append("outcome_parent_mismatch")
    if outcome.get("payload") != sidecar.get("outcome"):
        errors.append("outcome_drift")
    action_errors = ("action_drift", "action_hash", "proposal_not_executed")
    return {
        "valid": not errors,
        "errors": errors,
        "frames": len(rows),
        "events": len(stream.get("events", [])),
        "executed_actions_linked": len(rows) if not any(any(token in error for token in action_errors) for error in errors) else 0,
        "wrist_model_input": any(
            WRIST_CAMERA in event.get("payload", {}).get("model_inputs", [])
            for event in stream.get("events", [])
            if event.get("source") == "sensor"
        ),
    }


def emit_direct_vla_trace(dataset_root: Path, sidecar_path: Path, output_path: Path) -> dict[str, Any]:
    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    rows = load_episode_rows(dataset_root, int(sidecar["episode"]["index"]))
    if not rows:
        raise ValueError("episode has no dataset rows")
    stream = build_direct_vla_stream(sidecar, rows)
    report = validate_direct_vla_trace(stream, sidecar, rows)
    if not report["valid"]:
        raise ValueError(f"direct VLA trace failed validation: {report['errors']}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(stream, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--sidecar", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    report = emit_direct_vla_trace(args.dataset_root, args.sidecar, args.output)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
