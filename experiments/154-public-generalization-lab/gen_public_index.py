#!/usr/bin/env python3
"""Generate the deterministic public GEN5 comparison registry from GEN1-GEN4 evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
WEB_ROOT = REPO_ROOT / "experiments" / "03-digital-twin" / "web"
OUTPUT = WEB_ROOT / "assets" / "generalization-lab" / "registry.json"
VERIFY_OUTPUT = HERE / "verify" / "public-index-report.json"

BENCHMARK = REPO_ROOT / "experiments" / "150-multitask-evaluation-contract" / "benchmark-manifest.json"
PAIRED = REPO_ROOT / "experiments" / "152-paired-vla-comparison" / "verify" / "paired-report.json"
FAIRNESS = REPO_ROOT / "experiments" / "152-paired-vla-comparison" / "verify" / "fairness-report.json"
PATTERNS = (
    REPO_ROOT
    / "experiments"
    / "153-observable-failure-patterns"
    / "verify"
    / "patterns"
    / "failure-pattern-index.json"
)
COVERAGE = (
    REPO_ROOT / "experiments" / "153-observable-failure-patterns" / "verify" / "failure-coverage-report.json"
)
ARM_REGISTRY = WEB_ROOT / "assets" / "arm-lab" / "registry.json"
LAB1_PAIR = WEB_ROOT / "assets" / "arm-lab" / "evidence" / "lab1-pair-report.json"

SCHEMA_VERSION = "physical-ai-public-generalization-lab-v1"
MAX_PUBLIC_BYTES = 256_000
CLAIM_BOUNDARY = (
    "Recorded LIBERO simulator evidence only. Observed results and failure patterns are not a general winner, "
    "root-cause diagnosis, live inference, independent-human review, or real-robot performance claim."
)
SUPPORTED_CLAIMS = [
    "The fixed denominator contains 60 paired task-state cells and 120 recorded policy episodes.",
    "OpenVLA succeeded in 35/60 cells and pi05-libero succeeded in 58/60 cells under their disclosed adapters.",
    "All 27 non-success episodes are indexed as no_progress 6 or unknown 21 under observable GEN4 rules.",
]
UNSAFE_STRING = re.compile(r"(?:[A-Za-z]:[\\/]|/home/|/Users/|\\\\wsl|\.\.[\\/]|(?:sk|hf)_[A-Za-z0-9])")


class PublicIndexError(ValueError):
    """Raised when public evidence loses denominator, hash, or claim safety."""


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def walk(value: Any, pointer: str = "$") -> Iterable[tuple[str, str, Any]]:
    if isinstance(value, dict):
        for key, item in value.items():
            yield from walk(item, f"{pointer}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from walk(item, f"{pointer}[{index}]")
    else:
        yield pointer, pointer.rsplit(".", 1)[-1], value


def public_predicates(record: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            key: predicate[key]
            for key in ("metric", "operator", "observed", "threshold", "unit")
            if key in predicate
        }
        for predicate in record["predicates"]
    ]


def source_hashes(inputs: dict[str, dict[str, Any]]) -> dict[str, str]:
    return {key: canonical_hash(value) for key, value in sorted(inputs.items())}


def validate_inputs(inputs: dict[str, dict[str, Any]]) -> None:
    paired = inputs["paired"]
    denominator = paired.get("denominator", {})
    if denominator.get("paired_keys") != 60 or paired.get("overall", {}).get("denominator") != 60:
        raise PublicIndexError("paired denominator must be 60")
    if len(paired.get("pairs", [])) != 60:
        raise PublicIndexError("paired cells must contain 60 rows")
    if paired["overall"].get("openvla_successes") != 35 or paired["overall"].get("pi05_successes") != 58:
        raise PublicIndexError("paired raw count drift")
    patterns = inputs["patterns"]
    if patterns.get("denominator") != 27 or patterns.get("counts") != {"no_progress": 6, "unknown": 21}:
        raise PublicIndexError("failure pattern denominator drift")
    coverage = inputs["coverage"]
    if coverage.get("denominator") != {"non_success": 27, "indexed": 27, "omitted": 0}:
        raise PublicIndexError("failure coverage drift")
    if inputs["fairness"].get("denominator") != {
        "planned_pairs": 60,
        "included_pairs": 60,
        "excluded_pairs": 0,
        "unmatched_pairs": 0,
        "suites": ["libero_spatial", "libero_object", "libero_goal"],
        "task_groups": 12,
    }:
        raise PublicIndexError("fairness denominator or exclusion drift")
    arm = inputs["arm"]
    for episode_key, episode in arm.get("episodes", {}).items():
        for camera in episode.get("cameras", {}).values():
            if camera.get("sha256") != camera.get("canonical_sha256"):
                raise PublicIndexError(f"stale public camera hash: {episode_key}")
    lab1 = inputs["lab1"]
    contract = lab1.get("contract", {})
    if contract.get("rollout", {}).get("suite") != "libero_spatial" or contract["rollout"].get("task_id") != 5:
        raise PublicIndexError("LAB1 drilldown task drift")
    if contract.get("pass_init_state_index") != 0 or contract.get("fail_init_state_index") != 1:
        raise PublicIndexError("LAB1 drilldown state drift")


def public_episode_link(
    episode_key: str, pair: dict[str, Any], arm: dict[str, Any], lab1: dict[str, Any]
) -> dict[str, Any]:
    episode = arm["episodes"][episode_key]
    outcome = pair["openvla"]["outcome"]
    expected = "success" if episode_key == "pass" else "timeout"
    if outcome != expected or episode["frames"] != lab1["episodes"][episode_key]["expected_frames"]:
        raise PublicIndexError(f"LAB3 public episode mismatch: {episode_key}")
    if episode["canonical_dataset_tree_sha256"] != lab1["hashes"][episode_key]["dataset_tree_sha256"]:
        raise PublicIndexError(f"LAB3 dataset hash mismatch: {episode_key}")
    return {
        "episode_key": episode_key,
        "episode_id": episode["id"],
        "public_url": f"/arm-lab.html?episode={episode_key}",
        "run_key": pair["openvla"]["run_key"],
        "manifest_sha256": pair["openvla"]["manifest_sha256"],
        "canonical_dataset_tree_sha256": episode["canonical_dataset_tree_sha256"],
        "camera_sha256": {
            role: camera["sha256"] for role, camera in sorted(episode["cameras"].items())
        },
    }


def build_registry(inputs: dict[str, dict[str, Any]]) -> dict[str, Any]:
    validate_inputs(inputs)
    tasks = {
        (task["suite"], task["task_id"]): task
        for task in inputs["benchmark"].get("tasks", [])
    }
    patterns = {record["run_key"]: record for record in inputs["patterns"]["records"]}
    arm = inputs["arm"]
    lab1 = inputs["lab1"]
    cells = []
    for pair in sorted(inputs["paired"]["pairs"], key=lambda row: row["paired_key"]):
        task = tasks[(pair["suite"], pair["task_id"])]
        policies = {}
        for public_key, source_key in (("openvla", "openvla"), ("pi05", "pi05")):
            result = pair[source_key]
            pattern = patterns.get(result["run_key"])
            policies[public_key] = {
                "policy_id": result["policy_id"],
                "outcome": result["outcome"],
                "run_key": result["run_key"],
                "manifest_sha256": result["manifest_sha256"],
                "failure": None
                if pattern is None
                else {
                    "pattern_id": pattern["pattern_id"],
                    "rule_version": pattern["rule_version"],
                    "frame_range": pattern["frame_range"],
                    "predicates": public_predicates(pattern),
                },
            }
        cell = {
            "cell_id": pair["paired_key"],
            "suite": pair["suite"],
            "task_id": pair["task_id"],
            "state_index": pair["state_index"],
            "task_name": task["task_name"],
            "instruction": task["language_instruction"],
            "policies": policies,
            "public_episode": None,
        }
        if pair["suite"] == "libero_spatial" and pair["task_id"] == 5 and pair["state_index"] in {0, 1}:
            episode_key = "pass" if pair["state_index"] == 0 else "fail"
            cell["public_episode"] = public_episode_link(episode_key, pair, arm, lab1)
        cells.append(cell)
    paired = inputs["paired"]
    coverage = inputs["coverage"]
    registry = {
        "schema_version": SCHEMA_VERSION,
        "denominator": {"paired_cells": 60, "policy_episodes": 120, "suites": 3, "tasks": 12, "states_per_task": 5},
        "policies": [
            {"key": "openvla", "policy_id": "openvla-libero", "successes": 35, "denominator": 60},
            {"key": "pi05", "policy_id": "pi05-libero", "successes": 58, "denominator": 60},
        ],
        "paired_summary": {
            "difference_successes": paired["overall"]["difference_successes"],
            "difference_denominator": 60,
            "difference_rate": paired["overall"]["difference_rate"],
            "bootstrap_95": paired["paired_difference"]["bootstrap_95"],
            "contingency": paired["contingency"],
            "suites": paired["suites"],
        },
        "execution_contract": {
            "planned_pairs": inputs["fairness"]["denominator"]["planned_pairs"],
            "included_pairs": inputs["fairness"]["denominator"]["included_pairs"],
            "excluded_pairs": inputs["fairness"]["denominator"]["excluded_pairs"],
            "unmatched_pairs": inputs["fairness"]["denominator"]["unmatched_pairs"],
            "spec_verdict": inputs["fairness"]["spec_verdict"],
            "quality_verdict": inputs["fairness"]["quality_verdict"],
        },
        "failure_summary": {
            "denominator": 27,
            "counts": inputs["patterns"]["counts"],
            "specific_pattern_rate": coverage["coverage"]["specific_pattern_rate"],
            "unknown_rate": coverage["coverage"]["unknown_rate"],
            "disabled_patterns": inputs["patterns"]["disabled_patterns"],
            "definitions": {
                "no_progress": "Terminal-window end-effector displacement is below the declared 0.01 m threshold.",
                "unknown": "No enabled observable predicate matched; this is not a hidden-cause diagnosis.",
            },
        },
        "cells": cells,
        "supported_claims": SUPPORTED_CLAIMS,
        "source_hashes": source_hashes(inputs),
        "claim_boundary": CLAIM_BOUNDARY,
    }
    validate_registry(registry)
    return registry


def validate_registry(registry: dict[str, Any]) -> None:
    if registry.get("schema_version") != SCHEMA_VERSION:
        raise PublicIndexError("public registry version drift")
    if registry.get("denominator") != {
        "paired_cells": 60,
        "policy_episodes": 120,
        "suites": 3,
        "tasks": 12,
        "states_per_task": 5,
    }:
        raise PublicIndexError("public denominator missing or drifted")
    cells = registry.get("cells", [])
    if len(cells) != 60 or len({row.get("cell_id") for row in cells}) != 60:
        raise PublicIndexError("public cell denominator drift")
    outcomes = [policy["outcome"] for cell in cells for policy in cell["policies"].values()]
    if len(outcomes) != 120 or count_values(outcomes) != {"success": 93, "timeout": 27}:
        raise PublicIndexError("public episode outcome drift")
    failures = [policy["failure"] for cell in cells for policy in cell["policies"].values() if policy["failure"]]
    if count_values(item["pattern_id"] for item in failures) != {"no_progress": 6, "unknown": 21}:
        raise PublicIndexError("public failure denominator or unknown drift")
    links = [cell["public_episode"] for cell in cells if cell.get("public_episode")]
    if {link["episode_key"] for link in links} != {"pass", "fail"} or len(links) != 2:
        raise PublicIndexError("public LAB3 drilldown coverage drift")
    for pointer, key, value in walk(registry):
        if isinstance(value, str) and UNSAFE_STRING.search(value):
            raise PublicIndexError(f"unsafe local path or token at {pointer}")
        if key.lower() in {"token", "secret", "authorization", "artifact_ref"}:
            raise PublicIndexError(f"non-allowlisted public key at {pointer}")
    for claim in registry.get("supported_claims", []):
        lowered = claim.lower()
        if any(phrase in lowered for phrase in ("winner", "root cause", "real robot", "live inference")):
            raise PublicIndexError("unsupported public claim")
    if registry.get("claim_boundary") != CLAIM_BOUNDARY:
        raise PublicIndexError("public claim boundary drift")
    size = len(canonical_bytes(registry))
    if size > MAX_PUBLIC_BYTES:
        raise PublicIndexError(f"public registry exceeds size budget: {size}")


def count_values(values: Iterable[str]) -> dict[str, int]:
    result: dict[str, int] = {}
    for value in values:
        result[value] = result.get(value, 0) + 1
    return dict(sorted(result.items()))


def default_inputs() -> dict[str, dict[str, Any]]:
    return {
        "benchmark": load_json(BENCHMARK),
        "paired": load_json(PAIRED),
        "fairness": load_json(FAIRNESS),
        "patterns": load_json(PATTERNS),
        "coverage": load_json(COVERAGE),
        "arm": load_json(ARM_REGISTRY),
        "lab1": load_json(LAB1_PAIR),
    }


def write_outputs(registry: dict[str, Any], output: Path, verify_output: Path) -> dict[str, Any]:
    payload = canonical_bytes(registry)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(payload)
    report = {
        "schema_version": "physical-ai-gen5-public-index-report-v1",
        "pass": True,
        "registry_bytes": len(payload),
        "registry_sha256": hashlib.sha256(payload).hexdigest(),
        "cell_count": 60,
        "episode_count": 120,
        "failure_count": 27,
        "unknown_count": 21,
        "public_drilldowns": 2,
        "rejected_contracts": [
            "missing-denominator",
            "stale-episode-hash",
            "local-path-or-token",
            "unsupported-claim",
        ],
        "claim_boundary": CLAIM_BOUNDARY,
    }
    verify_output.parent.mkdir(parents=True, exist_ok=True)
    verify_output.write_bytes(json.dumps(report, ensure_ascii=False, indent=2).encode("utf-8") + b"\n")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--verify-output", type=Path, default=VERIFY_OUTPUT)
    args = parser.parse_args()
    registry = build_registry(default_inputs())
    report = write_outputs(registry, args.output, args.verify_output)
    print(
        "public generalization index: PASS "
        f"(cells=60, episodes=120, failures=27, bytes={report['registry_bytes']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
