#!/usr/bin/env python3
"""Validate GEN1 identities and invoke one exact OpenVLA LIBERO rollout."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
DEFAULT_REPO_ROOT = HERE.parents[1]
DEFAULT_CONFIG = HERE / "runner-config.json"
GEN1_DIR = DEFAULT_REPO_ROOT / "experiments" / "150-multitask-evaluation-contract"
if str(GEN1_DIR) not in sys.path:
    sys.path.insert(0, str(GEN1_DIR))

from verify_result_contract import adapter_revision  # noqa: E402
from verify_task_slice import load_json, sha256_repo_text_file  # noqa: E402


CONFIG_VERSION = "physical-ai-gen2-runner-config-v1"
REPORT_VERSION = "physical-ai-gen2-dry-run-v1"


class RunnerContractError(ValueError):
    """Raised before execution when a frozen identity no longer matches."""


def canonical_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def safe_repo_path(repo_root: Path, relative: str) -> Path:
    candidate = Path(relative)
    if candidate.is_absolute():
        raise RunnerContractError(f"source path must be repo-relative: {relative}")
    root = repo_root.resolve()
    resolved = (root / candidate).resolve()
    if resolved != root and root not in resolved.parents:
        raise RunnerContractError(f"source path escapes repo: {relative}")
    return resolved


def task_id_from_key(task_key: str) -> int:
    try:
        return int(task_key.rsplit("task-", 1)[1])
    except (IndexError, ValueError) as exc:
        raise RunnerContractError(f"invalid task key: {task_key}") from exc


def openvla_policy(registry: dict[str, Any], policy_id: str) -> dict[str, Any]:
    matches = [policy for policy in registry.get("policies", []) if policy.get("policy_id") == policy_id]
    if len(matches) != 1:
        raise RunnerContractError(f"expected exactly one policy registry entry for {policy_id}")
    return matches[0]


def load_runner_contract(
    config_path: Path = DEFAULT_CONFIG,
    repo_root: Path = DEFAULT_REPO_ROOT,
    *,
    _documents_override: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    config = load_json(config_path)
    errors: list[str] = []
    if config.get("schema_version") != CONFIG_VERSION:
        errors.append("runner config schema mismatch")
    sources: dict[str, Path] = {}
    for name, source in config.get("sources", {}).items():
        path = safe_repo_path(repo_root, str(source.get("path", "")))
        sources[name] = path
        if not path.is_file():
            errors.append(f"missing source: {name}")
        elif sha256_repo_text_file(path) != source.get("sha256"):
            errors.append(f"source revision mismatch: {name}")
    required = {"manifest", "initial_states", "policy_registry", "denominator", "orchestrator"}
    if set(sources) != required:
        errors.append(f"runner sources must be exactly {sorted(required)}")
    if errors:
        raise RunnerContractError("; ".join(errors))

    manifest = load_json(sources["manifest"])
    states = load_json(sources["initial_states"])
    registry = load_json(sources["policy_registry"])
    denominator = load_json(sources["denominator"])
    if _documents_override:
        manifest = _documents_override.get("manifest", manifest)
        states = _documents_override.get("initial_states", states)
        registry = _documents_override.get("policy_registry", registry)
        denominator = _documents_override.get("denominator", denominator)
    policy = openvla_policy(registry, config["policy_id"])
    environment_revision = config.get("environment_revision")
    if manifest.get("environment", {}).get("revision") != environment_revision:
        errors.append("manifest environment revision mismatch")
    if states.get("environment", {}).get("revision") != environment_revision:
        errors.append("initial-state environment revision mismatch")
    if registry.get("environment", {}).get("revision") != environment_revision:
        errors.append("policy registry environment revision mismatch")

    task_lookup = {(task["suite"], int(task["task_id"])): task for task in manifest.get("tasks", [])}
    state_lookup = {
        (task["suite"], int(task["task_id"])): {int(state["index"]) for state in task.get("selected_states", [])}
        for task in states.get("tasks", [])
    }
    expected_adapter = adapter_revision(policy)
    suite_order = config.get("suite_order", [])
    suite_rank = {suite: index for index, suite in enumerate(suite_order)}
    cells = []
    for run in denominator.get("runs", []):
        if run.get("policy", {}).get("policy_id") != config["policy_id"]:
            continue
        suite = run.get("suite")
        task_id = task_id_from_key(str(run.get("task_key", "")))
        state_index = int(run.get("state_index", -1))
        checkpoint = policy.get("suite_checkpoints", {}).get(suite, {})
        if suite not in suite_rank:
            errors.append(f"denominator suite outside configured order: {suite}")
        if (suite, task_id) not in task_lookup:
            errors.append(f"denominator task outside manifest: {suite}/task-{task_id:02d}")
        if state_index not in state_lookup.get((suite, task_id), set()):
            errors.append(f"denominator state outside contract: {suite}/task-{task_id:02d}/state-{state_index:02d}")
        if run.get("environment_revision") != environment_revision:
            errors.append(f"run environment revision mismatch: {run.get('run_key')}")
        if run.get("policy", {}).get("artifact_revision") != checkpoint.get("revision"):
            errors.append(f"checkpoint revision mismatch: {run.get('run_key')}")
        if run.get("policy", {}).get("adapter_revision") != expected_adapter:
            errors.append(f"adapter revision mismatch: {run.get('run_key')}")
        cells.append(
            {
                "run_key": run["run_key"],
                "suite": suite,
                "task_id": task_id,
                "state_index": state_index,
                "instruction": task_lookup.get((suite, task_id), {}).get("language_instruction"),
                "checkpoint_repo": checkpoint.get("repo_id"),
                "checkpoint_revision": checkpoint.get("revision"),
                "adapter_revision": expected_adapter,
                "environment_revision": environment_revision,
            }
        )

    cells.sort(key=lambda cell: (suite_rank.get(cell["suite"], 999), cell["task_id"], cell["state_index"]))
    if len(cells) != config.get("expected_cell_count"):
        errors.append(f"expected {config.get('expected_cell_count')} OpenVLA cells, got {len(cells)}")
    if len({cell["run_key"] for cell in cells}) != len(cells):
        errors.append("duplicate OpenVLA run key")
    if any(not cell["instruction"] for cell in cells):
        errors.append("OpenVLA cell is missing its frozen language instruction")
    suite_counts = Counter(cell["suite"] for cell in cells)
    if any(suite_counts[suite] != 20 for suite in suite_order):
        errors.append(f"expected 20 cells per suite, got {dict(suite_counts)}")
    if errors:
        raise RunnerContractError("; ".join(dict.fromkeys(errors)))
    return {
        "config": config,
        "sources": sources,
        "cells": cells,
        "suite_counts": dict(suite_counts),
    }


def select_cells(
    cells: list[dict[str, Any]],
    *,
    run_key: str | None = None,
    suite: str | None = None,
    task_id: int | None = None,
    state_index: int | None = None,
) -> list[dict[str, Any]]:
    selector_values = (suite, task_id, state_index)
    if run_key and any(value is not None for value in selector_values):
        raise RunnerContractError("--run-key cannot be combined with suite/task/state selectors")
    if any(value is not None for value in selector_values) and not all(value is not None for value in selector_values):
        raise RunnerContractError("suite, task-id, and state-index must be supplied together")
    if run_key:
        selected = [cell for cell in cells if cell["run_key"] == run_key]
    elif all(value is not None for value in selector_values):
        selected = [
            cell
            for cell in cells
            if cell["suite"] == suite and cell["task_id"] == task_id and cell["state_index"] == state_index
        ]
    else:
        selected = list(cells)
    if not selected:
        raise RunnerContractError("requested task/state is outside the frozen OpenVLA denominator")
    return selected


def execution_command(cell: dict[str, Any], contract: dict[str, Any], python: str, port: int) -> list[str]:
    config = contract["config"]
    script = config["sources"]["orchestrator"]["path"]
    return [
        python,
        "-u",
        script,
        "--policy",
        "openvla",
        "--suite",
        cell["suite"],
        "--ckpt",
        cell["checkpoint_repo"],
        "--ckpt-revision",
        cell["checkpoint_revision"],
        "--tasks",
        "1",
        "--task-offset",
        str(cell["task_id"]),
        "--trials",
        "1",
        "--trial-offset",
        str(cell["state_index"]),
        "--seed",
        str(config["seed"]),
        "--max-policy-steps",
        str(config["max_policy_steps"][cell["suite"]]),
        "--port",
        str(port),
    ]


def dry_run_report(contract: dict[str, Any], selected: list[dict[str, Any]], python: str, port: int) -> dict[str, Any]:
    cells = [
        {
            "order": order,
            **cell,
            "command": execution_command(cell, contract, python, port),
        }
        for order, cell in enumerate(selected)
    ]
    return {
        "schema_version": REPORT_VERSION,
        "pass": True,
        "policy_id": contract["config"]["policy_id"],
        "cell_count": len(cells),
        "suite_counts": dict(Counter(cell["suite"] for cell in cells)),
        "ordered_run_keys_sha256": canonical_hash([cell["run_key"] for cell in cells]),
        "cells": cells,
        "claim_boundary": "Dry-run validates identities and commands only; no rollout was executed.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="GEN1에서 고정한 OpenVLA cell을 검증·실행한다.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--repo-root", type=Path, default=DEFAULT_REPO_ROOT)
    parser.add_argument("--run-key")
    parser.add_argument("--suite")
    parser.add_argument("--task-id", type=int)
    parser.add_argument("--state-index", type=int)
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--json", action="store_true", help="dry-run report를 JSON으로 출력")
    parser.add_argument("--output", type=Path, help="dry-run JSON report 저장 경로")
    args = parser.parse_args()
    try:
        contract = load_runner_contract(args.config, args.repo_root)
        selected = select_cells(
            contract["cells"],
            run_key=args.run_key,
            suite=args.suite,
            task_id=args.task_id,
            state_index=args.state_index,
        )
        report = dry_run_report(contract, selected, args.python, args.port)
    except (OSError, KeyError, TypeError, RunnerContractError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    if args.execute:
        if len(selected) != 1:
            parser.error("--execute requires exactly one frozen cell selector")
        if os.environ.get("MUJOCO_GL") != "egl":
            parser.error("--execute requires MUJOCO_GL=egl")
        command = execution_command(selected[0], contract, args.python, args.port)
        return subprocess.run(command, cwd=args.repo_root, env=os.environ).returncode
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        for cell in report["cells"]:
            print(
                f"[{cell['order']:02d}] {cell['suite']}/task-{cell['task_id']:02d}/state-{cell['state_index']:02d} "
                f"{cell['run_key']}"
            )
        print(f"DRY_RUN cells={report['cell_count']} order_sha256={report['ordered_run_keys_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
