#!/usr/bin/env python3
"""Bind a bounded LeRobot episode and official Rerun artifact by hashes and claims."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from episode_profile import validate_profile


REQUIRED_ENTITIES = (
    "/observation.images.image",
    "/observation.images.image2",
    "/state",
    "/action",
)
REQUIRED_TIMELINES = ("frame_index", "timestamp")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def dataset_tree_hash(root: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    count = 0
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix()
        if relative.startswith(".cache/"):
            continue
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(sha256_file(path).encode("ascii"))
        digest.update(b"\n")
        count += 1
    return digest.hexdigest(), count


def evaluate_evidence(
    *,
    dataset_root: Path,
    sidecar_path: Path,
    rrd_path: Path,
    expected_frames: int,
    producer_kind: str,
    rrd_verified: bool,
    rrd_stats: str,
    baseline: dict[str, Any] | None = None,
) -> dict[str, Any]:
    info_path = dataset_root / "meta" / "info.json"
    info = json.loads(info_path.read_text(encoding="utf-8"))
    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    profile = validate_profile(info, sidecar, require_provenance=True)
    total_frames = info.get("total_frames")
    action_event_count = len(sidecar.get("action_events", []))
    entities = {entity: entity in rrd_stats for entity in REQUIRED_ENTITIES}
    timelines = {timeline: timeline in rrd_stats for timeline in REQUIRED_TIMELINES}
    tree_hash, dataset_files = dataset_tree_hash(dataset_root)
    hashes = {
        "dataset_tree_sha256": tree_hash,
        "info_sha256": sha256_file(info_path),
        "sidecar_sha256": sha256_file(sidecar_path),
        "rrd_sha256": sha256_file(rrd_path),
    }
    baseline_errors: list[str] = []
    if baseline is not None:
        expected_hashes = baseline.get("hashes", {})
        for key, value in hashes.items():
            if expected_hashes.get(key) != value:
                baseline_errors.append(f"hash mismatch: {key}")

    errors: list[str] = []
    if not profile["valid"]:
        errors.append("strict episode profile failed")
    if total_frames != expected_frames:
        errors.append(f"info frame count mismatch: {total_frames} != {expected_frames}")
    if action_event_count != expected_frames:
        errors.append(f"sidecar frame count mismatch: {action_event_count} != {expected_frames}")
    if not rrd_verified:
        errors.append("rrd verify failed")
    errors.extend(f"missing Rerun entity: {key}" for key, present in entities.items() if not present)
    errors.extend(f"missing Rerun timeline: {key}" for key, present in timelines.items() if not present)
    errors.extend(baseline_errors)

    return {
        "pass": not errors,
        "producer_kind": producer_kind,
        "producer_claim_ready": producer_kind == "openvla-libero" and not errors,
        "expected_frames": expected_frames,
        "observed_frames": {"info": total_frames, "sidecar_actions": action_event_count},
        "camera_keys": profile["camera_keys"],
        "state_shape": profile["state_shape"],
        "action_shape": profile["action_shape"],
        "profile_valid": profile["valid"],
        "rrd": {
            "verified": rrd_verified,
            "entities": entities,
            "timelines": timelines,
            "artifact": rrd_path.name,
        },
        "hashes": hashes,
        "dataset_files": dataset_files,
        "baseline_checked": baseline is not None,
        "errors": errors,
        "claim_boundary": "recorded simulation; not live inference or real telemetry",
    }


def run_rerun(rrd_path: Path, rerun_cli: Path) -> tuple[bool, str]:
    verify = subprocess.run(
        [str(rerun_cli), "rrd", "verify", str(rrd_path)],
        text=True,
        capture_output=True,
        check=False,
    )
    stats = subprocess.run(
        [str(rerun_cli), "rrd", "stats", str(rrd_path)],
        text=True,
        capture_output=True,
        check=False,
    )
    stats_text = f"{stats.stdout}\n{stats.stderr}"
    return verify.returncode == 0 and stats.returncode == 0, stats_text


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--sidecar", type=Path, required=True)
    parser.add_argument("--rrd", type=Path, required=True)
    parser.add_argument("--rerun-cli", type=Path, required=True)
    parser.add_argument("--expected-frames", type=int, required=True)
    parser.add_argument("--producer-kind", choices=("openvla-libero", "synthetic-smoke"), required=True)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    baseline = json.loads(args.baseline.read_text(encoding="utf-8")) if args.baseline else None
    rrd_verified, rrd_stats = run_rerun(args.rrd, args.rerun_cli)
    report = evaluate_evidence(
        dataset_root=args.dataset_root,
        sidecar_path=args.sidecar,
        rrd_path=args.rrd,
        expected_frames=args.expected_frames,
        producer_kind=args.producer_kind,
        rrd_verified=rrd_verified,
        rrd_stats=rrd_stats,
        baseline=baseline,
    )
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
