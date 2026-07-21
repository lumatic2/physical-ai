#!/usr/bin/env python3
"""Verify observable failure taxonomy and record schema."""

from __future__ import annotations

import argparse
import copy
import json
import re
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

HERE = Path(__file__).resolve().parent
SCHEMA_PATH = HERE / "failure-pattern-schema.json"
FIXTURES_PATH = HERE / "fixtures" / "invalid-pattern-contract.json"
OUTPUT = HERE / "verify" / "failure-pattern-contract-report.json"

EXPECTED_LABELS = {
    "no_progress",
    "wrong_object_interaction",
    "grasp_lost",
    "timeout_near_goal",
    "controller_rejected",
    "infrastructure_error",
    "unknown",
    "multiple",
}
CAUSAL_LANGUAGE = re.compile(
    r"(?i)(bad reasoning|did not understand|hidden reasoning|root cause|perception failure|planning failure|원인|이해 실패)"
)
CLAIM_BOUNDARY = "Observed failure pattern only; not a root-cause, hidden-reasoning, or real-robot diagnosis."


class ContractError(ValueError):
    """Raised when taxonomy language or schema permits unsupported diagnosis."""


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def set_path(value: dict[str, Any], path: str, replacement: Any) -> None:
    target: Any = value
    parts = path.split(".")
    for part in parts[:-1]:
        target = target[part]
    target[parts[-1]] = replacement


def base_record(pattern_id: str = "no_progress") -> dict[str, Any]:
    record = {
        "schema_version": "physical-ai-failure-pattern-record-v1",
        "run_key": "v1:fixture:timeout",
        "policy_id": "openvla-libero",
        "outcome": "timeout",
        "pattern_id": pattern_id,
        "rule_version": "gen4-rules-v1",
        "frame_range": {"start": 0, "end": 219},
        "predicates": [
            {
                "metric": "end_effector_displacement",
                "operator": "lt",
                "observed": 0.01,
                "threshold": 0.02,
                "unit": "meter",
                "source": {
                    "kind": "trajectory",
                    "ref": "episodes/fixture/trajectory.parquet",
                    "sha256": "a" * 64,
                    "frame_range": {"start": 0, "end": 219}
                }
            }
        ],
        "evidence": {
            "episode_ref": "episodes/fixture",
            "manifest_sha256": "b" * 64,
            "sources": [
                {
                    "kind": "episode-manifest",
                    "ref": "episodes/fixture/episode-manifest.json",
                    "sha256": "b" * 64
                }
            ]
        },
        "claim_boundary": CLAIM_BOUNDARY
    }
    if pattern_id == "unknown":
        record["unknown_reason"] = "no-declared-predicate-matched"
    if pattern_id == "multiple":
        record["components"] = ["no_progress", "grasp_lost"]
    if pattern_id == "infrastructure_error":
        record["policy_id"] = "infrastructure"
        record["outcome"] = "error"
    return record


def validate_record(schema: dict[str, Any], record: dict[str, Any]) -> None:
    errors = list(Draft202012Validator(schema).iter_errors(record))
    if errors:
        raise ContractError(f"record schema: {errors[0].message}")
    ranges = [record["frame_range"]]
    for predicate in record.get("predicates", []):
        if "frame_range" in predicate.get("source", {}):
            ranges.append(predicate["source"]["frame_range"])
    for source in record.get("evidence", {}).get("sources", []):
        if "frame_range" in source:
            ranges.append(source["frame_range"])
    if any(item["start"] > item["end"] for item in ranges):
        raise ContractError("frame range start exceeds end")


def validate_contract(schema: dict[str, Any], fixtures: dict[str, Any]) -> dict[str, Any]:
    definitions = schema.get("x-pattern-definitions", [])
    by_id = {item.get("id"): item for item in definitions}
    if set(by_id) != EXPECTED_LABELS or len(by_id) != len(definitions):
        raise ContractError("taxonomy labels are missing or duplicated")
    if by_id["infrastructure_error"].get("scope") != "attempt":
        raise ContractError("infrastructure_error must remain attempt-scoped")
    if any(
        item.get("scope") != "policy-episode"
        for label, item in by_id.items()
        if label != "infrastructure_error"
    ):
        raise ContractError("policy pattern scope drift")
    for label, item in by_id.items():
        text = f"{label} {item.get('description', '')}"
        if CAUSAL_LANGUAGE.search(text):
            raise ContractError(f"unsupported causal taxonomy language: {label}")
        if not item.get("required_predicates") or not item.get("evidence_sources"):
            raise ContractError(f"pattern lacks observable contract: {label}")
    required = set(schema.get("required", []))
    expected_required = {"pattern_id", "frame_range", "predicates", "evidence", "claim_boundary"}
    if not expected_required.issubset(required):
        raise ContractError("record schema does not require evidence boundary")
    for label in sorted(EXPECTED_LABELS):
        try:
            validate_record(schema, base_record(label))
        except ContractError as exc:
            raise ContractError(f"valid {label} fixture rejected: {exc}") from exc
    rejected = []
    for fixture in fixtures.get("cases", []):
        mutation = copy.deepcopy(base_record())
        set_path(mutation, fixture["path"], fixture["value"])
        try:
            validate_record(schema, mutation)
        except ContractError:
            pass
        else:
            raise ContractError(f"invalid fixture accepted: {fixture['id']}")
        rejected.append(fixture["id"])
    return {
        "schema_version": "physical-ai-gen4-failure-pattern-contract-report-v1",
        "pass": True,
        "labels": sorted(EXPECTED_LABELS),
        "policy_episode_labels": sorted(EXPECTED_LABELS - {"infrastructure_error"}),
        "attempt_labels": ["infrastructure_error"],
        "definitions_with_predicates": len(definitions),
        "definitions_with_evidence_sources": len(definitions),
        "valid_label_fixtures": len(EXPECTED_LABELS),
        "negative_fixtures_rejected": rejected,
        "claim_boundary": CLAIM_BOUNDARY,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schema", type=Path, default=SCHEMA_PATH)
    parser.add_argument("--fixtures", type=Path, default=FIXTURES_PATH)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    try:
        report = validate_contract(load_json(args.schema), load_json(args.fixtures))
    except (ContractError, FileNotFoundError, KeyError, TypeError, ValueError) as exc:
        print(f"failure pattern contract: FAIL — {exc}")
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        "failure pattern contract: PASS "
        f"(labels={len(report['labels'])}, negative={len(report['negative_fixtures_rejected'])})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
