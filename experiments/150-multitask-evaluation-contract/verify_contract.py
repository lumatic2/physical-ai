#!/usr/bin/env python3
"""Integrated clean gate for the complete GEN1 evaluation contract."""

from __future__ import annotations

import argparse
import copy
import json
import re
from pathlib import Path
from typing import Any

from verify_initial_states import validate_contract as validate_initial_states
from verify_policy_registry import (
    PI05_SNAPSHOT,
    checkpoint_snapshot,
    fetch_live_checkpoint_metadata,
    validate_openpi_source,
    validate_registry,
)
from verify_result_contract import validate_denominator
from verify_task_slice import (
    load_json,
    sha256_repo_text_file,
    validate_catalog,
    validate_manifest,
    validate_official_source,
)


PATH_SECRET_PATTERNS = (
    re.compile(r"C:[/\\]Users", re.I),
    re.compile(r"/home/[A-Za-z0-9._-]+"),
    re.compile("App" + "Data", re.I),
    re.compile(
        r"(?im)^\s*[\"']?(?:api[_-]?key|access[_-]?token|secret|password)[\"']?"
        r"\s*[:=]\s*[\"'][^\"'\r\n]+[\"']"
    ),
)


def source_hashes(base: Path) -> dict[str, str]:
    return {
        "benchmark_manifest": sha256_repo_text_file(base / "benchmark-manifest.json"),
        "initial_states": sha256_repo_text_file(base / "initial-states.json"),
        "policy_registry": sha256_repo_text_file(base / "policy-registry.json"),
    }


