#!/usr/bin/env python3
"""Validate the LAB1 LeRobot v3 episode profile and provenance sidecar."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


PROFILE_NAME = "physical-ai-lerobot-v3-profile-v1"
SIDECAR_SCHEMA = "physical-ai-provenance-v1"
REQUIRED_FEATURES = ("observation.state", "action", "timestamp")
INSTRUCTION_FEATURES = ("task", "task_index")
CANONICAL_SIDECAR_KEYS = {
    "action",
    "cameras",
    "features",
    "frames",
    "state",
    "task",
    "timestamp",
}
UNPINNED_REVISIONS = {"", "head", "latest", "main", "master", "unknown", "unversioned"}
HEX_REVISION = re.compile(r"^(?:[0-9a-f]{7,64}|sha256:[0-9a-f]{64})$", re.IGNORECASE)
WINDOWS_ABSOLUTE_PATH = re.compile(r"^[A-Za-z]:[\\/]")
TOKEN_VALUE = re.compile(r"^(?:hf_|ghp_|github_pat_|sk-)[A-Za-z0-9_-]{8,}")


def _feature_shape(features: dict[str, Any], key: str) -> list[int] | None:
    value = features.get(key)
    if not isinstance(value, dict):
        return None
    shape = value.get("shape")
    if not isinstance(shape, (list, tuple)) or not all(isinstance(item, int) for item in shape):
        return None
    return list(shape)


def _camera_keys(features: dict[str, Any]) -> list[str]:
    return sorted(
        key
        for key, value in features.items()
        if isinstance(value, dict) and value.get("dtype") in {"image", "video"}
    )


def _pinned_revision(value: Any) -> bool:
    return isinstance(value, str) and value.strip().lower() not in UNPINNED_REVISIONS and bool(
        HEX_REVISION.fullmatch(value.strip())
    )


def _walk_strings(value: Any, path: str = "$") -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    if isinstance(value, dict):
        for key, item in value.items():
            found.extend(_walk_strings(item, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.extend(_walk_strings(item, f"{path}[{index}]"))
    elif isinstance(value, str):
        found.append((path, value))
    return found


def _validate_provenance(
    provenance: dict[str, Any], camera_keys: list[str]
) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []

    def reject(code: str, message: str) -> None:
        errors.append({"code": code, "message": message})

    if provenance.get("schema_version") != SIDECAR_SCHEMA:
        reject("invalid_sidecar_schema", f"schema_version must be {SIDECAR_SCHEMA}")

    duplicates = sorted(CANONICAL_SIDECAR_KEYS.intersection(provenance))
    if duplicates:
        reject(
            "canonical_field_duplicated",
            f"sidecar must not own canonical fields: {', '.join(duplicates)}",
        )

    episode = provenance.get("episode")
    if not isinstance(episode, dict):
        reject("missing_episode_provenance", "sidecar episode object is required")
        episode = {}
    if episode.get("format") != "lerobot-v3":
        reject("invalid_episode_format", "episode.format must be lerobot-v3")
    if not _pinned_revision(episode.get("revision")):
        reject("invalid_episode_revision", "episode.revision must be a pinned hash")
    if not isinstance(episode.get("repo_id"), str) or not episode.get("repo_id", "").strip():
        reject("missing_episode_repo", "episode.repo_id is required")

    producer = provenance.get("producer")
    if not isinstance(producer, dict):
        reject("missing_producer", "producer object is required")
        producer = {}
    for component in ("environment", "policy"):
        value = producer.get(component)
        if not isinstance(value, dict):
            reject(f"missing_{component}", f"producer.{component} object is required")
            continue
        if not _pinned_revision(value.get("revision")):
            reject(
                f"invalid_{component}_revision",
                f"producer.{component}.revision must be a pinned hash",
            )

    roles = provenance.get("camera_roles")
    if not isinstance(roles, dict):
        reject("missing_camera_roles", "camera_roles object is required")
        roles = {}
    undeclared = sorted(set(camera_keys).difference(roles))
    unknown = sorted(set(roles).difference(camera_keys))
    if undeclared:
        reject("undeclared_camera_source", f"camera roles missing: {', '.join(undeclared)}")
    if unknown:
        reject("unknown_camera_source", f"camera roles not in episode: {', '.join(unknown)}")

    declared_roles: list[str] = []
    for camera_key, role in roles.items():
        if not isinstance(role, dict):
            reject("invalid_camera_role", f"camera_roles.{camera_key} must be an object")
            continue
        role_name = role.get("role")
        if role_name not in {"main", "wrist", "observer"}:
            reject("invalid_camera_role", f"camera_roles.{camera_key}.role is invalid")
        else:
            declared_roles.append(role_name)
        if not isinstance(role.get("source_key"), str) or not role.get("source_key", "").strip():
            reject("missing_camera_source_key", f"camera_roles.{camera_key}.source_key is required")
        if not isinstance(role.get("model_input"), bool):
            reject("invalid_model_input_flag", f"camera_roles.{camera_key}.model_input must be boolean")
    if "main" not in declared_roles or "wrist" not in declared_roles:
        reject("missing_required_camera_role", "camera_roles must declare main and wrist")

    claims = provenance.get("claims")
    if not isinstance(claims, dict):
        reject("missing_claim_boundary", "claims object is required")
    else:
        if claims.get("recording_mode") != "recorded":
            reject("invalid_recording_claim", "claims.recording_mode must be recorded")
        if claims.get("world") != "simulation":
            reject("invalid_world_claim", "claims.world must be simulation")

    for string_path, value in _walk_strings(provenance):
        if WINDOWS_ABSOLUTE_PATH.match(value) or value.startswith(("/home/", "/Users/")):
            reject("local_path_exposed", f"absolute local path is not allowed at {string_path}")
        if TOKEN_VALUE.match(value):
            reject("secret_exposed", f"token-like value is not allowed at {string_path}")

    return errors


def validate_profile(
    info: dict[str, Any],
    provenance: dict[str, Any] | None = None,
    *,
    require_provenance: bool = False,
) -> dict[str, Any]:
    """Return a deterministic validation report without importing LeRobot."""
    errors: list[dict[str, str]] = []

    def reject(code: str, message: str) -> None:
        errors.append({"code": code, "message": message})

    codebase_version = info.get("codebase_version")
    if not isinstance(codebase_version, str) or not codebase_version.startswith("v3."):
        reject("unsupported_lerobot_version", "codebase_version must be a pinned LeRobot v3.x version")

    features = info.get("features")
    if not isinstance(features, dict):
        reject("missing_features", "info.features must be an object")
        features = {}

    camera_keys = _camera_keys(features)
    if len(camera_keys) < 2:
        reject("insufficient_cameras", "at least two image/video camera features are required")

    for key in REQUIRED_FEATURES:
        if key not in features:
            reject("missing_required_feature", f"required feature is missing: {key}")
    if not any(key in features for key in INSTRUCTION_FEATURES):
        reject("missing_instruction_feature", "task or task_index feature is required")

    state_shape = _feature_shape(features, "observation.state")
    action_shape = _feature_shape(features, "action")
    if state_shape != [8]:
        reject("invalid_state_shape", "observation.state shape must be [8]")
    if action_shape != [7]:
        reject("invalid_action_shape", "action shape must be [7]")

    if provenance is None and require_provenance:
        reject("missing_provenance", "a provenance sidecar is required for local LAB evidence")
    elif provenance is not None:
        errors.extend(_validate_provenance(provenance, camera_keys))

    return {
        "profile": PROFILE_NAME,
        "valid": not errors,
        "codebase_version": codebase_version,
        "camera_keys": camera_keys,
        "state_shape": state_shape,
        "action_shape": action_shape,
        "provenance_required": require_provenance,
        "provenance_present": provenance is not None,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--info", type=Path, required=True, help="LeRobot meta/info.json")
    parser.add_argument("--provenance", type=Path, help="LAB provenance sidecar JSON")
    parser.add_argument("--require-provenance", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    info = json.loads(args.info.read_text(encoding="utf-8"))
    provenance = (
        json.loads(args.provenance.read_text(encoding="utf-8")) if args.provenance else None
    )
    report = validate_profile(info, provenance, require_provenance=args.require_provenance)
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
