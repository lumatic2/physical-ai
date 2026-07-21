#!/usr/bin/env python3
"""Build and verify a deterministic, stratified failure-pattern review packet."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from classify_patterns import OUTPUT as PATTERN_INDEX
from classify_patterns import canonical_hash
from extract_features import OUTPUT as FEATURE_INDEX

HERE = Path(__file__).resolve().parent
PACKET_PATH = HERE / "verify" / "review" / "reviewer-packet.json"
DECISIONS_PATH = HERE / "reviewer-decisions.json"
REPORT_PATH = HERE / "verify" / "reviewer-report.json"
PACKET_VERSION = "physical-ai-gen4-reviewer-packet-v1"
REPORT_VERSION = "physical-ai-gen4-reviewer-report-v1"
REVIEW_KIND = "manual-evidence-review-not-independent-human"
CLAIM_BOUNDARY = (
    "Calibration checks observable predicates and source alignment; it is not an independent-human, "
    "root-cause, hidden-reasoning, or real-robot review."
)


class ReviewError(ValueError):
    """Raised when reviewer sampling or audit evidence loses coverage."""


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def stratum(record: dict[str, Any], feature: dict[str, Any]) -> tuple[str, str, str]:
    return record["policy_id"], feature["suite"], record["pattern_id"]


def predicate_check(record: dict[str, Any], feature: dict[str, Any]) -> dict[str, Any]:
    pattern_id = record["pattern_id"]
    final_displacement = feature["eef_trajectory"]["final_window_displacement"]
    rejected = feature["controller_events"]["rejected_count"]
    if pattern_id == "no_progress":
        matched = final_displacement < 0.01
        detail = f"terminal eef displacement {final_displacement:.9f} m < 0.010000000 m"
    elif pattern_id == "unknown":
        matched = final_displacement >= 0.01 and rejected == 0
        detail = (
            f"active rules unmatched: terminal eef displacement {final_displacement:.9f} m >= "
            f"0.010000000 m; rejected controller events={rejected}"
        )
    else:
        raise ReviewError(f"review packet encountered unsupported actual label: {pattern_id}")
    return {
        "matches_record": matched,
        "detail": detail,
        "active_rule_inputs": {
            "final_window_eef_displacement_m": final_displacement,
            "controller_rejected_count": rejected,
        },
    }


def build_packet(feature_index: dict[str, Any], pattern_index: dict[str, Any]) -> dict[str, Any]:
    features = {row["run_key"]: row for row in feature_index["features"]}
    records = pattern_index["records"]
    if len(features) != 27 or len(records) != 27 or set(features) != {row["run_key"] for row in records}:
        raise ReviewError("review source denominator mismatch")
    grouped: dict[tuple[str, str, str], list[tuple[dict[str, Any], dict[str, Any]]]] = {}
    for record in records:
        feature = features[record["run_key"]]
        grouped.setdefault(stratum(record, feature), []).append((record, feature))
    samples = []
    for key, rows in sorted(grouped.items()):
        record, feature = min(rows, key=lambda pair: pair[0]["run_key"])
        cameras = {source["role"]: source for source in feature["camera_evidence"]}
        samples.append(
            {
                "sample_id": f"review-{len(samples) + 1:02d}",
                "run_key": record["run_key"],
                "policy_id": key[0],
                "suite": key[1],
                "pattern_id": key[2],
                "outcome": record["outcome"],
                "stratum_population": len(rows),
                "episode_ref": feature["episode_ref"],
                "frame_range": feature["frame_range"],
                "predicate_check": predicate_check(record, feature),
                "source_checklist": {
                    "main_camera": cameras["main"],
                    "wrist_camera": cameras["wrist"],
                    "event_stream": feature["sources"]["event"],
                    "trajectory": feature["sources"]["trajectory"],
                    "controller_event_count": feature["controller_events"]["acceptance_event_count"],
                },
            }
        )
    packet = {
        "schema_version": PACKET_VERSION,
        "sampling_rule": "one lexicographically-first run_key per observed policy/suite/label stratum",
        "source_denominator": 27,
        "sample_count": len(samples),
        "observed_strata": ["/".join(key) for key in sorted(grouped)],
        "source_hashes": {
            "feature_index": canonical_hash(feature_index),
            "pattern_index": canonical_hash(pattern_index),
        },
        "samples": samples,
        "claim_boundary": CLAIM_BOUNDARY,
    }
    validate_packet(packet, feature_index, pattern_index)
    return packet


def validate_packet(
    packet: dict[str, Any], feature_index: dict[str, Any], pattern_index: dict[str, Any]
) -> None:
    if packet.get("schema_version") != PACKET_VERSION or packet.get("source_denominator") != 27:
        raise ReviewError("review packet version or denominator drift")
    samples = packet.get("samples", [])
    if packet.get("sample_count") != len(samples) or not samples:
        raise ReviewError("review sample count drift")
    if any(sample.get("outcome") != "timeout" for sample in samples):
        raise ReviewError("review packet must sample non-success episodes only")
    if "unknown" not in {sample.get("pattern_id") for sample in samples}:
        raise ReviewError("unknown label excluded from reviewer sample")
    if {sample.get("policy_id") for sample in samples} != {"openvla-libero", "pi05-libero"}:
        raise ReviewError("policy stratification incomplete")
    if {sample.get("suite") for sample in samples} != {"libero_goal", "libero_object", "libero_spatial"}:
        raise ReviewError("suite stratification incomplete")
    features = {row["run_key"]: row for row in feature_index["features"]}
    records = {row["run_key"]: row for row in pattern_index["records"]}
    expected_groups: dict[tuple[str, str, str], list[str]] = {}
    for run_key, record in records.items():
        key = stratum(record, features[run_key])
        expected_groups.setdefault(key, []).append(run_key)
    expected = {key: min(keys) for key, keys in expected_groups.items()}
    actual: dict[tuple[str, str, str], str] = {}
    for sample in samples:
        key = (sample["policy_id"], sample["suite"], sample["pattern_id"])
        if key in actual:
            raise ReviewError("duplicate review stratum")
        actual[key] = sample["run_key"]
        if sample.get("stratum_population") != len(expected_groups.get(key, [])):
            raise ReviewError("stratum population drift")
        if sample.get("predicate_check", {}).get("matches_record") is not True:
            raise ReviewError("sample predicate does not support record")
        checklist = sample.get("source_checklist", {})
        if set(checklist) != {
            "main_camera",
            "wrist_camera",
            "event_stream",
            "trajectory",
            "controller_event_count",
        }:
            raise ReviewError("camera/event checklist incomplete")
    if actual != expected:
        raise ReviewError("review sample is not deterministic or strata-complete")
    hashes = packet.get("source_hashes", {})
    if hashes != {
        "feature_index": canonical_hash(feature_index),
        "pattern_index": canonical_hash(pattern_index),
    }:
        raise ReviewError("review source hash drift")
    if packet.get("claim_boundary") != CLAIM_BOUNDARY:
        raise ReviewError("review claim boundary drift")


def build_report(packet: dict[str, Any], decisions: dict[str, Any]) -> dict[str, Any]:
    if decisions.get("schema_version") != "physical-ai-gen4-reviewer-decisions-v1":
        raise ReviewError("review decision version drift")
    if decisions.get("claim_boundary") != CLAIM_BOUNDARY:
        raise ReviewError("review decision claim boundary drift")
    rows = decisions.get("decisions", [])
    by_id = {row.get("sample_id"): row for row in rows}
    if len(by_id) != len(rows) or set(by_id) != {sample["sample_id"] for sample in packet["samples"]}:
        raise ReviewError("review decisions must cover every sample exactly once")
    reviewed = []
    for sample in packet["samples"]:
        decision = by_id[sample["sample_id"]]
        if decision.get("review_kind") != REVIEW_KIND or not decision.get("reviewer_id"):
            raise ReviewError("review identity or independence disclosure missing")
        source_checks = decision.get("source_checks", {})
        if source_checks != {"main_camera_observed": True, "wrist_camera_observed": True, "event_source_observed": True}:
            raise ReviewError("manual camera/event source check incomplete")
        frame_range = sample["frame_range"]
        expected_frames = [frame_range["start"], (frame_range["start"] + frame_range["end"]) // 2, frame_range["end"]]
        if decision.get("reviewed_frame_indices") != expected_frames:
            raise ReviewError("manual review frame indices incomplete")
        reviewed_pattern = decision.get("reviewed_pattern_id")
        agrees = reviewed_pattern == sample["pattern_id"]
        disagreement = decision.get("disagreement")
        if not agrees:
            if not isinstance(disagreement, dict) or not disagreement.get("reason") or not disagreement.get("evidence_ref"):
                raise ReviewError("reviewer override is missing an auditable disagreement")
        elif disagreement is not None:
            raise ReviewError("agreement row must not fabricate disagreement")
        if not decision.get("reviewer_note"):
            raise ReviewError("reviewer note missing")
        reviewed.append(
            {
                "sample_id": sample["sample_id"],
                "run_key": sample["run_key"],
                "machine_pattern_id": sample["pattern_id"],
                "reviewed_pattern_id": reviewed_pattern,
                "agrees": agrees,
                "source_checks": source_checks,
                "reviewer_note": decision["reviewer_note"],
                "disagreement": disagreement,
            }
        )
    agrees = sum(row["agrees"] for row in reviewed)
    report = {
        "schema_version": REPORT_VERSION,
        "pass": agrees == len(reviewed),
        "review_kind": REVIEW_KIND,
        "sample_count": len(reviewed),
        "agreement": {"agreed": agrees, "disagreed": len(reviewed) - agrees, "rate": agrees / len(reviewed)},
        "label_counts": dict(sorted(Counter(row["machine_pattern_id"] for row in reviewed).items())),
        "reviewed": reviewed,
        "packet_sha256": canonical_hash(packet),
        "claim_boundary": CLAIM_BOUNDARY,
    }
    validate_report(report, packet)
    return report


def validate_report(report: dict[str, Any], packet: dict[str, Any]) -> None:
    if report.get("schema_version") != REPORT_VERSION or report.get("sample_count") != packet["sample_count"]:
        raise ReviewError("review report version or sample count drift")
    if report.get("packet_sha256") != canonical_hash(packet):
        raise ReviewError("review packet hash drift")
    reviewed = report.get("reviewed", [])
    counts = Counter(row.get("machine_pattern_id") for row in reviewed)
    if counts.get("unknown", 0) == 0 or report.get("label_counts") != dict(sorted(counts.items())):
        raise ReviewError("review report hides unknown labels")
    agreement = report.get("agreement", {})
    agreed = sum(row.get("agrees") is True for row in reviewed)
    if agreement != {"agreed": agreed, "disagreed": len(reviewed) - agreed, "rate": agreed / len(reviewed)}:
        raise ReviewError("agreement summary drift")
    if report.get("pass") is not (agreed == len(reviewed)):
        raise ReviewError("review pass drift")
    if report.get("claim_boundary") != CLAIM_BOUNDARY:
        raise ReviewError("review report claim boundary drift")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--features", type=Path, default=FEATURE_INDEX)
    parser.add_argument("--patterns", type=Path, default=PATTERN_INDEX)
    parser.add_argument("--decisions", type=Path, default=DECISIONS_PATH)
    parser.add_argument("--packet-output", type=Path, default=PACKET_PATH)
    parser.add_argument("--report-output", type=Path, default=REPORT_PATH)
    parser.add_argument("--packet-only", action="store_true")
    args = parser.parse_args()
    features = load_json(args.features)
    patterns = load_json(args.patterns)
    packet = build_packet(features, patterns)
    dump_json(args.packet_output, packet)
    if args.packet_only:
        print(f"reviewer packet: PASS (strata={packet['sample_count']}, unknown=included)")
        return 0
    report = build_report(packet, load_json(args.decisions))
    dump_json(args.report_output, report)
    print(
        "reviewer calibration: "
        f"{'PASS' if report['pass'] else 'FAIL'} "
        f"(sample={report['sample_count']}, agreement={report['agreement']['agreed']}/{report['sample_count']})"
    )
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
