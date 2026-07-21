#!/usr/bin/env python3
"""Run one provenance-locked π0.5-LIBERO compatibility probe."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import time
from typing import Any

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
GEN1_DIR = REPO_ROOT / "experiments" / "150-multitask-evaluation-contract"
DEFAULT_LOCK = HERE / "runtime-lock.json"
REPORT_VERSION = "physical-ai-gen3-pi05-probe-v1"
EXPECTED_CONFIG = "pi05_libero"
EXPECTED_CHECKPOINT = "gs://openpi-assets/checkpoints/pi05_libero"
EXPECTED_ACTION_SHAPE = (10, 7)
SUPPORTED_SUITES = ("libero_spatial", "libero_object", "libero_goal")


class ProbeContractError(ValueError):
    """Raised before a result can be accepted as GEN3 evidence."""


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def pi05_registry_entry(registry: dict[str, Any]) -> dict[str, Any]:
    matches = [policy for policy in registry.get("policies", []) if policy.get("policy_id") == "pi05-libero"]
    if len(matches) != 1:
        raise ProbeContractError("expected exactly one pi05-libero registry entry")
    return matches[0]


def validate_runtime_lock(lock: dict[str, Any], registry: dict[str, Any]) -> dict[str, Any]:
    policy = pi05_registry_entry(registry)
    checkpoint = policy.get("checkpoint", {})
    implementation = policy.get("implementation", {})
    errors: list[str] = []
    if lock.get("schema_version") != "physical-ai-gen3-pi05-runtime-lock-v1":
        errors.append("runtime lock schema mismatch")
    if lock.get("openpi", {}).get("revision") != implementation.get("revision"):
        errors.append("openpi revision mismatch")
    if lock.get("checkpoint", {}).get("config") != EXPECTED_CONFIG:
        errors.append("wrong suite checkpoint config")
    if lock.get("checkpoint", {}).get("uri") != EXPECTED_CHECKPOINT:
        errors.append("wrong suite checkpoint URI")
    if lock.get("checkpoint", {}).get("snapshot_sha256") != checkpoint.get("snapshot_sha256"):
        errors.append("checkpoint snapshot mismatch")
    if lock.get("environment", {}).get("revision") != registry.get("environment", {}).get("revision"):
        errors.append("environment revision mismatch")
    if tuple(lock.get("supported_suites", [])) != SUPPORTED_SUITES:
        errors.append("supported suite set mismatch")
    if errors:
        raise ProbeContractError("; ".join(errors))
    return policy


def validate_request(
    *,
    suite: str,
    state: Any,
    main_image: Any,
    wrist_image: Any,
    prompt: str,
    norm_stats_path: Path,
) -> None:
    import numpy as np

    errors: list[str] = []
    if suite not in SUPPORTED_SUITES:
        errors.append(f"unsupported suite: {suite}")
    if np.asarray(state).shape != (8,):
        errors.append(f"state must be 8D, got {np.asarray(state).shape}")
    for role, image in (("main", main_image), ("wrist", wrist_image)):
        array = np.asarray(image)
        if array.shape != (224, 224, 3):
            errors.append(f"{role} image must be 224x224x3, got {array.shape}")
        if array.dtype != np.uint8:
            errors.append(f"{role} image must be uint8, got {array.dtype}")
    if not isinstance(prompt, str) or not prompt.strip():
        errors.append("prompt must be non-empty")
    if not norm_stats_path.is_file():
        errors.append("missing LIBERO norm stats")
    if errors:
        raise ProbeContractError("; ".join(errors))


def validate_action_chunk(actions: Any) -> Any:
    import numpy as np

    array = np.asarray(actions)
    if array.shape != EXPECTED_ACTION_SHAPE:
        raise ProbeContractError(f"action chunk must be 10x7, got {array.shape}")
    if not np.isfinite(array).all():
        raise ProbeContractError("action chunk contains non-finite values")
    return array


def validate_checkpoint_materialization(checkpoint_dir: Path, lock: dict[str, Any]) -> dict[str, int]:
    files = [path for path in checkpoint_dir.rglob("*") if path.is_file()]
    object_count = len(files)
    total_bytes = sum(path.stat().st_size for path in files)
    expected = lock["checkpoint"]
    if object_count != int(expected["object_count"]):
        raise ProbeContractError(
            f"checkpoint object count mismatch: expected {expected['object_count']}, got {object_count}"
        )
    if total_bytes != int(expected["total_bytes"]):
        raise ProbeContractError(
            f"checkpoint byte count mismatch: expected {expected['total_bytes']}, got {total_bytes}"
        )
    return {"object_count": object_count, "total_bytes": total_bytes}


def input_digest(element: dict[str, Any]) -> str:
    import numpy as np

    digest = hashlib.sha256()
    for key in ("observation/image", "observation/wrist_image", "observation/state"):
        array = np.ascontiguousarray(element[key])
        digest.update(key.encode("utf-8"))
        digest.update(str(array.dtype).encode("ascii"))
        digest.update(json.dumps(list(array.shape)).encode("ascii"))
        digest.update(array.tobytes())
    digest.update(element["prompt"].encode("utf-8"))
    return digest.hexdigest()


def first_video_frame(path: Path) -> Any:
    import imageio.v3 as iio

    return next(iio.imiter(path, plugin="pyav"))


def task_instruction(suite: str, task_id: int) -> str:
    manifest = load_json(GEN1_DIR / "benchmark-manifest.json")
    matches = [
        task.get("language_instruction")
        for task in manifest.get("tasks", [])
        if task.get("suite") == suite and int(task.get("task_id", -1)) == task_id
    ]
    if len(matches) != 1 or not matches[0]:
        raise ProbeContractError("sample instruction is not frozen in GEN1")
    return str(matches[0])


def load_gen2_sample(sample_dir: Path, *, suite: str, task_id: int) -> dict[str, Any]:
    import numpy as np
    from openpi_client import image_tools
    import pyarrow.parquet as pq

    data_path = sample_dir / "dataset" / "data" / "chunk-000" / "file-000.parquet"
    main_path = sample_dir / "dataset" / "videos" / "observation.images.image" / "chunk-000" / "file-000.mp4"
    wrist_path = sample_dir / "dataset" / "videos" / "observation.images.image2" / "chunk-000" / "file-000.mp4"
    if not all(path.is_file() for path in (data_path, main_path, wrist_path)):
        raise ProbeContractError("GEN2 canonical sample is incomplete")
    first_row = pq.read_table(data_path).slice(0, 1).to_pylist()[0]

    def preprocess(frame: Any) -> Any:
        rotated = np.ascontiguousarray(np.asarray(frame)[::-1, ::-1])
        return image_tools.convert_to_uint8(image_tools.resize_with_pad(rotated, 224, 224))

    return {
        "observation/image": preprocess(first_video_frame(main_path)),
        "observation/wrist_image": preprocess(first_video_frame(wrist_path)),
        "observation/state": np.asarray(first_row["observation.state"], dtype=np.float32),
        "prompt": task_instruction(suite, task_id),
    }


def run_probe(*, sample_dir: Path, checkpoint_dir: Path, lock_path: Path) -> dict[str, Any]:
    import jax
    import numpy as np

    from openpi.policies import policy_config
    from openpi.training import config as training_config

    registry = load_json(GEN1_DIR / "policy-registry.json")
    lock = load_json(lock_path)
    policy_entry = validate_runtime_lock(lock, registry)
    materialization = validate_checkpoint_materialization(checkpoint_dir, lock)
    suite = "libero_spatial"
    task_id = 0
    state_index = 0
    element = load_gen2_sample(sample_dir, suite=suite, task_id=task_id)
    norm_stats_path = checkpoint_dir / "assets" / "physical-intelligence" / "libero" / "norm_stats.json"
    validate_request(
        suite=suite,
        state=element["observation/state"],
        main_image=element["observation/image"],
        wrist_image=element["observation/wrist_image"],
        prompt=element["prompt"],
        norm_stats_path=norm_stats_path,
    )
    config = training_config.get_config(EXPECTED_CONFIG)
    started = time.perf_counter()
    policy = policy_config.create_trained_policy(config, checkpoint_dir)
    load_seconds = time.perf_counter() - started
    started = time.perf_counter()
    result = policy.infer(element)
    inference_seconds = time.perf_counter() - started
    actions = validate_action_chunk(result.get("actions"))
    devices = [
        {"platform": device.platform, "device_kind": device.device_kind, "id": int(device.id)}
        for device in jax.devices()
    ]
    return {
        "schema_version": REPORT_VERSION,
        "pass": True,
        "sample": {
            "canonical_ref": "gen2:libero_spatial/task-00/state-00/frame-000000",
            "suite": suite,
            "task_id": task_id,
            "state_index": state_index,
            "input_sha256": input_digest(element),
            "state_dim": int(np.asarray(element["observation/state"]).size),
            "main_image_shape": list(np.asarray(element["observation/image"]).shape),
            "wrist_image_shape": list(np.asarray(element["observation/wrist_image"]).shape),
            "prompt": element["prompt"],
        },
        "policy": {
            "policy_id": policy_entry["policy_id"],
            "openpi_revision": lock["openpi"]["revision"],
            "config": EXPECTED_CONFIG,
            "checkpoint_uri": EXPECTED_CHECKPOINT,
            "checkpoint_snapshot_sha256": lock["checkpoint"]["snapshot_sha256"],
            "materialized_object_count": materialization["object_count"],
            "materialized_total_bytes": materialization["total_bytes"],
        },
        "runtime": {
            "devices": devices,
            "load_seconds": round(load_seconds, 6),
            "inference_seconds": round(inference_seconds, 6),
        },
        "output": {
            "shape": list(actions.shape),
            "finite": bool(np.isfinite(actions).all()),
            "sha256": hashlib.sha256(np.ascontiguousarray(actions).tobytes()).hexdigest(),
            "first_action": [round(float(value), 8) for value in actions[0]],
        },
        "negative_gates": [
            "wrong suite checkpoint config rejected",
            "missing LIBERO norm stats rejected",
            "action dimension mismatch rejected",
            "non-finite action rejected",
        ],
        "claim_boundary": (
            "One actual π0.5-LIBERO inference compatibility probe; not a rollout success or policy ranking."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="GEN3 π0.5-LIBERO 실제 compatibility probe")
    parser.add_argument("--sample-dir", type=Path, required=True)
    parser.add_argument("--checkpoint-dir", type=Path, required=True)
    parser.add_argument("--lock", type=Path, default=DEFAULT_LOCK)
    parser.add_argument("--output", type=Path, default=HERE / "verify" / "pi05-probe-report.json")
    args = parser.parse_args()
    try:
        report = run_probe(sample_dir=args.sample_dir, checkpoint_dir=args.checkpoint_dir, lock_path=args.lock)
    except (ProbeContractError, FileNotFoundError, KeyError, TypeError, ValueError) as exc:
        print(f"pi05 probe: FAIL — {exc}")
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        "pi05 probe: PASS "
        f"({report['output']['shape'][0]}x{report['output']['shape'][1]}, "
        f"inference={report['runtime']['inference_seconds']}s)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
