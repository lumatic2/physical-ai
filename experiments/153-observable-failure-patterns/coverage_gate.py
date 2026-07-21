#!/usr/bin/env python3
"""Aggregate all GEN4 non-success records and enforce negative claim boundaries."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from classify_patterns import OUTPUT as PATTERN_INDEX
from classify_patterns import canonical_hash
from extract_features import OUTPUT as FEATURE_INDEX
from reviewer_calibration import REPORT_PATH as REVIEWER_REPORT

HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "verify" / "failure-coverage-report.json"
REPORT_VERSION = "physical-ai-gen4-failure-coverage-v1"
CLAIM_BOUNDARY = (
    "Counts describe observed simulator failure patterns only; they do not establish root cause, "
    "hidden reasoning, model diagnosis, independent-human agreement, or real-robot performance."
)
FORBIDDEN_SUPPORTED_CLAIMS = (
    "root cause",
    "caused by",
    "model did not understand",
    "perception failure",
    "planning failure",
    "real robot",
    "independent human",
)


class CoverageError(ValueError):
    """Raised when failure coverage or its public claim boundary drifts."""


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def validate_supported_claim(text: str) -> None:
    lowered = text.lower()
    matched = [phrase for phrase in FORBIDDEN_SUPPORTED_CLAIMS if phrase in lowered]
    if matched:
        raise CoverageError(f"supported claim crosses evidence boundary: {matched[0]}")


def nested_counts(rows: list[dict[str, str]], keys: tuple[str, ...]) -> dict[str, Any]:
    if len(keys) == 1:
        return dict(sorted(Counter(row[keys[0]] for row in rows).items()))
    result: dict[str, Any] = {}
    for value in sorted({row[keys[0]] for row in rows}):
        result[value] = nested_counts([row for row in rows if row[keys[0]] == value], keys[1:])
    return result


def summarize(feature_index: dict[str, Any], pattern_index: dict[str, Any]) -> tuple[list[dict[str, str]], dict[str, Any]]:
    features = {row["run_key"]: row for row in feature_index["features"]}
    records = pattern_index["records"]
    if len(features) != 27 or len(records) != 27 or set(features) != {row["run_key"] for row in records}:
        raise CoverageError("canonical non-success denominator mismatch")
    rows = []
    for record in records:
        feature = features[record["run_key"]]
        if record["outcome"] != "timeout" or not record.get("predicates") or not record.get("evidence", {}).get("sources"):
            raise CoverageError("record lacks evidence-backed non-success coverage")
        rows.append(
            {
                "run_key": record["run_key"],
                "policy_id": record["policy_id"],
                "suite": feature["suite"],
                "pattern_id": record["pattern_id"],
            }
        )
    rows.sort(key=lambda row: row["run_key"])
    counts = Counter(row["pattern_id"] for row in rows)
    summary = {
        "total": len(rows),
        "by_pattern": dict(sorted(counts.items())),
        "by_policy": nested_counts(rows, ("policy_id", "pattern_id")),
        "by_suite": nested_counts(rows, ("suite", "pattern_id")),
        "by_policy_suite": nested_counts(rows, ("policy_id", "suite", "pattern_id")),
    }
    return rows, summary


def build_report(
    feature_index: dict[str, Any], pattern_index: dict[str, Any], reviewer_report: dict[str, Any]
) -> dict[str, Any]:
    rows, summary = summarize(feature_index, pattern_index)
    specific = summary["by_pattern"].get("no_progress", 0)
    unknown = summary["by_pattern"].get("unknown", 0)
    supported_claims = [
        "All 27 canonical simulator non-success episodes have an evidence-backed observed pattern record or unknown.",
        "Observed counts are no_progress 6 and unknown 21 under gen4-rules-v1.",
        "Unknown is 21/27 because the available sources do not justify a more specific declared pattern.",
    ]
    for claim in supported_claims:
        validate_supported_claim(claim)
    report = {
        "schema_version": REPORT_VERSION,
        "pass": True,
        "denominator": {"non_success": 27, "indexed": len(rows), "omitted": 27 - len(rows)},
        "coverage": {
            "evidence_backed_or_unknown": len(rows),
            "rate": len(rows) / 27,
            "specific_pattern": specific,
            "specific_pattern_rate": specific / 27,
            "unknown": unknown,
            "unknown_rate": unknown / 27,
        },
        "breakdown": summary,
        "source_availability": feature_index["availability"],
        "reviewer_calibration": {
            "pass": reviewer_report["pass"],
            "review_kind": reviewer_report["review_kind"],
            "sample_count": reviewer_report["sample_count"],
            "agreement": reviewer_report["agreement"],
            "report_sha256": canonical_hash(reviewer_report),
        },
        "claims": {
            "supported": supported_claims,
            "not_established": [
                "A root cause for any episode.",
                "A perception, planning, or language-understanding diagnosis.",
                "Independent-human agreement or real-robot performance.",
            ],
        },
        "inputs": {
            "feature_index_sha256": canonical_hash(feature_index),
            "pattern_index_sha256": canonical_hash(pattern_index),
            "reviewer_report_sha256": canonical_hash(reviewer_report),
        },
        "covered_run_keys_sha256": canonical_hash([row["run_key"] for row in rows]),
        "claim_boundary": CLAIM_BOUNDARY,
    }
    validate_report(report, feature_index, pattern_index, reviewer_report)
    return report


def validate_report(
    report: dict[str, Any],
    feature_index: dict[str, Any],
    pattern_index: dict[str, Any],
    reviewer_report: dict[str, Any],
) -> None:
    if report.get("schema_version") != REPORT_VERSION:
        raise CoverageError("coverage report version drift")
    rows, expected = summarize(feature_index, pattern_index)
    denominator = report.get("denominator", {})
    if denominator != {"non_success": 27, "indexed": 27, "omitted": 0}:
        raise CoverageError("coverage denominator omission")
    if report.get("breakdown") != expected:
        raise CoverageError("coverage breakdown drift or unknown hidden")
    coverage = report.get("coverage", {})
    if coverage != {
        "evidence_backed_or_unknown": 27,
        "rate": 1.0,
        "specific_pattern": 6,
        "specific_pattern_rate": 6 / 27,
        "unknown": 21,
        "unknown_rate": 21 / 27,
    }:
        raise CoverageError("unknown or evidence coverage drift")
    if report.get("covered_run_keys_sha256") != canonical_hash([row["run_key"] for row in rows]):
        raise CoverageError("covered run key drift")
    reviewer = report.get("reviewer_calibration", {})
    if reviewer != {
        "pass": True,
        "review_kind": "manual-evidence-review-not-independent-human",
        "sample_count": 7,
        "agreement": {"agreed": 7, "disagreed": 0, "rate": 1.0},
        "report_sha256": canonical_hash(reviewer_report),
    }:
        raise CoverageError("reviewer calibration drift")
    for claim in report.get("claims", {}).get("supported", []):
        validate_supported_claim(claim)
    if len(report.get("claims", {}).get("not_established", [])) != 3:
        raise CoverageError("negative claim disclosure missing")
    if report.get("claim_boundary") != CLAIM_BOUNDARY:
        raise CoverageError("coverage claim boundary drift")
    if report.get("pass") is not True:
        raise CoverageError("coverage pass drift")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--features", type=Path, default=FEATURE_INDEX)
    parser.add_argument("--patterns", type=Path, default=PATTERN_INDEX)
    parser.add_argument("--reviewer", type=Path, default=REVIEWER_REPORT)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    report = build_report(load_json(args.features), load_json(args.patterns), load_json(args.reviewer))
    dump_json(args.output, report)
    print(
        "failure coverage gate: PASS "
        f"(indexed=27/27, no_progress={report['coverage']['specific_pattern']}, unknown={report['coverage']['unknown']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
