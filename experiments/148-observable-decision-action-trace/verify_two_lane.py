#!/usr/bin/env python3
"""Verify direct-VLA and VLM-to-skill PASS/FAIL traces as one evidence bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from event_schema import validate_event_stream


STREAM_NAMES = ("direct_pass", "direct_fail", "vlm_pass", "vlm_fail")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _environment_outcome(stream: dict[str, Any]) -> dict[str, Any]:
    results = [event for event in stream.get("events", []) if event.get("source") == "environment" and event.get("causal_role") == "result"]
    return results[-1].get("payload", {}) if results else {}


def _component_revisions(stream: dict[str, Any], source: str) -> set[tuple[str, str]]:
    return {
        (event["model_or_component"]["name"], event["model_or_component"]["revision"])
        for event in stream.get("events", [])
        if event.get("source") == source and isinstance(event.get("model_or_component"), dict)
    }


def evaluate_two_lane(streams: dict[str, dict[str, Any]], paths: dict[str, Path] | None = None) -> dict[str, Any]:
    errors: list[str] = []
    schema_reports = {name: validate_event_stream(streams.get(name)) for name in STREAM_NAMES}
    for name, report in schema_reports.items():
        errors.extend(f"{name}:{error}" for error in report["errors"])

    for name in ("direct_pass", "direct_fail"):
        stream = streams[name]
        sources = {event.get("source") for event in stream.get("events", [])}
        if stream.get("lane") != "direct_vla" or "vla" not in sources or "vlm" in sources:
            errors.append(f"{name}:direct_source_boundary_broken")
        if any(event.get("assistance") != {"used": False, "source": "none"} for event in stream.get("events", [])):
            errors.append(f"{name}:unexpected_assistance")

    for name in ("vlm_pass", "vlm_fail"):
        stream = streams[name]
        sources = {event.get("source") for event in stream.get("events", [])}
        if stream.get("lane") != "vlm_skill" or "vlm" not in sources or "vla" in sources:
            errors.append(f"{name}:vlm_source_boundary_broken")
        for event in stream.get("events", []):
            if event.get("source") in {"controller", "environment"} and event.get("assistance") != {"used": True, "source": "scripted_skill"}:
                errors.append(f"{name}:{event.get('id')}:scripted_assistance_missing")
        outcome = _environment_outcome(stream)
        if outcome.get("measured") is not True:
            errors.append(f"{name}:outcome_not_measured")

    expected_outcomes = {
        "direct_pass": (True, "success"),
        "direct_fail": (False, "timeout"),
        "vlm_pass": (True, "success"),
        "vlm_fail": (False, "timeout"),
    }
    outcomes: dict[str, dict[str, Any]] = {}
    for name, expected in expected_outcomes.items():
        outcome = _environment_outcome(streams[name])
        outcomes[name] = outcome
        if (outcome.get("success"), outcome.get("termination")) != expected:
            errors.append(f"{name}:outcome_drift")

    direct_revisions = _component_revisions(streams["direct_pass"], "vla") | _component_revisions(streams["direct_fail"], "vla")
    vlm_revisions = _component_revisions(streams["vlm_pass"], "vlm") | _component_revisions(streams["vlm_fail"], "vlm")
    if len(direct_revisions) != 1:
        errors.append("direct_vla_revision_drift")
    if len(vlm_revisions) != 1:
        errors.append("vlm_revision_drift")
    episode_revisions = {stream.get("episode_ref", {}).get("dataset_revision") for stream in streams.values()}
    if len(episode_revisions) != 1:
        errors.append("dataset_revision_drift")

    hashes = {name: _sha256(path) for name, path in paths.items()} if paths else {}
    return {
        "pass": not errors,
        "errors": errors,
        "schema": {name: report["valid"] for name, report in schema_reports.items()},
        "outcomes": outcomes,
        "provenance": {
            "direct_vla": [list(item) for item in sorted(direct_revisions)],
            "vlm": [list(item) for item in sorted(vlm_revisions)],
            "dataset_revision": next(iter(episode_revisions)) if len(episode_revisions) == 1 else None,
            "direct_assistance": "none",
            "vlm_controller_assistance": "scripted_skill",
        },
        "event_counts": {name: len(stream["events"]) for name, stream in streams.items()},
        "artifact_sha256": hashes,
        "claim_boundary": "recorded LIBERO simulation: direct OpenVLA actions versus auxiliary Qwen3-VL skill selection plus scripted controller",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    for name in STREAM_NAMES:
        parser.add_argument(f"--{name.replace('_', '-')}", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    paths = {name: getattr(args, name) for name in STREAM_NAMES}
    streams = {name: json.loads(path.read_text(encoding="utf-8")) for name, path in paths.items()}
    report = evaluate_two_lane(streams, paths)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
