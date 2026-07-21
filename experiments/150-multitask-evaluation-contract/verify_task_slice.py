#!/usr/bin/env python3
"""Validate the frozen GEN1 LIBERO task slice against a pinned catalog/source."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "physical-ai-multitask-benchmark-v1"
CATALOG_VERSION = "libero-task-catalog-snapshot-v1"
EXPECTED_REVISION = "8f1084e3132a39270c3a13ebe37270a43ece2a01"
EXPECTED_TASK_IDS = {
    "libero_spatial": [0, 3, 5, 8],
    "libero_object": [0, 3, 6, 9],
    "libero_goal": [0, 3, 6, 9],
}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_repo_text_file(path: Path) -> str:
    """Hash tracked text as Git-normalized LF bytes on every platform."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def extract_task_map(path: Path) -> dict[str, list[str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "libero_task_map":
                    value = ast.literal_eval(node.value)
                    if isinstance(value, dict):
                        return value
    raise ValueError(f"libero_task_map assignment not found: {path}")


def validate_catalog(catalog: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if catalog.get("schema_version") != CATALOG_VERSION:
        errors.append("catalog schema_version mismatch")
    if catalog.get("revision") != EXPECTED_REVISION:
        errors.append("catalog revision mismatch")
    suites = catalog.get("suites")
    if not isinstance(suites, dict) or set(suites) != set(EXPECTED_TASK_IDS):
        errors.append("catalog suite set mismatch")
        return errors
    for suite, tasks in suites.items():
        if not isinstance(tasks, list) or len(tasks) != 10 or len(set(tasks)) != 10:
            errors.append(f"catalog {suite} must contain 10 unique tasks")
    if not SHA256_RE.fullmatch(str(catalog.get("source_sha256", ""))):
        errors.append("catalog source_sha256 must be lowercase SHA-256")
    return errors


def validate_manifest(manifest: dict[str, Any], catalog: dict[str, Any]) -> list[str]:
    errors = validate_catalog(catalog)
    if manifest.get("schema_version") != SCHEMA_VERSION:
        errors.append("manifest schema_version mismatch")

    environment = manifest.get("environment")
    if not isinstance(environment, dict):
        errors.append("environment must be an object")
        return errors
    if environment.get("revision") != EXPECTED_REVISION:
        errors.append("environment revision mismatch")
    if environment.get("task_map_sha256") != catalog.get("source_sha256"):
        errors.append("manifest task_map_sha256 does not match catalog")

    suite_contract = manifest.get("suite_contract")
    if not isinstance(suite_contract, dict) or set(suite_contract) != set(EXPECTED_TASK_IDS):
        errors.append("suite_contract must contain exactly spatial/object/goal")
    else:
        for suite, expected_ids in EXPECTED_TASK_IDS.items():
            if suite_contract.get(suite, {}).get("task_ids") != expected_ids:
                errors.append(f"{suite} task_ids drifted from frozen selection")

    tasks = manifest.get("tasks")
    if not isinstance(tasks, list):
        errors.append("tasks must be an array")
        return errors
    if len(tasks) != 12:
        errors.append(f"expected 12 tasks, got {len(tasks)}")

    keys: list[str] = []
    names: list[str] = []
    suite_counts: Counter[str] = Counter()
    for index, task in enumerate(tasks):
        if not isinstance(task, dict):
            errors.append(f"tasks[{index}] must be an object")
            continue
        suite = task.get("suite")
        task_id = task.get("task_id")
        task_name = task.get("task_name")
        task_key = task.get("task_key")
        keys.append(str(task_key))
        names.append(str(task_name))
        suite_counts[str(suite)] += 1

        if suite not in EXPECTED_TASK_IDS or not isinstance(task_id, int):
            errors.append(f"tasks[{index}] has unknown suite or non-integer task_id")
            continue
        catalog_tasks = catalog["suites"][suite]
        if task_id < 0 or task_id >= len(catalog_tasks) or catalog_tasks[task_id] != task_name:
            errors.append(f"tasks[{index}] suite/task_id does not match official catalog")
        expected_key = f"{suite}/task-{task_id:02d}"
        if task_key != expected_key:
            errors.append(f"tasks[{index}] task_key mismatch")
        if task.get("problem_folder") != suite:
            errors.append(f"tasks[{index}] problem_folder mismatch")
        if task.get("bddl_file") != f"{task_name}.bddl":
            errors.append(f"tasks[{index}] bddl_file mismatch")
        if task.get("language_instruction") != str(task_name).replace("_", " "):
            errors.append(f"tasks[{index}] language_instruction mismatch")
        if not SHA256_RE.fullmatch(str(task.get("bddl_sha256", ""))):
            errors.append(f"tasks[{index}] bddl_sha256 must be lowercase SHA-256")
        if not str(task.get("selection_reason", "")).strip():
            errors.append(f"tasks[{index}] selection_reason is required")

    for duplicate in sorted(key for key, count in Counter(keys).items() if count > 1):
        errors.append(f"duplicate task_key: {duplicate}")
    for duplicate in sorted(name for name, count in Counter(names).items() if count > 1):
        errors.append(f"duplicate task_name: {duplicate}")
    for suite in EXPECTED_TASK_IDS:
        if suite_counts[suite] != 4:
            errors.append(f"{suite} must contain exactly 4 selected tasks")
    if not str(manifest.get("claim_boundary", "")).strip():
        errors.append("claim_boundary is required")
    return errors


def locate_libero_files(root: Path, catalog: dict[str, Any]) -> tuple[Path, Path]:
    source = root / catalog["source_path"]
    bddl_root = root / "libero" / "libero" / "bddl_files"
    if not source.is_file() or not bddl_root.is_dir():
        raise ValueError("--libero-root must point to the pinned LIBERO repository root")
    return source, bddl_root


def validate_official_source(
    manifest: dict[str, Any], catalog: dict[str, Any], libero_root: Path
) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    source, bddl_root = locate_libero_files(libero_root, catalog)
    source_hash = sha256_file(source)
    if source_hash != catalog["source_sha256"]:
        errors.append("official task map hash mismatch")
    source_map = extract_task_map(source)
    for suite, tasks in catalog["suites"].items():
        if source_map.get(suite) != tasks:
            errors.append(f"official task map content mismatch: {suite}")

    try:
        head = subprocess.run(
            ["git", "-C", str(libero_root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        head = None
        errors.append("could not verify LIBERO git revision")
    if head != EXPECTED_REVISION:
        errors.append("LIBERO checkout revision mismatch")

    verified_bddl = 0
    for task in manifest["tasks"]:
        bddl = bddl_root / task["suite"] / task["bddl_file"]
        if not bddl.is_file():
            errors.append(f"missing official BDDL: {task['task_key']}")
            continue
        if sha256_file(bddl) != task["bddl_sha256"]:
            errors.append(f"BDDL hash mismatch: {task['task_key']}")
        else:
            verified_bddl += 1
    return errors, {"git_head": head, "task_map_sha256": source_hash, "verified_bddl": verified_bddl}


def build_report(
    manifest_path: Path,
    manifest: dict[str, Any],
    errors: list[str],
    official: dict[str, Any] | None,
) -> dict[str, Any]:
    counts = Counter(task.get("suite") for task in manifest.get("tasks", []) if isinstance(task, dict))
    return {
        "schema_version": "physical-ai-task-slice-verification-v1",
        "pass": not errors,
        "manifest": manifest_path.name,
        "manifest_sha256": sha256_repo_text_file(manifest_path),
        "revision": manifest.get("environment", {}).get("revision"),
        "task_count": len(manifest.get("tasks", [])),
        "suite_counts": dict(sorted(counts.items())),
        "official_source": official,
        "errors": errors,
        "claim_boundary": "Task identities and BDDL bytes are verified; no rollout was executed.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    base = Path(__file__).resolve().parent
    parser.add_argument("--manifest", type=Path, default=base / "benchmark-manifest.json")
    parser.add_argument("--catalog", type=Path, default=base / "official-task-catalog.json")
    parser.add_argument("--libero-root", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    manifest = load_json(args.manifest)
    catalog = load_json(args.catalog)
    errors = validate_manifest(manifest, catalog)
    official = None
    if args.libero_root:
        official_errors, official = validate_official_source(manifest, catalog, args.libero_root)
        errors.extend(official_errors)
    report = build_report(args.manifest, manifest, errors, official)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
