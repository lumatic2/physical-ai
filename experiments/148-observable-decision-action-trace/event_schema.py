#!/usr/bin/env python3
"""Validate observable Physical AI causal event streams without external dependencies."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "physical-ai-causal-events-v1"
SOURCES = {"sensor", "vlm", "vla", "controller", "environment"}
LANES = {"direct_vla", "vlm_skill"}
ROLES = {"observation", "decision", "proposal", "execution", "result"}
ASSISTANCE_SOURCES = {"none", "simulator_ground_truth", "scripted_skill"}
ROLE_BY_SOURCE = {
    "sensor": {"observation"},
    "vlm": {"observation", "decision"},
    "vla": {"proposal"},
    "controller": {"execution"},
    "environment": {"result"},
}
HIDDEN_REASONING_KEYS = {
    "chain_of_thought",
    "chain-of-thought",
    "hidden_reasoning",
    "internal_reasoning",
    "reasoning",
    "rationale",
    "thoughts",
}
EVENT_FIELDS = {
    "id",
    "timestep",
    "timestamp_sec",
    "source",
    "kind",
    "causal_role",
    "parents",
    "model_or_component",
    "payload_ref",
    "payload",
    "assistance",
}


def _contains_hidden_reasoning(value: Any) -> bool:
    if isinstance(value, dict):
        return any(
            str(key).lower() in HIDDEN_REASONING_KEYS or _contains_hidden_reasoning(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(_contains_hidden_reasoning(item) for item in value)
    return False


def _valid_revision(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip()) and value.lower() not in {"latest", "main", "unknown"}


def validate_event_stream(document: Any) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(document, dict):
        return {"valid": False, "errors": ["document_not_object"], "event_count": 0}

    if document.get("schema_version") != SCHEMA_VERSION:
        errors.append("invalid_schema_version")
    if document.get("lane") not in LANES:
        errors.append("invalid_lane")
    if not isinstance(document.get("claim_boundary"), str) or not document["claim_boundary"].strip():
        errors.append("missing_claim_boundary")

    episode_ref = document.get("episode_ref")
    if not isinstance(episode_ref, dict):
        errors.append("missing_episode_ref")
    else:
        if not _valid_revision(episode_ref.get("dataset_revision")):
            errors.append("invalid_dataset_revision")
        if not isinstance(episode_ref.get("episode_index"), int) or episode_ref["episode_index"] < 0:
            errors.append("invalid_episode_index")

    events = document.get("events")
    if not isinstance(events, list) or not events:
        return {"valid": False, "errors": errors + ["events_missing_or_empty"], "event_count": 0}

    seen: dict[str, dict[str, Any]] = {}
    previous_time = -1.0
    for index, event in enumerate(events):
        prefix = f"event[{index}]"
        if not isinstance(event, dict):
            errors.append(f"{prefix}:not_object")
            continue
        missing = sorted(EVENT_FIELDS - set(event))
        if missing:
            errors.append(f"{prefix}:missing_fields:{','.join(missing)}")
        extra = sorted(set(event) - EVENT_FIELDS)
        if extra:
            errors.append(f"{prefix}:unknown_fields:{','.join(extra)}")
        if _contains_hidden_reasoning(event):
            errors.append(f"{prefix}:hidden_reasoning_forbidden")

        event_id = event.get("id")
        if not isinstance(event_id, str) or not event_id:
            errors.append(f"{prefix}:invalid_id")
        elif event_id in seen:
            errors.append(f"{prefix}:duplicate_id")

        timestep = event.get("timestep")
        if not isinstance(timestep, int) or timestep < 0:
            errors.append(f"{prefix}:invalid_timestep")
        timestamp = event.get("timestamp_sec")
        if not isinstance(timestamp, (int, float)) or isinstance(timestamp, bool) or not math.isfinite(timestamp) or timestamp < 0:
            errors.append(f"{prefix}:invalid_timestamp")
        elif timestamp < previous_time:
            errors.append(f"{prefix}:timestamp_regression")
        else:
            previous_time = float(timestamp)

        source = event.get("source")
        role = event.get("causal_role")
        if source not in SOURCES:
            errors.append(f"{prefix}:unknown_source")
        if role not in ROLES:
            errors.append(f"{prefix}:unknown_causal_role")
        elif source in ROLE_BY_SOURCE and role not in ROLE_BY_SOURCE[source]:
            errors.append(f"{prefix}:source_role_mismatch")

        parents = event.get("parents")
        if not isinstance(parents, list) or any(not isinstance(parent, str) or not parent for parent in parents):
            errors.append(f"{prefix}:invalid_parents")
        else:
            if len(parents) != len(set(parents)):
                errors.append(f"{prefix}:duplicate_parent")
            for parent in parents:
                if parent not in seen:
                    errors.append(f"{prefix}:missing_or_forward_parent:{parent}")
            if role != "observation" and not parents:
                errors.append(f"{prefix}:causal_event_requires_parent")

        component = event.get("model_or_component")
        if not isinstance(component, dict) or set(component) != {"name", "revision"}:
            errors.append(f"{prefix}:invalid_component")
        elif not isinstance(component["name"], str) or not component["name"].strip() or not _valid_revision(component["revision"]):
            errors.append(f"{prefix}:invalid_component_revision")

        if not isinstance(event.get("payload_ref"), str) or not event["payload_ref"].strip():
            errors.append(f"{prefix}:invalid_payload_ref")
        if not isinstance(event.get("payload"), dict):
            errors.append(f"{prefix}:invalid_payload")

        assistance = event.get("assistance")
        if not isinstance(assistance, dict) or set(assistance) != {"used", "source"}:
            errors.append(f"{prefix}:unmarked_assistance")
        else:
            used = assistance.get("used")
            assistance_source = assistance.get("source")
            if not isinstance(used, bool) or assistance_source not in ASSISTANCE_SOURCES:
                errors.append(f"{prefix}:invalid_assistance")
            elif used != (assistance_source != "none"):
                errors.append(f"{prefix}:assistance_flag_mismatch")

        if isinstance(event_id, str) and event_id:
            seen[event_id] = event

    return {"valid": not errors, "errors": errors, "event_count": len(events)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("stream", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = validate_event_stream(json.loads(args.stream.read_text(encoding="utf-8")))
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
