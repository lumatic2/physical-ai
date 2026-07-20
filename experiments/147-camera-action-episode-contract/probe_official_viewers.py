#!/usr/bin/env python3
"""Measure whether a LeRobot episode is reusable by the LAB1 viewer stack."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


REQUIRED_FEATURES = ("observation.state", "action", "timestamp")


def evaluate_metadata(info: dict[str, Any]) -> dict[str, Any]:
    """Return a small, deterministic reuse decision from LeRobot info.json."""
    features = info.get("features", {})
    camera_keys = sorted(
        key
        for key, value in features.items()
        if isinstance(value, dict) and value.get("dtype") in {"image", "video"}
    )
    missing_features = [key for key in REQUIRED_FEATURES if key not in features]
    reasons: list[str] = []
    if len(camera_keys) < 2:
        reasons.append("at least two camera features are required")
    if missing_features:
        reasons.append(f"missing required features: {', '.join(missing_features)}")

    return {
        "reusable": not reasons,
        "camera_keys": camera_keys,
        "camera_count": len(camera_keys),
        "required_features": list(REQUIRED_FEATURES),
        "missing_features": missing_features,
        "rejection_reasons": reasons,
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def shape_of(value: Any) -> list[int] | None:
    shape = getattr(value, "shape", None)
    return list(shape) if shape is not None else None


def inspect_sample(dataset_root: Path, repo_id: str, episode_index: int) -> dict[str, Any]:
    from lerobot.datasets import LeRobotDataset

    dataset = LeRobotDataset(
        repo_id,
        root=dataset_root,
        episodes=[episode_index],
        video_backend="pyav",
    )
    sample = dataset[0]
    camera_keys = list(dataset.meta.camera_keys)
    return {
        "episode_index": episode_index,
        "episode_frames": len(dataset),
        "camera_shapes_chw": {key: shape_of(sample[key]) for key in camera_keys},
        "state_shape": shape_of(sample.get("observation.state")),
        "action_shape": shape_of(sample.get("action")),
        "timestamp_seconds": float(sample["timestamp"]),
        "instruction": sample.get("task"),
        "video_backend": "pyav",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--rrd", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repo-id", default="lerobot/libero")
    parser.add_argument("--episode-index", type=int, default=0)
    args = parser.parse_args()

    info_path = args.dataset_root / "meta" / "info.json"
    info = json.loads(info_path.read_text(encoding="utf-8"))
    decision = evaluate_metadata(info)
    sample = inspect_sample(args.dataset_root, args.repo_id, args.episode_index)
    rrd = args.rrd.resolve()

    report = {
        "source": {
            "repo_id": args.repo_id,
            "url": f"https://huggingface.co/datasets/{args.repo_id}",
            "accessed": "2026-07-21",
            "codebase_version": info.get("codebase_version"),
            "fps": info.get("fps"),
        },
        "contract": decision,
        "sample": sample,
        "rerun_artifact": {
            "path": str(rrd),
            "exists": rrd.is_file(),
            "size_bytes": rrd.stat().st_size if rrd.is_file() else None,
            "sha256": sha256_file(rrd) if rrd.is_file() else None,
        },
    }
    report["reusable"] = bool(decision["reusable"] and report["rerun_artifact"]["exists"])

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["reusable"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
