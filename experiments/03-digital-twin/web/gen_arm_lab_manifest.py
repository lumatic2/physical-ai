"""Build and verify the deterministic public LAB3 evidence bundle.

The LAB1/LAB2 directories remain canonical.  This script only derives the
small, browser-readable subset used by the public arm laboratory screen.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq


REPO_ROOT = Path(__file__).resolve().parents[3]
WEB_ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT = WEB_ROOT / "assets" / "arm-lab"
LAB1_ROOT = REPO_ROOT / "experiments" / "147-camera-action-episode-contract" / "verify" / "canonical"
LAB2_ROOT = REPO_ROOT / "experiments" / "148-observable-decision-action-trace" / "verify"
ALLOWED_EVENT_SOURCES = {"sensor", "vlm", "vla", "controller", "environment"}
MAX_BUNDLE_BYTES = 5 * 1024 * 1024
ABSOLUTE_PATH_PATTERNS = (
    re.compile(r"(?:^|[\s\"'=])(?:[A-Za-z]):[\\/]"),
    re.compile(r"(?:^|[\s\"'])/(?:home|mnt|Users|tmp)/"),
)
TOKEN_PATTERNS = (
    re.compile(r"\b(?:hf|sk|ghp|github_pat)_[A-Za-z0-9_-]{8,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
)


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(json_bytes(value))


def copy_artifact(source: Path, destination: Path) -> dict[str, Any]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    return {
        "path": destination.as_posix(),
        "bytes": destination.stat().st_size,
        "sha256": sha256_file(destination),
        "canonical_sha256": sha256_file(source),
    }


def relative_artifact(artifact: dict[str, Any], output: Path) -> dict[str, Any]:
    result = dict(artifact)
    result["path"] = Path(result["path"]).relative_to(output).as_posix()
    return result


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def public_trace(outcome: str) -> dict[str, Any]:
    dataset = LAB1_ROOT / outcome / "dataset"
    info = load_json(dataset / "meta" / "info.json")
    episode = pq.read_table(dataset / "meta" / "episodes" / "chunk-000" / "file-000.parquet").to_pylist()[0]
    rows = pq.read_table(dataset / "data" / "chunk-000" / "file-000.parquet").to_pylist()
    return {
        "schema_version": "physical-ai-public-trace-v1",
        "outcome": outcome,
        "fps": info["fps"],
        "instruction": episode["tasks"][0],
        "state_names": info["features"]["observation.state"]["names"],
        "action_names": info["features"]["action"]["names"],
        "frames": [
            {
                "frame": row["frame_index"],
                "timestamp_sec": row["timestamp"],
                "state": row["observation.state"],
                "action": row["action"],
            }
            for row in rows
        ],
    }


def add_json_artifact(output: Path, relative_path: str, value: Any, canonical_path: Path | None = None) -> dict[str, Any]:
    destination = output / relative_path
    write_json(destination, value)
    artifact = {
        "path": relative_path,
        "bytes": destination.stat().st_size,
        "sha256": sha256_file(destination),
    }
    if canonical_path is not None:
        artifact["canonical_sha256"] = sha256_file(canonical_path)
    return artifact


def build_bundle(output: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)

    pair_report_path = LAB1_ROOT / "pair-report.json"
    comparison_report_path = LAB2_ROOT / "two-lane" / "comparison-report.json"
    pair_report = load_json(pair_report_path)
    comparison_report = load_json(comparison_report_path)
    episodes: dict[str, Any] = {}

    for outcome in ("pass", "fail"):
        dataset = LAB1_ROOT / outcome / "dataset"
        trace = public_trace(outcome)
        main_source = dataset / "videos" / "observation.images.image" / "chunk-000" / "file-000.mp4"
        wrist_source = dataset / "videos" / "observation.images.image2" / "chunk-000" / "file-000.mp4"
        main_artifact = relative_artifact(copy_artifact(main_source, output / "media" / f"{outcome}-main.mp4"), output)
        wrist_artifact = relative_artifact(copy_artifact(wrist_source, output / "media" / f"{outcome}-wrist.mp4"), output)
        trace_artifact = add_json_artifact(output, f"traces/{outcome}.json", trace)

        direct_path = LAB2_ROOT / "direct-vla" / f"{outcome}-events.json"
        vlm_path = LAB2_ROOT / "vlm-skill" / ("vlm-skill-events.json" if outcome == "pass" else "vlm-skill-events-fail.json")
        direct_artifact = add_json_artifact(output, f"events/{outcome}-direct-vla.json", load_json(direct_path), direct_path)
        vlm_artifact = add_json_artifact(output, f"events/{outcome}-vlm-skill.json", load_json(vlm_path), vlm_path)

        outcome_record = pair_report["outcomes"][outcome]
        episodes[outcome] = {
            "id": f"libero-openvla-task5-{outcome}",
            "label": "PASS" if outcome == "pass" else "FAIL",
            "outcome": outcome_record,
            "frames": pair_report["frames"][outcome],
            "fps": trace["fps"],
            "duration_sec": pair_report["frames"][outcome] / trace["fps"],
            "instruction": trace["instruction"],
            "cameras": {
                "main": {
                    **main_artifact,
                    "label": "주 카메라 · 모델 입력",
                    "source_key": "agentview_image",
                    "model_input": True,
                },
                "wrist": {
                    **wrist_artifact,
                    "label": "손목 카메라 · 관찰 전용",
                    "source_key": "robot0_eye_in_hand_image",
                    "model_input": False,
                },
            },
            "trace": trace_artifact,
            "event_lanes": {
                "direct_vla": direct_artifact,
                "vlm_skill": vlm_artifact,
            },
            "canonical_dataset_tree_sha256": pair_report["hashes"][outcome]["dataset_tree_sha256"],
        }

    evidence = {
        "lab1_pair_report": add_json_artifact(output, "evidence/lab1-pair-report.json", pair_report, pair_report_path),
        "lab2_comparison_report": add_json_artifact(output, "evidence/lab2-comparison-report.json", comparison_report, comparison_report_path),
    }
    registry = {
        "schema_version": "physical-ai-public-arm-lab-v1",
        "generated_from": {
            "dataset_revision": pair_report["contract"]["dataset_revision"],
            "environment": pair_report["contract"]["producer"]["environment"],
            "policy": pair_report["contract"]["producer"]["policy"],
            "vlm": {
                "name": comparison_report["provenance"]["vlm"][0][0],
                "revision": comparison_report["provenance"]["vlm"][0][1],
            },
        },
        "claim_boundary": "recorded LIBERO simulation evidence; not live inference, real robot telemetry, or free-form chain-of-thought",
        "camera_contract": {
            "model_input": "observation.images.image",
            "observer_only": ["observation.images.image2"],
        },
        "episodes": episodes,
        "evidence": evidence,
        "sources": [
            {"name": "OpenVLA", "url": "https://github.com/openvla/openvla", "accessed_at": "2026-07-21"},
            {"name": "LIBERO", "url": "https://github.com/Lifelong-Robot-Learning/LIBERO", "accessed_at": "2026-07-21"},
            {"name": "Qwen3-VL", "url": "https://github.com/QwenLM/Qwen3-VL", "accessed_at": "2026-07-21"},
        ],
    }
    write_json(output / "registry.json", registry)
    verify_bundle(output)
    return registry


def iter_artifact_records(registry: dict[str, Any]):
    for episode in registry["episodes"].values():
        yield from episode["cameras"].values()
        yield episode["trace"]
        yield from episode["event_lanes"].values()
    yield from registry["evidence"].values()


def reject_sensitive_text(text: str) -> None:
    for pattern in ABSOLUTE_PATH_PATTERNS:
        if pattern.search(text):
            raise ValueError(f"absolute local path forbidden: {pattern.pattern}")
    for pattern in TOKEN_PATTERNS:
        if pattern.search(text):
            raise ValueError(f"token-like value forbidden: {pattern.pattern}")


def verify_event_document(document: dict[str, Any], path: str) -> None:
    for event in document.get("events", []):
        source = event.get("source")
        if source not in ALLOWED_EVENT_SOURCES:
            raise ValueError(f"unsupported event source {source!r} in {path}")


def verify_bundle(output: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    registry_path = output / "registry.json"
    if not registry_path.is_file():
        raise ValueError("missing registry.json")
    registry_text = registry_path.read_text(encoding="utf-8")
    reject_sensitive_text(registry_text)
    registry = json.loads(registry_text)
    if registry.get("schema_version") != "physical-ai-public-arm-lab-v1":
        raise ValueError("unsupported registry schema")
    claim = registry.get("claim_boundary", "").lower()
    if "recorded" not in claim or "simulation" not in claim or "not live" not in claim or "real robot" not in claim:
        raise ValueError("claim boundary must state recorded simulation and reject live/real claims")

    referenced = {"registry.json"}
    for artifact in iter_artifact_records(registry):
        relative_path = artifact.get("path", "")
        if not relative_path or Path(relative_path).is_absolute() or ".." in Path(relative_path).parts:
            raise ValueError(f"unsafe artifact path: {relative_path!r}")
        path = output / relative_path
        referenced.add(relative_path)
        if not path.is_file():
            raise ValueError(f"missing artifact: {relative_path}")
        if path.stat().st_size != artifact.get("bytes"):
            raise ValueError(f"size mismatch: {relative_path}")
        if sha256_file(path) != artifact.get("sha256"):
            raise ValueError(f"hash mismatch: {relative_path}")
        if path.suffix == ".json":
            text = path.read_text(encoding="utf-8")
            reject_sensitive_text(text)
            document = json.loads(text)
            if relative_path.startswith("events/"):
                verify_event_document(document, relative_path)

    actual = {path.relative_to(output).as_posix() for path in output.rglob("*") if path.is_file()}
    unreferenced = actual - referenced
    if unreferenced:
        raise ValueError(f"unreferenced public artifacts: {sorted(unreferenced)}")
    total_bytes = sum(path.stat().st_size for path in output.rglob("*") if path.is_file())
    if total_bytes > MAX_BUNDLE_BYTES:
        raise ValueError(f"bundle size {total_bytes} exceeds {MAX_BUNDLE_BYTES}")
    return {"valid": True, "files": len(actual), "bytes": total_bytes, "registry_sha256": sha256_file(registry_path)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    result = verify_bundle(args.output) if args.verify_only else (build_bundle(args.output) and verify_bundle(args.output))
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
