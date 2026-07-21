#!/usr/bin/env python3
"""Extract read-only trajectory and event features from 27 timeout episodes."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pyarrow.parquet as pq

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
OPENVLA_MANIFEST = REPO_ROOT / "experiments" / "151-openvla-multitask-baseline" / "verify" / "canonical" / "manifest.json"
PI05_MANIFEST = REPO_ROOT / "experiments" / "152-paired-vla-comparison" / "verify" / "canonical" / "pi05-manifest.json"
OUTPUT = HERE / "verify" / "features" / "failure-features.json"

REPORT_VERSION = "physical-ai-gen4-failure-feature-index-v1"
HEX64 = "0123456789abcdef"
CLAIM_BOUNDARY = "Derived observable features only; no failure label, root cause, or hidden reasoning is inferred."


class FeatureError(ValueError):
    """Raised when derived features lose source fidelity or units."""


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative_ref(artifact_ref: str, path: Path, attempt_root: Path) -> str:
    return f"{artifact_ref}/{path.relative_to(attempt_root).as_posix()}"


def source_ref(kind: str, artifact_ref: str, path: Path, attempt_root: Path) -> dict[str, Any]:
    return {
        "kind": kind,
        "ref": relative_ref(artifact_ref, path, attempt_root),
        "sha256": sha256_file(path),
    }


def euclidean_steps(values: np.ndarray) -> np.ndarray:
    if len(values) < 2:
        return np.zeros(0, dtype=np.float64)
    return np.linalg.norm(np.diff(values, axis=0), axis=1)


def finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def walk_numbers(value: Any) -> Iterable[float]:
    if isinstance(value, dict):
        for item in value.values():
            yield from walk_numbers(item)
    elif isinstance(value, list):
        for item in value:
            yield from walk_numbers(item)
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        yield float(value)


def timeout_rows(manifest: dict[str, Any], outcome_field: str) -> list[dict[str, Any]]:
    return [row for row in manifest.get("cells", []) if row.get(outcome_field) != "success"]


def extract_episode(row: dict[str, Any], artifact_root: Path, policy_id: str) -> dict[str, Any]:
    artifact_ref = row["artifact_ref"]
    attempt_root = artifact_root / artifact_ref
    manifest_path = attempt_root / "episode-manifest.json"
    if sha256_file(manifest_path) != row["manifest_sha256"]:
        raise FeatureError(f"canonical manifest hash drift: {row['run_key']}")
    dataset_root = attempt_root / "dataset"
    parquet_files = sorted((dataset_root / "data").rglob("*.parquet"))
    video_files = sorted((dataset_root / "videos").rglob("*.mp4"))
    events_path = attempt_root / "events" / "episode_000000.json"
    if len(parquet_files) != 1:
        raise FeatureError(f"trajectory source count: {row['run_key']}")
    if len(video_files) != 2:
        raise FeatureError(f"camera evidence count: {row['run_key']}")
    if not events_path.is_file():
        raise FeatureError(f"event source missing: {row['run_key']}")
    raw_paths = [manifest_path, parquet_files[0], events_path, *video_files]
    before = {relative_ref(artifact_ref, path, attempt_root): sha256_file(path) for path in raw_paths}
    table = pq.read_table(parquet_files[0])
    states = np.asarray(table["observation.state"].to_pylist(), dtype=np.float64)
    actions = np.asarray(table["action"].to_pylist(), dtype=np.float64)
    timestamps = np.asarray(table["timestamp"].to_pylist(), dtype=np.float64).reshape(-1)
    frame_indices = np.asarray(table["frame_index"].to_pylist(), dtype=np.int64).reshape(-1)
    if states.ndim != 2 or states.shape[1] != 8 or actions.ndim != 2 or actions.shape[1] != 7:
        raise FeatureError(f"state/action shape mismatch: {row['run_key']}")
    if not np.isfinite(states).all() or not np.isfinite(actions).all() or not np.isfinite(timestamps).all():
        raise FeatureError(f"non-finite raw trajectory: {row['run_key']}")
    if len(states) == 0 or len(states) != len(actions) or len(states) != len(timestamps):
        raise FeatureError(f"trajectory row count mismatch: {row['run_key']}")
    events = load_json(events_path).get("events", [])
    controller = [event for event in events if event.get("source") == "controller"]
    accepted = [event.get("payload", {}).get("accepted") is True for event in controller]
    rejected = [event for event in controller if event.get("payload", {}).get("accepted") is False]
    xyz = states[:, :3]
    path_steps = euclidean_steps(xyz)
    final_window_start = max(0, len(xyz) - max(20, len(xyz) // 5))
    gripper_state = states[:, 6:8].mean(axis=1)
    translational_action = np.linalg.norm(actions[:, :3], axis=1)
    gripper_command = actions[:, 6]
    sign_transitions = int(np.count_nonzero(np.diff(np.signbit(gripper_command))))
    camera_refs = []
    for video in video_files:
        role = "wrist" if "image2" in video.as_posix() else "main"
        camera_refs.append({"role": role, **source_ref("camera", artifact_ref, video, attempt_root)})
    after = {relative_ref(artifact_ref, path, attempt_root): sha256_file(path) for path in raw_paths}
    return {
        "run_key": row["run_key"],
        "policy_id": policy_id,
        "suite": row["suite"],
        "task_id": int(row["task_id"]),
        "state_index": int(row["state_index"]),
        "outcome": "timeout",
        "episode_ref": artifact_ref,
        "manifest_sha256": row["manifest_sha256"],
        "frame_range": {
            "start": int(frame_indices[0]),
            "end": int(frame_indices[-1]),
            "count": len(frame_indices),
        },
        "duration": {
            "value": float(timestamps[-1] - timestamps[0]),
            "unit": "second",
        },
        "eef_trajectory": {
            "unit": "meter",
            "start_xyz": xyz[0].tolist(),
            "end_xyz": xyz[-1].tolist(),
            "net_displacement": float(np.linalg.norm(xyz[-1] - xyz[0])),
            "path_length": float(path_steps.sum()),
            "max_distance_from_start": float(np.linalg.norm(xyz - xyz[0], axis=1).max()),
            "final_window_start_frame": int(frame_indices[final_window_start]),
            "final_window_displacement": float(np.linalg.norm(xyz[-1] - xyz[final_window_start])),
        },
        "gripper_state": {
            "unit": "simulator-qpos",
            "initial_mean": float(gripper_state[0]),
            "final_mean": float(gripper_state[-1]),
            "range": float(gripper_state.max() - gripper_state.min()),
        },
        "executed_action": {
            "translation_unit": "environment-normalized-command",
            "mean_translation_norm": float(translational_action.mean()),
            "max_translation_norm": float(translational_action.max()),
            "gripper_unit": "environment-normalized-command",
            "gripper_min": float(gripper_command.min()),
            "gripper_max": float(gripper_command.max()),
            "gripper_sign_transitions": sign_transitions,
        },
        "controller_events": {
            "acceptance_event_count": len(controller),
            "accepted_count": sum(accepted),
            "rejected_count": len(rejected),
            "all_accepted": bool(controller) and all(accepted),
            "rejected_event_ids": [event["id"] for event in rejected],
        },
        "camera_evidence": sorted(camera_refs, key=lambda item: item["role"]),
        "object_relation": {
            "available": False,
            "value": None,
            "reason": "canonical-episode-has-no-object-pose-or-contact-feature",
        },
        "goal_distance": {
            "available": False,
            "value": None,
            "reason": "canonical-episode-has-no-task-specific-goal-distance-proxy",
        },
        "sources": {
            "trajectory": source_ref("trajectory", artifact_ref, parquet_files[0], attempt_root),
            "event": source_ref("event-stream", artifact_ref, events_path, attempt_root),
        },
        "raw_integrity": {"before": before, "after": after, "unchanged": before == after},
        "claim_boundary": CLAIM_BOUNDARY,
    }


def validate_feature_index(report: dict[str, Any]) -> None:
    rows = report.get("features")
    if not isinstance(rows, list) or len(rows) != 27:
        raise FeatureError("non-success denominator must be 27")
    if len({row.get("run_key") for row in rows}) != 27:
        raise FeatureError("duplicate feature denominator")
    counts = Counter(row.get("policy_id") for row in rows)
    if counts != {"openvla-libero": 25, "pi05-libero": 2}:
        raise FeatureError("policy denominator mismatch")
    for row in rows:
        if row.get("outcome") != "timeout" or "pattern_id" in row:
            raise FeatureError("feature row promoted to label")
        frames = row.get("frame_range", {})
        if frames.get("start") != 0 or frames.get("end") != frames.get("count") - 1:
            raise FeatureError("frame range mismatch")
        if row.get("eef_trajectory", {}).get("unit") != "meter":
            raise FeatureError("eef unit mismatch")
        action = row.get("executed_action", {})
        if action.get("translation_unit") != "environment-normalized-command":
            raise FeatureError("action unit mismatch")
        if not all(finite_number(value) for value in walk_numbers({
            "duration": row.get("duration"),
            "eef": row.get("eef_trajectory"),
            "gripper": row.get("gripper_state"),
            "action": action,
        })):
            raise FeatureError("feature values must be finite")
        cameras = row.get("camera_evidence", [])
        if {item.get("role") for item in cameras} != {"main", "wrist"}:
            raise FeatureError("camera evidence incomplete")
        sources = row.get("sources", {})
        if sources.get("event", {}).get("kind") != "event-stream":
            raise FeatureError("event source missing")
        if sources.get("trajectory", {}).get("kind") != "trajectory":
            raise FeatureError("trajectory source missing")
        refs = [*cameras, *sources.values()]
        for source in refs:
            ref = source.get("ref")
            sha = source.get("sha256", "")
            if not isinstance(ref, str) or Path(ref).is_absolute() or ".." in Path(ref).parts:
                raise FeatureError("source ref must be relative")
            if len(sha) != 64 or any(char not in HEX64 for char in sha):
                raise FeatureError("source hash invalid")
        for unavailable in (row.get("object_relation", {}), row.get("goal_distance", {})):
            if unavailable.get("available") is not False or unavailable.get("value") is not None or not unavailable.get("reason"):
                raise FeatureError("unavailable feature must remain explicit")
        integrity = row.get("raw_integrity", {})
        if integrity.get("unchanged") is not True or integrity.get("before") != integrity.get("after"):
            raise FeatureError("raw integrity drift")
        if row.get("claim_boundary") != CLAIM_BOUNDARY:
            raise FeatureError("claim boundary drift")


def build_index(open_root: Path, pi_root: Path) -> dict[str, Any]:
    open_manifest = load_json(OPENVLA_MANIFEST)
    pi_manifest = load_json(PI05_MANIFEST)
    open_rows = timeout_rows(open_manifest, "outcome")
    pi_rows = timeout_rows(pi_manifest, "status")
    if len(open_rows) != 25 or len(pi_rows) != 2:
        raise FeatureError("canonical non-success denominator drift")
    features = [extract_episode(row, open_root, "openvla-libero") for row in open_rows]
    features.extend(extract_episode(row, pi_root, "pi05-libero") for row in pi_rows)
    features.sort(key=lambda row: (row["policy_id"], row["suite"], row["task_id"], row["state_index"]))
    report = {
        "schema_version": REPORT_VERSION,
        "pass": True,
        "denominator": {
            "non_success": len(features),
            "by_policy": dict(sorted(Counter(row["policy_id"] for row in features).items())),
        },
        "availability": {
            "robot_state": 27,
            "executed_action": 27,
            "dual_camera": 27,
            "controller_events": 27,
            "object_relation": 0,
            "goal_distance": 0,
        },
        "features": features,
        "sources": {
            "openvla_manifest": {"ref": str(OPENVLA_MANIFEST.relative_to(REPO_ROOT)).replace("\\", "/"), "sha256": sha256_file(OPENVLA_MANIFEST)},
            "pi05_manifest": {"ref": str(PI05_MANIFEST.relative_to(REPO_ROOT)).replace("\\", "/"), "sha256": sha256_file(PI05_MANIFEST)},
        },
        "claim_boundary": CLAIM_BOUNDARY,
    }
    validate_feature_index(report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--openvla-root", type=Path, default=Path("/home/yusun/physical-ai-runs/gen2-openvla"))
    parser.add_argument("--pi05-root", type=Path, default=Path("/home/yusun/physical-ai-runs/gen3-pi05"))
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    try:
        report = build_index(args.openvla_root, args.pi05_root)
    except (FeatureError, FileNotFoundError, KeyError, TypeError, ValueError) as exc:
        print(f"failure feature extraction: FAIL — {exc}")
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        "failure feature extraction: PASS "
        f"(non_success={report['denominator']['non_success']}, "
        f"openvla={report['denominator']['by_policy']['openvla-libero']}, "
        f"pi05={report['denominator']['by_policy']['pi05-libero']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
