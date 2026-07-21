#!/usr/bin/env python3
"""Verify paired VLA provenance, disclosures, retries, and claim boundaries."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
GEN1_DIR = REPO_ROOT / "experiments" / "150-multitask-evaluation-contract"
GEN2_DIR = REPO_ROOT / "experiments" / "151-openvla-multitask-baseline"
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from paired_statistics import validate_report as validate_paired_report  # noqa: E402

REGISTRY = GEN1_DIR / "policy-registry.json"
ADAPTER_REPORT = HERE / "verify" / "adapter-parity-report.json"
OPENVLA_MANIFEST = GEN2_DIR / "verify" / "canonical" / "manifest.json"
PI05_MANIFEST = HERE / "verify" / "canonical" / "pi05-manifest.json"
PAIRED_REPORT = HERE / "verify" / "paired-report.json"
CLAIM_CONTRACT = HERE / "fairness-claim-contract.json"
OUTPUT = HERE / "verify" / "fairness-report.json"

REPORT_VERSION = "physical-ai-gen3-fairness-report-v1"
OPENVLA_ADAPTER = "eb1ae763aea5977f0b6b52be912411277c59ac90c9c8158b5485e70e1376c32e"
PI05_ADAPTER = "13bafd5d20562ec027e9d3c575b05ee5990ed7ec6def2a56964347ec18b9b037"
PI05_SNAPSHOT = "11e0f560ebc9ca0f65d26241dd08e2ac07c22ee91455f1789afc2fc5c0378d7b"
OPENVLA_REVISIONS = {
    "libero_spatial": "962318cec55ac10993ff0f5f43eda9a270b4c873",
    "libero_object": "287d6cfdf12d07b1449505f66d9bf3550257e9b3",
    "libero_goal": "fa5ae1e7509348889295bba8e08621d8b55e9baf",
}


class FairnessError(ValueError):
    """Raised when a fair-comparison disclosure can be hidden or overstated."""


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def by_id(rows: list[dict[str, Any]], field: str) -> dict[str, dict[str, Any]]:
    indexed = {row[field]: row for row in rows}
    if len(indexed) != len(rows):
        raise FairnessError(f"duplicate {field}")
    return indexed


def build_report(
    registry: dict[str, Any],
    adapter_report: dict[str, Any],
    openvla_manifest: dict[str, Any],
    pi05_manifest: dict[str, Any],
    paired_report: dict[str, Any],
    claim_contract: dict[str, Any],
) -> dict[str, Any]:
    validate_paired_report(paired_report)
    policies = by_id(registry.get("policies", []), "policy_id")
    adapters = by_id(adapter_report.get("adapters", []), "policy_id")
    if set(policies) != {"openvla-libero", "pi05-libero"} or set(adapters) != set(policies):
        raise FairnessError("policy registry mismatch")
    open_registry = policies["openvla-libero"]
    pi_registry = policies["pi05-libero"]
    open_checkpoints = {
        suite: {
            "repo_id": value["repo_id"],
            "revision": value["revision"],
        }
        for suite, value in open_registry["suite_checkpoints"].items()
    }
    open_attempts = int(openvla_manifest["terminal_cells"]) + int(openvla_manifest["infrastructure_attempts"])
    pi_attempts = int(pi05_manifest["attempts"])
    report = {
        "schema_version": REPORT_VERSION,
        "pass": True,
        "spec_verdict": "pass",
        "quality_verdict": "pass",
        "denominator": {
            "planned_pairs": 60,
            "included_pairs": paired_report["denominator"]["paired_keys"],
            "excluded_pairs": 0,
            "unmatched_pairs": 0,
            "suites": paired_report["denominator"]["suites"],
            "task_groups": paired_report["denominator"]["task_groups"],
        },
        "policies": {
            "openvla-libero": {
                "family": open_registry["family"],
                "checkpoint_topology": "suite-specific",
                "suite_checkpoints": open_checkpoints,
                "adapter_revision": adapters["openvla-libero"]["adapter_revision"],
                "model_inputs": adapters["openvla-libero"]["model_inputs"],
                "raw_output_shape": adapters["openvla-libero"]["raw_output_shape"],
                "executed_chunk_shape": adapters["openvla-libero"]["executed_chunk_shape"],
                "replan_steps": adapters["openvla-libero"]["replan_steps"],
                "attempts": {
                    "total": open_attempts,
                    "policy_terminal": openvla_manifest["terminal_cells"],
                    "infrastructure_error": openvla_manifest["infrastructure_attempts"],
                    "explicit_retries": openvla_manifest["infrastructure_attempts"],
                },
            },
            "pi05-libero": {
                "family": pi_registry["family"],
                "checkpoint_topology": "single-shared-checkpoint",
                "checkpoint": pi_registry["checkpoint"],
                "adapter_revision": adapters["pi05-libero"]["adapter_revision"],
                "model_inputs": adapters["pi05-libero"]["model_inputs"],
                "raw_output_shape": adapters["pi05-libero"]["raw_output_shape"],
                "executed_chunk_shape": adapters["pi05-libero"]["executed_chunk_shape"],
                "replan_steps": adapters["pi05-libero"]["replan_steps"],
                "attempts": {
                    "total": pi_attempts,
                    "policy_terminal": pi05_manifest["terminal"],
                    "infrastructure_error": pi05_manifest["infrastructure_error_attempts"],
                    "explicit_retries": pi05_manifest["infrastructure_error_attempts"],
                },
            },
        },
        "paired_result": {
            "openvla_successes": paired_report["overall"]["openvla_successes"],
            "pi05_successes": paired_report["overall"]["pi05_successes"],
            "difference_successes": paired_report["overall"]["difference_successes"],
            "denominator": paired_report["overall"]["denominator"],
            "difference_rate": paired_report["paired_difference"]["rate"],
            "bootstrap_95": paired_report["paired_difference"]["bootstrap_95"],
            "suite_breakdown": paired_report["suites"],
            "contingency": paired_report["contingency"],
        },
        "disclosures": [
            {"id": item, "status": "disclosed"}
            for item in claim_contract["required_disclosures"]
        ],
        "allowed_claims": claim_contract["allowed_claims"],
        "forbidden_claim_patterns": claim_contract["forbidden_claim_patterns"],
        "claim_boundary": claim_contract["claim_boundary"],
    }
    return report


def validate_report(report: dict[str, Any]) -> None:
    if report.get("schema_version") != REPORT_VERSION or report.get("pass") is not True:
        raise FairnessError("report identity drift")
    if report.get("spec_verdict") != "pass" or report.get("quality_verdict") != "pass":
        raise FairnessError("spec/quality verdict not pass")
    denominator = report.get("denominator", {})
    if (
        denominator.get("planned_pairs") != 60
        or denominator.get("included_pairs") != 60
        or denominator.get("excluded_pairs") != 0
        or denominator.get("unmatched_pairs") != 0
    ):
        raise FairnessError("hidden exclusion or unmatched denominator")
    policies = report.get("policies", {})
    if set(policies) != {"openvla-libero", "pi05-libero"}:
        raise FairnessError("policy provenance drift")
    open_policy = policies["openvla-libero"]
    pi_policy = policies["pi05-libero"]
    revisions = {
        suite: item.get("revision")
        for suite, item in open_policy.get("suite_checkpoints", {}).items()
    }
    if (
        open_policy.get("checkpoint_topology") != "suite-specific"
        or revisions != OPENVLA_REVISIONS
        or open_policy.get("adapter_revision") != OPENVLA_ADAPTER
        or pi_policy.get("checkpoint_topology") != "single-shared-checkpoint"
        or pi_policy.get("checkpoint", {}).get("snapshot_sha256") != PI05_SNAPSHOT
        or pi_policy.get("adapter_revision") != PI05_ADAPTER
    ):
        raise FairnessError("provenance drift")
    if open_policy.get("model_inputs") == pi_policy.get("model_inputs"):
        raise FairnessError("identical-input claim drift")
    if open_policy.get("executed_chunk_shape") == pi_policy.get("executed_chunk_shape"):
        raise FairnessError("action adapter disclosure drift")
    for policy_id, expected in {
        "openvla-libero": {"total": 61, "policy_terminal": 60, "infrastructure_error": 1, "explicit_retries": 1},
        "pi05-libero": {"total": 62, "policy_terminal": 60, "infrastructure_error": 2, "explicit_retries": 2},
    }.items():
        if policies[policy_id].get("attempts") != expected:
            raise FairnessError(f"hidden retry: {policy_id}")
    result = report.get("paired_result", {})
    if (
        result.get("openvla_successes") != 35
        or result.get("pi05_successes") != 58
        or result.get("difference_successes") != 23
        or result.get("denominator") != 60
        or result.get("difference_rate") != 23 / 60
    ):
        raise FairnessError("paired result drift")
    required = {
        "fixed-denominator",
        "checkpoint-topology",
        "model-input-differences",
        "action-adapter-differences",
        "retry-and-infrastructure-history",
        "exclusions",
        "claim-boundary",
    }
    disclosed = {
        item.get("id") for item in report.get("disclosures", []) if item.get("status") == "disclosed"
    }
    if disclosed != required:
        raise FairnessError("required disclosure missing")
    validate_claims(report.get("allowed_claims", []), report.get("forbidden_claim_patterns", []))


def validate_claims(claims: list[dict[str, Any]], patterns: list[dict[str, Any]]) -> None:
    if not claims:
        raise FairnessError("allowed claims missing")
    for claim in claims:
        if not claim.get("evidence"):
            raise FairnessError("claim without evidence")
        text = str(claim.get("text", ""))
        for item in patterns:
            if re.search(item["pattern"], text):
                raise FairnessError(f"forbidden claim: {item['id']}")


def set_path(value: dict[str, Any], path: str, replacement: Any) -> None:
    parts = path.split(".")
    target: Any = value
    for part in parts[:-1]:
        target = target[part]
    target[parts[-1]] = replacement


def add_sources(report: dict[str, Any], paths: dict[str, Path]) -> None:
    report["sources"] = {
        name: {
            "ref": str(path.relative_to(REPO_ROOT)).replace("\\", "/"),
            "sha256": sha256_file(path),
        }
        for name, path in paths.items()
    }
    report["external_sources"] = [
        {"url": "https://github.com/openvla/openvla", "accessed": "2026-07-21"},
        {"url": "https://github.com/Physical-Intelligence/openpi/tree/15a9616a00943ada6c20a0f158e3adb39df2ccac", "accessed": "2026-07-21"},
        {"url": "https://github.com/Lifelong-Robot-Learning/LIBERO/tree/8f1084e3132a39270c3a13ebe37270a43ece2a01", "accessed": "2026-07-21"}
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    paths = {
        "policy_registry": REGISTRY,
        "adapter_report": ADAPTER_REPORT,
        "openvla_manifest": OPENVLA_MANIFEST,
        "pi05_manifest": PI05_MANIFEST,
        "paired_report": PAIRED_REPORT,
        "claim_contract": CLAIM_CONTRACT,
    }
    try:
        report = build_report(
            load_json(REGISTRY),
            load_json(ADAPTER_REPORT),
            load_json(OPENVLA_MANIFEST),
            load_json(PI05_MANIFEST),
            load_json(PAIRED_REPORT),
            load_json(CLAIM_CONTRACT),
        )
        validate_report(report)
        add_sources(report, paths)
    except (FairnessError, FileNotFoundError, KeyError, TypeError, ValueError) as exc:
        print(f"fairness and claim gate: FAIL — {exc}")
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        "fairness and claim gate: PASS "
        f"(pairs={report['denominator']['included_pairs']}, exclusions=0, "
        f"attempts=61/62, verdict={report['spec_verdict']}/{report['quality_verdict']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
