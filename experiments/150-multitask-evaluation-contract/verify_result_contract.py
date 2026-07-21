#!/usr/bin/env python3
"""Generate the immutable 120-cell denominator and verify terminal result fixtures."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from verify_policy_registry import policy_by_id
from verify_task_slice import EXPECTED_REVISION, load_json, sha256_repo_text_file


DENOMINATOR_VERSION = "physical-ai-run-denominator-v1"
RESULT_INDEX_VERSION = "physical-ai-result-index-v1"


def canonical_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def adapter_revision(policy: dict[str, Any]) -> str:
    return canonical_hash(
        {
            "implementation": policy["implementation"],
            "inputs": policy["inputs"],
            "outputs": policy["outputs"],
        }
    )


def artifact_revision(policy: dict[str, Any], suite: str) -> str:
    if policy["policy_id"] == "openvla-libero":
        return policy["suite_checkpoints"][suite]["revision"]
    return policy["checkpoint"]["snapshot_sha256"]


def make_run_key(record: dict[str, Any]) -> str:
    policy = record["policy"]
    return ":".join(
        (
            "v1",
            record["suite"],
            record["task_key"].split("/")[-1],
            f"state-{record['state_index']:02d}",
            policy["policy_id"],
            policy["artifact_revision"],
            policy["adapter_revision"],
        )
    )


def build_denominator(
    manifest: dict[str, Any], initial_states: dict[str, Any], registry: dict[str, Any], sources: dict[str, str]
) -> dict[str, Any]:
    state_map = {
        task["task_key"]: [state["index"] for state in task["selected_states"]]
        for task in initial_states["tasks"]
    }
    policies = {policy["policy_id"]: policy for policy in registry["policies"]}
    runs: list[dict[str, Any]] = []
    for task in manifest["tasks"]:
        for state_index in state_map[task["task_key"]]:
            for policy_id in ("openvla-libero", "pi05-libero"):
                policy = policies[policy_id]
                record = {
                    "suite": task["suite"],
                    "task_key": task["task_key"],
                    "state_index": state_index,
                    "policy": {
                        "policy_id": policy_id,
                        "family": policy["family"],
                        "artifact_revision": artifact_revision(policy, task["suite"]),
                        "adapter_revision": adapter_revision(policy),
                    },
                    "environment_revision": EXPECTED_REVISION,
                }
                record["run_key"] = make_run_key(record)
                runs.append(record)
    return {
        "schema_version": DENOMINATOR_VERSION,
        "generated_at": "2026-07-21",
        "source_sha256": sources,
        "run_key_version": "v1",
        "planned_run_count": len(runs),
        "runs": runs,
        "claim_boundary": "Planned immutable run identities only; no result status is implied.",
    }


def validate_denominator(
    denominator: dict[str, Any], manifest: dict[str, Any], initial_states: dict[str, Any], registry: dict[str, Any], sources: dict[str, str]
) -> list[str]:
    errors: list[str] = []
    expected = build_denominator(manifest, initial_states, registry, sources)
    if denominator.get("schema_version") != DENOMINATOR_VERSION:
        errors.append("denominator schema_version mismatch")
    if denominator.get("source_sha256") != sources:
        errors.append("denominator source hash drift")
    runs = denominator.get("runs")
    if not isinstance(runs, list) or len(runs) != 120 or denominator.get("planned_run_count") != 120:
        errors.append("denominator must contain exactly 120 planned runs")
        return errors
    keys = [run.get("run_key") for run in runs]
    for key, count in Counter(keys).items():
        if count > 1:
            errors.append(f"duplicate run_key: {key}")
    if denominator != expected:
        errors.append("denominator does not match regenerated canonical contract")
    return errors


def make_result(run: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    status = spec["status"]
    steps = 0 if status == "excluded" else 1
    result = {
        "schema_version": "physical-ai-multitask-run-v1",
        **copy.deepcopy(run),
        "attempt": 1,
        "status": status,
        "timing": {
            "steps": steps,
            "duration_seconds": float(steps),
            "policy_latency_ms": {
                "count": steps,
                "total": 10.0 * steps,
                "minimum": 10.0 if steps else None,
                "maximum": 10.0 if steps else None,
            },
        },
        "outcome": {"success": status == "success", "termination_reason": "success"},
        "evidence": {},
    }
    if status == "success":
        result["evidence"]["episode_ref"] = {
            "uri": "experiments/fixture/episode-success.json",
            "sha256": spec["evidence_hash"],
        }
    elif status == "timeout":
        result["outcome"]["termination_reason"] = "max_steps"
        result["evidence"]["episode_ref"] = {
            "uri": "experiments/fixture/episode-timeout.json",
            "sha256": spec["evidence_hash"],
        }
    elif status == "error":
        result["outcome"]["termination_reason"] = "runtime_error"
        result["evidence"]["error_ref"] = {
            "uri": "experiments/fixture/error-report.json",
            "sha256": spec["evidence_hash"],
        }
    else:
        result["outcome"]["termination_reason"] = "manifest_exclusion"
        result["evidence"]["exclusion_reason"] = spec["reason"]
    return result


def validate_result_index(index: dict[str, Any], denominator: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if index.get("schema_version") != RESULT_INDEX_VERSION:
        errors.append("result index schema_version mismatch")
    if index.get("denominator_sha256") != canonical_hash(denominator):
        errors.append("result index denominator hash mismatch")
    results = index.get("results")
    if not isinstance(results, list):
        return errors + ["results must be an array"]
    validator = Draft202012Validator(schema)
    denominator_by_key = {run["run_key"]: run for run in denominator["runs"]}
    keys: list[str] = []
    for result_index, result in enumerate(results):
        for schema_error in sorted(validator.iter_errors(result), key=lambda error: list(error.path)):
            errors.append(f"results[{result_index}] schema: {schema_error.message}")
        key = result.get("run_key")
        keys.append(str(key))
        planned = denominator_by_key.get(key)
        if planned is None:
            errors.append(f"result run_key is outside denominator: {key}")
            continue
        for field in ("suite", "task_key", "state_index", "policy", "environment_revision"):
            if result.get(field) != planned.get(field):
                errors.append(f"result identity drift: {key}/{field}")
    for key, count in Counter(keys).items():
        if count > 1:
            errors.append(f"duplicate run_key: {key}")
    coverage = index.get("coverage")
    if coverage not in {"partial", "complete"}:
        errors.append("result index coverage must be partial or complete")
    if coverage == "complete" and set(keys) != set(denominator_by_key):
        errors.append("complete result index does not cover denominator")
    return errors


def apply_mutation(index: dict[str, Any], mutation: dict[str, Any]) -> dict[str, Any]:
    mutated = copy.deepcopy(index)
    if mutation["operation"] == "duplicate-first":
        mutated["results"].append(copy.deepcopy(mutated["results"][0]))
    elif mutation["operation"] == "claim-complete":
        mutated["coverage"] = "complete"
    elif mutation["operation"] == "remove-evidence":
        mutated["results"][mutation["result_index"]]["evidence"] = {}
    else:
        raise ValueError(f"unknown mutation operation: {mutation['operation']}")
    return mutated


def main() -> int:
    parser = argparse.ArgumentParser()
    base = Path(__file__).resolve().parent
    parser.add_argument("--manifest", type=Path, default=base / "benchmark-manifest.json")
    parser.add_argument("--initial-states", type=Path, default=base / "initial-states.json")
    parser.add_argument("--registry", type=Path, default=base / "policy-registry.json")
    parser.add_argument("--schema", type=Path, default=base / "schemas" / "multitask-run-v1.json")
    parser.add_argument("--denominator", type=Path, default=base / "run-denominator.json")
    parser.add_argument("--write-denominator", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    manifest = load_json(args.manifest)
    states = load_json(args.initial_states)
    registry = load_json(args.registry)
    schema = load_json(args.schema)
    sources = {
        "benchmark_manifest": sha256_repo_text_file(args.manifest),
        "initial_states": sha256_repo_text_file(args.initial_states),
        "policy_registry": sha256_repo_text_file(args.registry),
    }
    if args.write_denominator:
        denominator = build_denominator(manifest, states, registry, sources)
        args.denominator.write_text(json.dumps(denominator, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    denominator = load_json(args.denominator)
    errors = validate_denominator(denominator, manifest, states, registry, sources)
    case_specs = load_json(base / "fixtures" / "result-case-specs.json")
    results = [make_result(denominator["runs"][case["denominator_index"]], case) for case in case_specs["valid_cases"]]
    valid_index = {
        "schema_version": RESULT_INDEX_VERSION,
        "denominator_sha256": canonical_hash(denominator),
        "coverage": "partial",
        "results": results,
    }
    errors.extend(validate_result_index(valid_index, denominator, schema))
    rejected: list[str] = []
    for mutation in case_specs["invalid_mutations"]:
        mutation_errors = validate_result_index(apply_mutation(valid_index, mutation), denominator, schema)
        if any(mutation["expected_error"] in error for error in mutation_errors):
            rejected.append(mutation["id"])
        else:
            errors.append(f"negative fixture did not fail as expected: {mutation['id']}")
    round_trip = json.loads(json.dumps(valid_index, sort_keys=True)) == valid_index
    if not round_trip:
        errors.append("terminal result fixtures did not round-trip losslessly")
    report = {
        "schema_version": "physical-ai-result-contract-verification-v1",
        "pass": not errors,
        "denominator": args.denominator.name,
        "denominator_sha256": sha256_repo_text_file(args.denominator),
        "planned_run_count": len(denominator["runs"]),
        "unique_run_key_count": len({run["run_key"] for run in denominator["runs"]}),
        "terminal_statuses_tested": [case["status"] for case in case_specs["valid_cases"]],
        "lossless_round_trip": round_trip,
        "negative_fixtures_rejected": rejected,
        "errors": errors,
        "claim_boundary": "Run identities and result semantics only; no policy rollout result exists yet.",
    }
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
