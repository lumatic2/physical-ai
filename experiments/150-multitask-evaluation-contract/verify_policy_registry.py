#!/usr/bin/env python3
"""Verify exact policy artifacts and task-policy compatibility declarations."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from verify_task_slice import EXPECTED_REVISION, SHA256_RE, load_json, sha256_file, sha256_repo_text_file


SCHEMA_VERSION = "physical-ai-policy-compatibility-v1"
OPENPI_REVISION = "15a9616a00943ada6c20a0f158e3adb39df2ccac"
PI05_SNAPSHOT = "11e0f560ebc9ca0f65d26241dd08e2ac07c22ee91455f1789afc2fc5c0378d7b"
OPENVLA_CHECKPOINTS = {
    "libero_spatial": ("openvla/openvla-7b-finetuned-libero-spatial", "962318cec55ac10993ff0f5f43eda9a270b4c873"),
    "libero_object": ("openvla/openvla-7b-finetuned-libero-object", "287d6cfdf12d07b1449505f66d9bf3550257e9b3"),
    "libero_goal": ("openvla/openvla-7b-finetuned-libero-goal", "fa5ae1e7509348889295bba8e08621d8b55e9baf"),
}


def checkpoint_snapshot(metadata: dict[str, Any]) -> str:
    lines = []
    for item in sorted(metadata.get("objects", []), key=lambda value: value.get("name", "")):
        lines.append(
            "|".join(
                str(item.get(key) or "") for key in ("name", "generation", "size", "crc32c", "md5Hash")
            )
        )
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def policy_by_id(registry: dict[str, Any], policy_id: str) -> dict[str, Any] | None:
    for policy in registry.get("policies", []):
        if policy.get("policy_id") == policy_id:
            return policy
    return None


def validate_metadata(metadata: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    objects = metadata.get("objects")
    if not isinstance(objects, list) or len(objects) != 16:
        errors.append("pi05 checkpoint must contain 16 metadata objects")
        return errors
    if len({item.get("name") for item in objects}) != 16:
        errors.append("pi05 checkpoint metadata contains duplicate object names")
    total = sum(int(item.get("size", 0)) for item in objects)
    if total != 12439085481 or metadata.get("total_bytes") != total:
        errors.append("pi05 checkpoint total size mismatch")
    actual_snapshot = checkpoint_snapshot(metadata)
    if actual_snapshot != PI05_SNAPSHOT or metadata.get("snapshot_sha256") != actual_snapshot:
        errors.append("pi05 checkpoint metadata snapshot hash mismatch")
    if not any(item.get("name", "").endswith("norm_stats.json") for item in objects):
        errors.append("pi05 checkpoint norm stats metadata missing")
    return errors


def validate_registry(
    registry: dict[str, Any], manifest: dict[str, Any], metadata: dict[str, Any], repo_root: Path
) -> tuple[list[str], list[dict[str, Any]]]:
    errors = validate_metadata(metadata)
    matrix: list[dict[str, Any]] = []
    if registry.get("schema_version") != SCHEMA_VERSION:
        errors.append("policy registry schema_version mismatch")
    if registry.get("environment", {}).get("revision") != EXPECTED_REVISION:
        errors.append("policy registry environment revision mismatch")
    common = registry.get("common_result_contract", {})
    if common.get("executed_action_dim") != 7 or len(common.get("action_semantics", [])) != 7:
        errors.append("common executed action contract must be 7D")
    if common.get("camera_roles") != ["main", "wrist"] or not common.get("episode_evidence_required"):
        errors.append("common camera/evidence contract mismatch")

    policies = registry.get("policies")
    if not isinstance(policies, list) or {policy.get("policy_id") for policy in policies} != {
        "openvla-libero",
        "pi05-libero",
    }:
        errors.append("policy registry must contain exactly OpenVLA and pi0.5")
        return errors, matrix
    openvla = policy_by_id(registry, "openvla-libero") or {}
    pi05 = policy_by_id(registry, "pi05-libero") or {}

    implementation = openvla.get("implementation", {})
    for file_field, hash_field in (("local_client", "local_client_sha256"), ("local_server", "local_server_sha256")):
        path = repo_root / str(implementation.get(file_field, ""))
        expected_hash = implementation.get(hash_field)
        if not path.is_file() or not SHA256_RE.fullmatch(str(expected_hash or "")) or sha256_repo_text_file(path) != expected_hash:
            errors.append(f"OpenVLA {file_field} source hash mismatch")
    checkpoints = openvla.get("suite_checkpoints", {})
    for suite, (repo_id, revision) in OPENVLA_CHECKPOINTS.items():
        checkpoint = checkpoints.get(suite, {})
        if (checkpoint.get("repo_id"), checkpoint.get("revision")) != (repo_id, revision):
            errors.append(f"OpenVLA checkpoint suite mismatch: {suite}")
        if checkpoint.get("status") not in {"declared_compatible", "excluded"}:
            errors.append(f"OpenVLA unresolved suite status: {suite}")
    ov_inputs = openvla.get("inputs", {})
    if not ov_inputs.get("main_camera", {}).get("model_input"):
        errors.append("OpenVLA main camera must be a model input")
    if ov_inputs.get("wrist_camera", {}).get("model_input"):
        errors.append("OpenVLA wrist camera must remain observer-only")
    if ov_inputs.get("robot_state", {}).get("model_input"):
        errors.append("OpenVLA robot state must not be relabeled as model input")
    ov_outputs = openvla.get("outputs", {})
    if (ov_outputs.get("raw_action_dim"), ov_outputs.get("executed_action_dim")) != (7, 7):
        errors.append("OpenVLA action dimension mismatch")
    if "invert" not in str(ov_outputs.get("gripper_transform", "")):
        errors.append("OpenVLA gripper transform is incomplete")

    pi_impl = pi05.get("implementation", {})
    if pi_impl.get("revision") != OPENPI_REVISION:
        errors.append("openpi implementation revision mismatch")
    for path, digest in pi_impl.get("source_hashes", {}).items():
        if not path or not SHA256_RE.fullmatch(str(digest)):
            errors.append("openpi source hash registry malformed")
    checkpoint = pi05.get("checkpoint", {})
    if (
        checkpoint.get("config") != "pi05_libero"
        or checkpoint.get("uri") != "gs://openpi-assets/checkpoints/pi05_libero"
        or checkpoint.get("snapshot_sha256") != PI05_SNAPSHOT
        or checkpoint.get("object_count") != 16
        or checkpoint.get("total_bytes") != 12439085481
    ):
        errors.append("pi0.5 checkpoint registry mismatch")
    pi_inputs = pi05.get("inputs", {})
    if not pi_inputs.get("main_camera", {}).get("model_input") or not pi_inputs.get("wrist_camera", {}).get("model_input"):
        errors.append("pi0.5 must declare main and wrist camera inputs")
    if pi_inputs.get("robot_state", {}).get("dim") != 8 or not pi_inputs.get("robot_state", {}).get("model_input"):
        errors.append("pi0.5 robot state input must be 8D")
    pi_outputs = pi05.get("outputs", {})
    if (
        pi_outputs.get("model_action_dim") != 32
        or pi_outputs.get("action_horizon") != 10
        or pi_outputs.get("exposed_action_dim") != 7
        or pi_outputs.get("replan_steps") != 5
    ):
        errors.append("pi0.5 action chunk contract mismatch")

    observed = set(openvla.get("observed_cells", [])) | set(pi05.get("observed_cells", []))
    for task in manifest.get("tasks", []):
        suite = task["suite"]
        for policy_id, coverage in (
            ("openvla-libero", checkpoints.get(suite, {})),
            ("pi05-libero", pi05.get("suite_coverage", {}).get(suite, {})),
        ):
            status = coverage.get("status")
            if status == "excluded" and not str(coverage.get("reason", "")).strip():
                errors.append(f"reasonless exclusion: {task['task_key']}/{policy_id}")
            elif status != "declared_compatible":
                errors.append(f"unresolved compatibility: {task['task_key']}/{policy_id}")
            matrix.append(
                {
                    "task_key": task["task_key"],
                    "policy_id": policy_id,
                    "status": status,
                    "evidence_level": "observed_local" if any(cell.startswith(task["task_key"] + "/") for cell in observed) else "official_declared_unprobed",
                }
            )
    if len(matrix) != 24:
        errors.append(f"expected 24 task-policy pairs, got {len(matrix)}")
    if not str(registry.get("claim_boundary", "")).strip():
        errors.append("policy registry claim_boundary is required")
    return errors, matrix


def validate_openpi_source(registry: dict[str, Any], openpi_root: Path) -> list[str]:
    errors: list[str] = []
    try:
        head = subprocess.run(
            ["git", "-C", str(openpi_root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return ["could not verify openpi git revision"]
    if head != OPENPI_REVISION:
        errors.append("openpi checkout revision mismatch")
    pi05 = policy_by_id(registry, "pi05-libero") or {}
    for relative, expected_hash in pi05.get("implementation", {}).get("source_hashes", {}).items():
        path = openpi_root / relative
        if not path.is_file() or sha256_file(path) != expected_hash:
            errors.append(f"openpi source hash mismatch: {relative}")
    return errors


def fetch_live_checkpoint_metadata() -> list[dict[str, Any]]:
    base_url = "https://storage.googleapis.com/storage/v1/b/openpi-assets/o"
    params = {
        "prefix": "checkpoints/pi05_libero/",
        "fields": "items(name,generation,size,crc32c,md5Hash),nextPageToken",
    }
    items: list[dict[str, Any]] = []
    while True:
        url = f"{base_url}?{urllib.parse.urlencode(params)}"
        with urllib.request.urlopen(url, timeout=30) as response:
            payload = json.load(response)
        items.extend(payload.get("items", []))
        token = payload.get("nextPageToken")
        if not token:
            return items
        params["pageToken"] = token


def apply_mutation(registry: dict[str, Any], mutation: dict[str, Any]) -> dict[str, Any]:
    mutated = copy.deepcopy(registry)
    policy = policy_by_id(mutated, mutation["policy_id"])
    if policy is None:
        raise ValueError("mutation policy not found")
    target: Any = policy
    for key in mutation["path"][:-1]:
        target = target[key]
    target[mutation["path"][-1]] = mutation["value"]
    return mutated


def main() -> int:
    parser = argparse.ArgumentParser()
    base = Path(__file__).resolve().parent
    parser.add_argument("--registry", type=Path, default=base / "policy-registry.json")
    parser.add_argument("--manifest", type=Path, default=base / "benchmark-manifest.json")
    parser.add_argument("--metadata", type=Path, default=base / "pi05-checkpoint-metadata.json")
    parser.add_argument("--repo-root", type=Path, default=base.parents[1])
    parser.add_argument("--openpi-root", type=Path)
    parser.add_argument("--verify-live-gcs", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    registry = load_json(args.registry)
    manifest = load_json(args.manifest)
    metadata = load_json(args.metadata)
    errors, matrix = validate_registry(registry, manifest, metadata, args.repo_root.resolve())
    if args.openpi_root:
        errors.extend(validate_openpi_source(registry, args.openpi_root.resolve()))
    live_checkpoint = None
    if args.verify_live_gcs:
        live_items = fetch_live_checkpoint_metadata()
        live_checkpoint = {
            "object_count": len(live_items),
            "total_bytes": sum(int(item.get("size", 0)) for item in live_items),
            "snapshot_sha256": checkpoint_snapshot({"objects": live_items}),
        }
        if live_checkpoint != {
            "object_count": 16,
            "total_bytes": 12439085481,
            "snapshot_sha256": PI05_SNAPSHOT,
        }:
            errors.append("live pi0.5 checkpoint metadata drift")
    report = {
        "schema_version": "physical-ai-policy-registry-verification-v1",
        "pass": not errors,
        "registry": args.registry.name,
        "registry_sha256": sha256_repo_text_file(args.registry),
        "policy_count": len(registry.get("policies", [])),
        "task_policy_pair_count": len(matrix),
        "declared_compatible_count": sum(pair["status"] == "declared_compatible" for pair in matrix),
        "excluded_count": sum(pair["status"] == "excluded" for pair in matrix),
        "openpi_source_verified": bool(args.openpi_root),
        "live_checkpoint_metadata": live_checkpoint,
        "matrix": matrix,
        "errors": errors,
        "claim_boundary": "Static compatibility and artifact identity only; unprobed cells have no success claim.",
    }
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "matrix"}, indent=2, ensure_ascii=False))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
