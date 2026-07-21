#!/usr/bin/env python3
"""Build and verify the GEN1 task-wise initial-state contract."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

from verify_task_slice import EXPECTED_REVISION, SHA256_RE, load_json, sha256_file


SCHEMA_VERSION = "physical-ai-initial-state-contract-v1"
REPORT_VERSION = "physical-ai-initial-state-verification-v1"
SELECTED_INDICES = [0, 1, 2, 3, 4]
RESET_SEED = 0
RENDER_SIZE = 128
RESET_REPEATS = 2
ROBOT_KEYS = ("robot0_joint_pos", "robot0_eef_pos", "robot0_eef_quat", "robot0_gripper_qpos")
EXPECTED_STATE_SHAPE = {
    "libero_spatial": [92],
    "libero_object": [110],
    "libero_goal": [79],
}


def canonical_array(value: Any) -> tuple[bytes, str, list[int]]:
    import numpy as np

    array = np.asarray(value)
    if array.dtype.byteorder == ">" or (array.dtype.byteorder == "=" and not np.little_endian):
        array = array.byteswap().view(array.dtype.newbyteorder("<"))
    array = np.ascontiguousarray(array)
    return array.tobytes(order="C"), array.dtype.str, list(array.shape)


def fingerprint_array(value: Any) -> str:
    payload, dtype, shape = canonical_array(value)
    header = json.dumps({"dtype": dtype, "shape": shape}, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256()
    digest.update(header.encode("utf-8"))
    digest.update(b"\0")
    digest.update(payload)
    return digest.hexdigest()


def fingerprint_mapping(values: dict[str, Any]) -> str:
    component_hashes = {key: fingerprint_array(values[key]) for key in sorted(values)}
    encoded = json.dumps(component_hashes, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def trusted_libero_imports():
    import torch

    original_load = torch.load
    torch.load = lambda *args, **kwargs: original_load(*args, **{**kwargs, "weights_only": False})
    from libero.libero import benchmark, get_libero_path
    from libero.libero.envs import OffScreenRenderEnv

    return benchmark, get_libero_path, OffScreenRenderEnv


def verify_libero_revision(libero_root: Path) -> str:
    head = subprocess.run(
        ["git", "-C", str(libero_root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if head != EXPECTED_REVISION:
        raise ValueError(f"LIBERO revision mismatch: {head}")
    return head


def init_file_path(libero_root: Path, task: dict[str, Any]) -> Path:
    return libero_root / "libero" / "libero" / "init_files" / task["suite"] / f"{task['task_name']}.pruned_init"


def build_contract(manifest: dict[str, Any], libero_root: Path) -> dict[str, Any]:
    benchmark, _, _ = trusted_libero_imports()
    revision = verify_libero_revision(libero_root)
    suite_cache: dict[str, Any] = {}
    tasks: list[dict[str, Any]] = []
    for selected in manifest["tasks"]:
        suite_name = selected["suite"]
        suite = suite_cache.setdefault(suite_name, benchmark.get_benchmark_dict()[suite_name]())
        task_id = selected["task_id"]
        upstream_task = suite.get_task(task_id)
        if upstream_task.name != selected["task_name"]:
            raise ValueError(f"task identity drift: {selected['task_key']}")
        states = suite.get_task_init_states(task_id)
        source = init_file_path(libero_root, selected)
        if not source.is_file():
            raise ValueError(f"missing init-state file: {selected['task_key']}")
        tasks.append(
            {
                "task_key": selected["task_key"],
                "suite": suite_name,
                "task_id": task_id,
                "init_states_file": f"{selected['task_name']}.pruned_init",
                "source_file_sha256": sha256_file(source),
                "available_state_count": int(states.shape[0]),
                "state_shape": list(states.shape[1:]),
                "dtype": str(states.dtype),
                "selected_states": [
                    {"index": index, "tensor_sha256": fingerprint_array(states[index])}
                    for index in SELECTED_INDICES
                ],
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": "2026-07-21",
        "environment": {"name": "LIBERO", "revision": revision},
        "selection": {
            "indices": SELECTED_INDICES,
            "seed": RESET_SEED,
            "render_size": RENDER_SIZE,
            "reset_repeats": RESET_REPEATS,
        },
        "tasks": tasks,
        "claim_boundary": "Initial-state tensors and repeated simulator reset fingerprints are fixed; no policy action was executed.",
    }


def validate_contract(contract: dict[str, Any], manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if contract.get("schema_version") != SCHEMA_VERSION:
        errors.append("initial-state schema_version mismatch")
    if contract.get("environment", {}).get("revision") != EXPECTED_REVISION:
        errors.append("initial-state environment revision mismatch")
    selection = contract.get("selection", {})
    if selection.get("indices") != SELECTED_INDICES:
        errors.append("selected state order drift")
    if selection.get("seed") != RESET_SEED:
        errors.append("reset seed drift")
    if selection.get("render_size") != RENDER_SIZE or selection.get("reset_repeats") != RESET_REPEATS:
        errors.append("reset probe configuration drift")

    expected_tasks = {task["task_key"]: task for task in manifest.get("tasks", [])}
    tasks = contract.get("tasks")
    if not isinstance(tasks, list) or len(tasks) != len(expected_tasks):
        errors.append(f"expected {len(expected_tasks)} task initial-state entries")
        return errors
    keys = [str(task.get("task_key")) for task in tasks if isinstance(task, dict)]
    for duplicate, count in Counter(keys).items():
        if count > 1:
            errors.append(f"duplicate initial-state task_key: {duplicate}")
    if set(keys) != set(expected_tasks):
        errors.append("initial-state task set does not match benchmark manifest")

    for index, task in enumerate(tasks):
        if not isinstance(task, dict):
            errors.append(f"tasks[{index}] must be an object")
            continue
        task_key = task.get("task_key")
        expected = expected_tasks.get(task_key)
        if expected and (task.get("suite"), task.get("task_id")) != (expected["suite"], expected["task_id"]):
            errors.append(f"task identity mismatch: {task_key}")
        expected_file = f"{expected['task_name']}.pruned_init" if expected else None
        if task.get("init_states_file") != expected_file:
            errors.append(f"init-state filename mismatch: {task_key}")
        if not SHA256_RE.fullmatch(str(task.get("source_file_sha256", ""))):
            errors.append(f"source file hash invalid: {task_key}")
        if task.get("available_state_count", 0) < len(SELECTED_INDICES):
            errors.append(f"not enough available initial states: {task_key}")
        if task.get("state_shape") != EXPECTED_STATE_SHAPE.get(task.get("suite")) or task.get("dtype") != "float64":
            errors.append(f"state tensor contract mismatch: {task_key}")
        states = task.get("selected_states")
        if not isinstance(states, list) or [state.get("index") for state in states] != SELECTED_INDICES:
            errors.append(f"selected state order drift: {task_key}")
            continue
        for state in states:
            if not SHA256_RE.fullmatch(str(state.get("tensor_sha256", ""))):
                errors.append(f"state tensor hash invalid: {task_key}/{state.get('index')}")
    if not str(contract.get("claim_boundary", "")).strip():
        errors.append("initial-state claim_boundary is required")
    return errors


def observation_fingerprints(obs: dict[str, Any]) -> dict[str, str]:
    required = ("agentview_image", "robot0_eye_in_hand_image", "object-state", *ROBOT_KEYS)
    missing = [key for key in required if key not in obs]
    if missing:
        raise ValueError(f"reset observation missing keys: {', '.join(missing)}")
    return {
        "main_camera_sha256": fingerprint_array(obs["agentview_image"]),
        "wrist_camera_sha256": fingerprint_array(obs["robot0_eye_in_hand_image"]),
        "robot_state_sha256": fingerprint_mapping({key: obs[key] for key in ROBOT_KEYS}),
        "object_state_sha256": fingerprint_array(obs["object-state"]),
    }


def probe_resets(
    contract: dict[str, Any], manifest: dict[str, Any], libero_root: Path
) -> tuple[list[str], list[dict[str, Any]]]:
    benchmark, get_libero_path, OffScreenRenderEnv = trusted_libero_imports()
    verify_libero_revision(libero_root)
    contract_tasks = {task["task_key"]: task for task in contract["tasks"]}
    suite_cache: dict[str, Any] = {}
    errors: list[str] = []
    cells: list[dict[str, Any]] = []
    for selected in manifest["tasks"]:
        suite_name = selected["suite"]
        suite = suite_cache.setdefault(suite_name, benchmark.get_benchmark_dict()[suite_name]())
        task_id = selected["task_id"]
        task = suite.get_task(task_id)
        states = suite.get_task_init_states(task_id)
        bddl = os.path.join(get_libero_path("bddl_files"), task.problem_folder, task.bddl_file)
        env = OffScreenRenderEnv(bddl_file_name=bddl, camera_heights=RENDER_SIZE, camera_widths=RENDER_SIZE)
        try:
            expected_states = {state["index"]: state for state in contract_tasks[selected["task_key"]]["selected_states"]}
            task_fingerprints: set[str] = set()
            for state_index in SELECTED_INDICES:
                tensor_hash = fingerprint_array(states[state_index])
                if tensor_hash != expected_states[state_index]["tensor_sha256"]:
                    errors.append(f"state tensor hash drift: {selected['task_key']}/{state_index}")
                repeats: list[dict[str, str]] = []
                for _ in range(RESET_REPEATS):
                    # A clean-run comparison restarts the environment RNG as well as the simulator state.
                    env.seed(RESET_SEED)
                    env.reset()
                    repeats.append(observation_fingerprints(env.set_init_state(states[state_index])))
                matched = repeats[0] == repeats[1]
                if not matched:
                    errors.append(f"reset fingerprint drift: {selected['task_key']}/{state_index}")
                combined = hashlib.sha256(
                    json.dumps(repeats[0], sort_keys=True, separators=(",", ":")).encode("utf-8")
                ).hexdigest()
                task_fingerprints.add(combined)
                cells.append(
                    {
                        "task_key": selected["task_key"],
                        "state_index": state_index,
                        "tensor_sha256": tensor_hash,
                        "reset_fingerprint_sha256": combined,
                        "repeats_match": matched,
                        "components": repeats[0],
                    }
                )
            if len(task_fingerprints) != len(SELECTED_INDICES):
                errors.append(f"selected reset fingerprints are not unique: {selected['task_key']}")
        finally:
            env.close()
    return errors, cells


def apply_mutation(contract: dict[str, Any], mutation: dict[str, Any]) -> dict[str, Any]:
    mutated = copy.deepcopy(contract)
    if mutation["operation"] == "set-selection":
        mutated["selection"][mutation["field"]] = mutation["value"]
    elif mutation["operation"] == "reverse-states":
        mutated["tasks"][mutation["task_index"]]["selected_states"].reverse()
    elif mutation["operation"] == "set-state-hash":
        mutated["tasks"][mutation["task_index"]]["selected_states"][mutation["state_index"]]["tensor_sha256"] = mutation["value"]
    else:
        raise ValueError(f"unknown mutation operation: {mutation['operation']}")
    return mutated


def main() -> int:
    parser = argparse.ArgumentParser()
    base = Path(__file__).resolve().parent
    parser.add_argument("--manifest", type=Path, default=base / "benchmark-manifest.json")
    parser.add_argument("--contract", type=Path, default=base / "initial-states.json")
    parser.add_argument("--libero-root", type=Path)
    parser.add_argument("--build-contract", action="store_true")
    parser.add_argument("--probe-resets", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    manifest = load_json(args.manifest)
    if args.build_contract:
        if not args.libero_root:
            parser.error("--build-contract requires --libero-root")
        contract = build_contract(manifest, args.libero_root)
        args.contract.write_text(json.dumps(contract, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    contract = load_json(args.contract)
    errors = validate_contract(contract, manifest)
    cells: list[dict[str, Any]] = []
    if args.probe_resets:
        if not args.libero_root:
            parser.error("--probe-resets requires --libero-root")
        probe_errors, cells = probe_resets(contract, manifest, args.libero_root)
        errors.extend(probe_errors)
    report = {
        "schema_version": REPORT_VERSION,
        "pass": not errors,
        "contract": args.contract.name,
        "contract_sha256": sha256_file(args.contract),
        "revision": contract.get("environment", {}).get("revision"),
        "task_count": len(contract.get("tasks", [])),
        "selected_state_count": sum(len(task.get("selected_states", [])) for task in contract.get("tasks", [])),
        "reset_probe_count": len(cells),
        "reset_repeat_count": RESET_REPEATS if cells else 0,
        "all_repeats_match": bool(cells) and all(cell["repeats_match"] for cell in cells),
        "cells": cells,
        "errors": errors,
        "claim_boundary": "Repeated simulator reset fingerprints only; no policy action or success outcome was measured.",
    }
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "cells"}, indent=2, ensure_ascii=False))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