def scrub_paths(base: Path) -> list[str]:
    errors: list[str] = []
    for path in sorted(base.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in {".json", ".md", ".py"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for pattern in PATH_SECRET_PATTERNS:
            if pattern.search(text):
                errors.append(f"path/secret scrub failed: {path.relative_to(base).as_posix()}")
                break
    return errors


def evidence_gate(base: Path) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    expected = {
        "task-slice-report.json": ("manifest_sha256", sha256_repo_text_file(base / "benchmark-manifest.json")),
        "initial-state-report.json": ("contract_sha256", sha256_repo_text_file(base / "initial-states.json")),
        "policy-registry-report.json": ("registry_sha256", sha256_repo_text_file(base / "policy-registry.json")),
        "result-contract-report.json": ("denominator_sha256", sha256_repo_text_file(base / "run-denominator.json")),
    }
    summary: dict[str, Any] = {}
    for filename, (hash_field, expected_hash) in expected.items():
        path = base / "verify" / "canonical" / filename
        report = load_json(path)
        if not report.get("pass"):
            errors.append(f"canonical evidence is not PASS: {filename}")
        if report.get(hash_field) != expected_hash:
            errors.append(f"canonical evidence hash drift: {filename}")
        summary[filename] = {"pass": bool(report.get("pass")), hash_field: report.get(hash_field)}
    state_report = load_json(base / "verify" / "canonical" / "initial-state-report.json")
    if state_report.get("reset_probe_count") != 60 or not state_report.get("all_repeats_match"):
        errors.append("initial-state canonical reset evidence is incomplete")
    registry_report = load_json(base / "verify" / "canonical" / "policy-registry-report.json")
    if registry_report.get("task_policy_pair_count") != 24:
        errors.append("policy registry canonical pair evidence is incomplete")
    result_report = load_json(base / "verify" / "canonical" / "result-contract-report.json")
    if result_report.get("planned_run_count") != 120 or result_report.get("unique_run_key_count") != 120:
        errors.append("result contract canonical denominator evidence is incomplete")
    return errors, summary


def apply_mutation(denominator: dict[str, Any], mutation: dict[str, Any]) -> dict[str, Any]:
    mutated = copy.deepcopy(denominator)
    if mutation["operation"] == "delete-first":
        mutated["runs"].pop(0)
        mutated["planned_run_count"] = len(mutated["runs"])
    elif mutation["operation"] == "duplicate-first":
        mutated["runs"].append(copy.deepcopy(mutated["runs"][0]))
        mutated["planned_run_count"] = len(mutated["runs"])
    elif mutation["operation"] == "replace-environment-revision":
        mutated["runs"][0]["environment_revision"] = mutation["value"]
    else:
        raise ValueError(f"unknown mutation operation: {mutation['operation']}")
    return mutated


def integrated_gate(
    base: Path,
    repo_root: Path,
    libero_root: Path | None = None,
    openpi_root: Path | None = None,
    verify_live_gcs: bool = False,
) -> dict[str, Any]:
    manifest = load_json(base / "benchmark-manifest.json")
    catalog = load_json(base / "official-task-catalog.json")
    initial_states = load_json(base / "initial-states.json")
    registry = load_json(base / "policy-registry.json")
    metadata = load_json(base / "pi05-checkpoint-metadata.json")
    denominator = load_json(base / "run-denominator.json")
    sources = source_hashes(base)
    errors: list[str] = []
    subgates: dict[str, Any] = {}

    task_errors = validate_catalog(catalog) + validate_manifest(manifest, catalog)
    if libero_root:
        official_errors, official_summary = validate_official_source(manifest, catalog, libero_root)
        task_errors.extend(official_errors)
        subgates["official_libero"] = official_summary
    errors.extend(task_errors)
    subgates["task_slice"] = {"pass": not task_errors, "task_count": len(manifest.get("tasks", []))}

    state_errors = validate_initial_states(initial_states, manifest)
    errors.extend(state_errors)
    subgates["initial_states"] = {
        "pass": not state_errors,
        "selected_state_count": sum(len(task["selected_states"]) for task in initial_states["tasks"]),
    }

    registry_errors, matrix = validate_registry(registry, manifest, metadata, repo_root)
    if openpi_root:
        registry_errors.extend(validate_openpi_source(registry, openpi_root))
    if verify_live_gcs:
        live_items = fetch_live_checkpoint_metadata()
        live_snapshot = checkpoint_snapshot({"objects": live_items})
        subgates["live_pi05_checkpoint"] = {
            "object_count": len(live_items),
            "total_bytes": sum(int(item.get("size", 0)) for item in live_items),
            "snapshot_sha256": live_snapshot,
        }
        if live_snapshot != PI05_SNAPSHOT:
            registry_errors.append("live pi0.5 checkpoint metadata drift")
    errors.extend(registry_errors)
    subgates["policy_registry"] = {"pass": not registry_errors, "pair_count": len(matrix)}

    denominator_errors = validate_denominator(denominator, manifest, initial_states, registry, sources)
    errors.extend(denominator_errors)
    subgates["denominator"] = {
        "pass": not denominator_errors,
        "planned": len(denominator.get("runs", [])),
        "unique": len({run.get("run_key") for run in denominator.get("runs", [])}),
    }

    evidence_errors, evidence_summary = evidence_gate(base)
    errors.extend(evidence_errors)
    subgates["canonical_evidence"] = {"pass": not evidence_errors, "reports": evidence_summary}

    scrub_errors = scrub_paths(base)
    errors.extend(scrub_errors)
    subgates["path_secret_scrub"] = {"pass": not scrub_errors}

    rejected: list[str] = []
    mutations = load_json(base / "fixtures" / "integrated-contract-mutations.json")
    for mutation in mutations:
        mutation_errors = validate_denominator(
            apply_mutation(denominator, mutation), manifest, initial_states, registry, sources
        )
        if any(mutation["expected_error"] in error for error in mutation_errors):
            rejected.append(mutation["id"])
        else:
            errors.append(f"integrated negative fixture did not fail: {mutation['id']}")
    subgates["negative_fixtures"] = {"pass": len(rejected) == len(mutations), "rejected": rejected}

    return {
        "schema_version": "physical-ai-gen1-contract-gate-v1",
        "pass": not errors,
        "task_count": len(manifest["tasks"]),
        "state_count_per_task": 5,
        "policy_count": len(registry["policies"]),
        "planned_cell_count": len(denominator["runs"]),
        "subgates": subgates,
        "errors": errors,
        "claim_boundary": "GEN1 freezes evaluation identities and evidence requirements; it contains no policy performance result.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    base = Path(__file__).resolve().parent
    parser.add_argument("--base", type=Path, default=base)
    parser.add_argument("--repo-root", type=Path, default=base.parents[1])
    parser.add_argument("--libero-root", type=Path)
    parser.add_argument("--openpi-root", type=Path)
    parser.add_argument("--verify-live-gcs", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = integrated_gate(
        args.base.resolve(),
        args.repo_root.resolve(),
        args.libero_root.resolve() if args.libero_root else None,
        args.openpi_root.resolve() if args.openpi_root else None,
        args.verify_live_gcs,
    )
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
