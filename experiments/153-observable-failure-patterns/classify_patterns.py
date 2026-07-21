#!/usr/bin/env python3
"""Classify failure features with order-independent observable rules."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from extract_features import OUTPUT as FEATURE_INDEX  # noqa: E402
from extract_features import (  # noqa: E402
    sha256_file,
    validate_feature_index,
)
from verify_contract import (  # noqa: E402
    CLAIM_BOUNDARY,
    SCHEMA_PATH,
    load_json,
    validate_record,
)

RULES_PATH = HERE / "classification-rules-v1.json"
OUTPUT = HERE / "verify" / "patterns" / "failure-pattern-index.json"
INDEX_VERSION = "physical-ai-gen4-failure-pattern-index-v1"
SUPPORTED_ACTIVE = {"no_progress", "controller_rejected"}
SUPPORTED_INACTIVE = {"wrong_object_interaction", "grasp_lost", "timeout_near_goal"}
CLASSIFIER_BOUNDARY = "Observed failure pattern only; not a root-cause, hidden-reasoning, or real-robot diagnosis."


class ClassifierError(ValueError):
    """Raised when a rule or output loses deterministic evidence support."""


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def nested(value: dict[str, Any], path: str) -> Any:
    target: Any = value
    for part in path.split("."):
        target = target[part]
    return target


def clean_source(source: dict[str, Any], *, frame_range: dict[str, int] | None = None) -> dict[str, Any]:
    result = {key: source[key] for key in ("kind", "ref", "sha256")}
    if frame_range is not None:
        result["frame_range"] = frame_range
    if source.get("event_ids"):
        result["event_ids"] = source["event_ids"]
    return result


def manifest_source(feature: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": "episode-manifest",
        "ref": f"{feature['episode_ref']}/episode-manifest.json",
        "sha256": feature["manifest_sha256"],
    }


def evaluate_rule(feature: dict[str, Any], rule: dict[str, Any]) -> dict[str, Any] | None:
    pattern_id = rule.get("pattern_id")
    if pattern_id not in SUPPORTED_ACTIVE:
        raise ClassifierError(f"unsupported causal or unavailable active label: {pattern_id}")
    value = nested(feature, rule["feature"])
    threshold = rule["threshold"]
    operator = rule["operator"]
    matched = (operator == "lt" and value < threshold) or (operator == "gt" and value > threshold)
    if operator not in {"lt", "gt"}:
        raise ClassifierError(f"unsupported operator: {operator}")
    if not matched:
        return None
    if pattern_id == "no_progress":
        source = feature.get("sources", {}).get("trajectory")
        if not source:
            raise ClassifierError("missing pointer for no_progress")
        frame_range = {
            "start": feature["eef_trajectory"]["final_window_start_frame"],
            "end": feature["frame_range"]["end"],
        }
        predicate = {
            "metric": "end_effector_displacement",
            "operator": "lt",
            "observed": value,
            "threshold": threshold,
            "unit": rule["unit"],
            "source": clean_source(source, frame_range=frame_range),
        }
    else:
        source = feature.get("sources", {}).get("event")
        event_ids = feature.get("controller_events", {}).get("rejected_event_ids", [])
        if not source or not event_ids:
            raise ClassifierError("missing pointer for controller_rejected")
        source = {**source, "event_ids": event_ids}
        predicate = {
            "metric": "controller_acceptance",
            "operator": "is_false",
            "observed": False,
            "threshold": False,
            "unit": "boolean",
            "source": clean_source(source),
        }
        frame_range = copy.deepcopy(feature["frame_range"])
        frame_range.pop("count", None)
    return {"pattern_id": pattern_id, "predicate": predicate, "frame_range": frame_range}


def evidence_sources(feature: dict[str, Any], matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sources = [manifest_source(feature)]
    if matches:
        sources.extend(match["predicate"]["source"] for match in matches)
    else:
        sources.extend(clean_source(source) for source in feature["sources"].values())
        sources.extend(clean_source(source) for source in feature["camera_evidence"])
    unique = {source["ref"]: source for source in sources}
    return [unique[key] for key in sorted(unique)]


def classify_feature(feature: dict[str, Any], rules: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    active = [rule for rule in rules.get("rules", []) if rule.get("enabled") is True]
    inactive = [rule for rule in rules.get("rules", []) if rule.get("enabled") is False]
    if {rule.get("pattern_id") for rule in inactive} != SUPPORTED_INACTIVE:
        raise ClassifierError("inactive availability disclosure drift")
    matches = [result for rule in active if (result := evaluate_rule(feature, rule)) is not None]
    matches.sort(key=lambda item: item["pattern_id"])
    whole_range = {"start": feature["frame_range"]["start"], "end": feature["frame_range"]["end"]}
    record = {
        "schema_version": "physical-ai-failure-pattern-record-v1",
        "run_key": feature["run_key"],
        "policy_id": feature["policy_id"],
        "outcome": feature["outcome"],
        "pattern_id": "unknown",
        "rule_version": rules["rule_version"],
        "frame_range": whole_range,
        "predicates": [],
        "evidence": {
            "episode_ref": feature["episode_ref"],
            "manifest_sha256": feature["manifest_sha256"],
            "sources": evidence_sources(feature, matches),
        },
        "claim_boundary": CLASSIFIER_BOUNDARY,
    }
    if not matches:
        record["unknown_reason"] = "no-declared-predicate-matched"
        record["predicates"] = [
            {
                "metric": "declared_pattern_match_count",
                "operator": "eq",
                "observed": 0,
                "threshold": 0,
                "unit": "count",
                "source": manifest_source(feature),
            }
        ]
    elif len(matches) == 1:
        record["pattern_id"] = matches[0]["pattern_id"]
        record["frame_range"] = matches[0]["frame_range"]
        record["predicates"] = [matches[0]["predicate"]]
    else:
        record["pattern_id"] = "multiple"
        record["components"] = [match["pattern_id"] for match in matches]
        record["predicates"] = [match["predicate"] for match in matches]
        record["predicates"].append(
            {
                "metric": "declared_pattern_match_count",
                "operator": "gte",
                "observed": len(matches),
                "threshold": 2,
                "unit": "count",
                "source": manifest_source(feature),
            }
        )
    try:
        validate_record(schema, record)
    except ValueError as exc:
        raise ClassifierError(f"pattern record invalid: {exc}") from exc
    return record


def build_index(feature_report: dict[str, Any], rules: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    validate_feature_index(feature_report)
    if rules.get("rule_version") != "gen4-rules-v1":
        raise ClassifierError("rule version drift")
    records = [classify_feature(feature, rules, schema) for feature in feature_report["features"]]
    records.sort(key=lambda row: row["run_key"])
    counts = Counter(record["pattern_id"] for record in records)
    report = {
        "schema_version": INDEX_VERSION,
        "pass": True,
        "rule_version": rules["rule_version"],
        "denominator": len(records),
        "counts": dict(sorted(counts.items())),
        "records_sha256": canonical_hash(records),
        "records": records,
        "inputs": {
            "features_sha256": canonical_hash(feature_report),
            "rules_sha256": canonical_hash(rules),
            "record_schema_sha256": canonical_hash(schema),
        },
        "disabled_patterns": {
            rule["pattern_id"]: rule["unavailable_reason"]
            for rule in sorted(rules["rules"], key=lambda item: item["pattern_id"])
            if rule.get("enabled") is False
        },
        "claim_boundary": "Deterministic observable pattern index; unknown is preserved and no pattern is a root cause.",
    }
    validate_index(report, feature_report, schema)
    return report


def validate_index(report: dict[str, Any], feature_report: dict[str, Any], schema: dict[str, Any]) -> None:
    records = report.get("records", [])
    if report.get("denominator") != 27 or len(records) != 27:
        raise ClassifierError("pattern denominator mismatch")
    if len({record.get("run_key") for record in records}) != 27:
        raise ClassifierError("duplicate pattern record")
    feature_by_key = {feature["run_key"]: feature for feature in feature_report["features"]}
    if set(feature_by_key) != {record["run_key"] for record in records}:
        raise ClassifierError("feature/pattern key mismatch")
    for record in records:
        try:
            validate_record(schema, record)
        except ValueError as exc:
            raise ClassifierError(f"pattern schema failure: {exc}") from exc
        feature = feature_by_key[record["run_key"]]
        allowed_refs = {
            f"{feature['episode_ref']}/episode-manifest.json",
            *(source["ref"] for source in feature["sources"].values()),
            *(source["ref"] for source in feature["camera_evidence"]),
        }
        used_refs = {source["ref"] for source in record["evidence"]["sources"]}
        used_refs.update(predicate["source"]["ref"] for predicate in record["predicates"])
        if not used_refs.issubset(allowed_refs):
            raise ClassifierError("missing or invented evidence pointer")
        if record["claim_boundary"] != CLAIM_BOUNDARY:
            raise ClassifierError("claim boundary drift")
    expected_counts = dict(sorted(Counter(record["pattern_id"] for record in records).items()))
    if report.get("counts") != expected_counts:
        raise ClassifierError("pattern count drift")
    if report.get("records_sha256") != canonical_hash(records):
        raise ClassifierError("deterministic record hash drift")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--features", type=Path, default=FEATURE_INDEX)
    parser.add_argument("--rules", type=Path, default=RULES_PATH)
    parser.add_argument("--schema", type=Path, default=SCHEMA_PATH)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    try:
        report = build_index(load_json(args.features), load_json(args.rules), load_json(args.schema))
    except (ClassifierError, FileNotFoundError, KeyError, TypeError, ValueError) as exc:
        print(f"deterministic failure classifier: FAIL — {exc}")
        return 2
    report["sources"] = {
        "features": {"ref": str(args.features.relative_to(REPO_ROOT)).replace("\\", "/"), "sha256": sha256_file(args.features)},
        "rules": {"ref": str(args.rules.relative_to(REPO_ROOT)).replace("\\", "/"), "sha256": sha256_file(args.rules)},
        "record_schema": {"ref": str(args.schema.relative_to(REPO_ROOT)).replace("\\", "/"), "sha256": sha256_file(args.schema)},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        "deterministic failure classifier: PASS "
        f"(denominator={report['denominator']}, counts={json.dumps(report['counts'], sort_keys=True)})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
