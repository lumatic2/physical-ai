#!/usr/bin/env python3
"""Execute an allowlisted VLM-selected skill and emit an assisted causal trace."""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any

import numpy as np

from direct_vla import load_episode_rows
from event_schema import validate_event_stream
from vlm_runner import validate_vlm_decision


SUPPORTED_BINDINGS = {("pick_and_place", "black_bowl", "plate"): "canonical_action_replay"}


def validate_skill_binding(decision: Any) -> dict[str, str]:
    report = validate_vlm_decision(decision)
    if not report["valid"]:
        raise ValueError(f"invalid VLM decision: {report['errors']}")
    skill = decision["selected_skill"]
    key = (skill["name"], skill["target"], skill["destination"])
    implementation = SUPPORTED_BINDINGS.get(key)
    if implementation is None:
        raise ValueError(f"unsupported_skill_binding:{key}")
    return {**skill, "implementation": implementation}


def execute_canonical_skill(
    *, vlm_record: dict[str, Any], dataset_root: Path, sidecar: dict[str, Any]
) -> dict[str, Any]:
    binding = validate_skill_binding(vlm_record["decision"])
    rows = load_episode_rows(dataset_root, int(sidecar["episode"]["index"]))
    if not rows:
        raise ValueError("canonical skill source has no actions")

    os.environ.setdefault("MUJOCO_GL", "egl")
    import torch
    from libero.libero import benchmark, get_libero_path
    from libero.libero.envs import OffScreenRenderEnv

    original_load = torch.load
    torch.load = lambda *args, **kwargs: original_load(*args, **{**kwargs, "weights_only": False})
    rollout = sidecar["rollout"]
    suite = benchmark.get_benchmark_dict()[rollout["suite"]]()
    task = suite.get_task(int(rollout["task_id"]))
    init_states = suite.get_task_init_states(int(rollout["task_id"]))
    bddl = os.path.join(get_libero_path("bddl_files"), task.problem_folder, task.bddl_file)
    env = OffScreenRenderEnv(bddl_file_name=bddl, camera_heights=256, camera_widths=256)
    env.seed(int(rollout["environment_seed"]))
    env.reset()
    env.set_init_state(init_states[int(rollout["init_state_index"])])
    for _ in range(10):
        env.step([0, 0, 0, 0, 0, 0, -1])

    started = time.perf_counter()
    success = False
    reward = 0.0
    executed_hashes: list[str] = []
    try:
        for row, action_event in zip(rows, sidecar["action_events"], strict=True):
            action = np.asarray(row["action"], dtype=np.float32)
            _, reward, success, _ = env.step(action.tolist())
            executed_hashes.append(action_event["executed_action_sha256"])
            if success:
                break
    finally:
        env.close()
        torch.load = original_load
    latency_ms = (time.perf_counter() - started) * 1000.0
    return {
        "schema_version": "physical-ai-bounded-skill-result-v1",
        "skill": binding,
        "assistance": {"used": True, "source": "scripted_skill"},
        "action_source": {
            "kind": "canonical_action_replay",
            "dataset_revision": sidecar["episode"]["revision"],
            "episode_index": sidecar["episode"]["index"],
        },
        "rollout": rollout,
        "environment": sidecar["producer"]["environment"],
        "actions_requested": len(rows),
        "actions_executed": len(executed_hashes),
        "executed_action_hashes": executed_hashes,
        "outcome": {
            "success": bool(success),
            "termination": "success" if success else "timeout",
            "reward": float(reward),
            "measured": True,
            "latency_ms": round(latency_ms, 3),
        },
        "claim_boundary": "VLM selected an allowlisted skill; a scripted canonical action replay executed it in LIBERO simulation",
    }


def build_vlm_skill_stream(
    *, vlm_record: dict[str, Any], execution: dict[str, Any], sidecar: dict[str, Any]
) -> dict[str, Any]:
    decision = vlm_record["decision"]
    model = vlm_record["model"]
    environment = execution["environment"]
    episode = sidecar["episode"]
    inference_sec = float(vlm_record["generation"]["latency_ms"]) / 1000.0
    execution_sec = inference_sec + float(execution["outcome"]["latency_ms"]) / 1000.0
    events = [
        {
            "id": "sensor-frame-000000",
            "timestep": 0,
            "timestamp_sec": 0.0,
            "source": "sensor",
            "kind": "model_input_observation",
            "causal_role": "observation",
            "parents": [],
            "model_or_component": environment,
            "payload_ref": f"lerobot://episode/{episode['index']}/frame/0/observation.images.image",
            "payload": {"image_sha256": vlm_record["input"]["image_sha256"], "instruction": vlm_record["input"]["instruction"]},
            "assistance": {"used": False, "source": "none"},
        },
        {
            "id": "vlm-scene-observation",
            "timestep": 0,
            "timestamp_sec": inference_sec,
            "source": "vlm",
            "kind": "structured_scene_observation",
            "causal_role": "observation",
            "parents": ["sensor-frame-000000"],
            "model_or_component": {"name": model["name"], "revision": model["revision"]},
            "payload_ref": "vlm-record://decision/scene",
            "payload": decision["scene"],
            "assistance": {"used": False, "source": "none"},
        },
        {
            "id": "vlm-skill-selection",
            "timestep": 0,
            "timestamp_sec": inference_sec,
            "source": "vlm",
            "kind": "bounded_skill_selection",
            "causal_role": "decision",
            "parents": ["vlm-scene-observation"],
            "model_or_component": {"name": model["name"], "revision": model["revision"]},
            "payload_ref": "vlm-record://decision/selected_skill",
            "payload": {**decision["selected_skill"], "confidence": decision["confidence"]},
            "assistance": {"used": False, "source": "none"},
        },
        {
            "id": "controller-skill-execution",
            "timestep": 0,
            "timestamp_sec": inference_sec,
            "source": "controller",
            "kind": "scripted_skill_execution",
            "causal_role": "execution",
            "parents": ["vlm-skill-selection"],
            "model_or_component": {"name": "canonical-action-replay", "revision": episode["revision"]},
            "payload_ref": "skill-result://executed_action_hashes",
            "payload": {
                "skill": execution["skill"],
                "actions_requested": execution["actions_requested"],
                "actions_executed": execution["actions_executed"],
                "action_source": execution["action_source"],
            },
            "assistance": {"used": True, "source": "scripted_skill"},
        },
        {
            "id": "environment-skill-outcome",
            "timestep": execution["actions_executed"] - 1,
            "timestamp_sec": execution_sec,
            "source": "environment",
            "kind": "measured_skill_outcome",
            "causal_role": "result",
            "parents": ["controller-skill-execution"],
            "model_or_component": environment,
            "payload_ref": "skill-result://outcome",
            "payload": execution["outcome"],
            "assistance": {"used": True, "source": "scripted_skill"},
        },
    ]
    return {
        "schema_version": "physical-ai-causal-events-v1",
        "episode_ref": {"dataset_revision": episode["revision"], "episode_index": episode["index"]},
        "lane": "vlm_skill",
        "claim_boundary": "local auxiliary VLM selected a bounded skill; scripted action replay executed it in LIBERO simulation",
        "events": events,
    }


def validate_vlm_skill_trace(stream: dict[str, Any], execution: dict[str, Any]) -> dict[str, Any]:
    base = validate_event_stream(stream)
    errors = list(base["errors"])
    events = stream.get("events", [])
    expected_sources = ["sensor", "vlm", "vlm", "controller", "environment"]
    if [event.get("source") for event in events] != expected_sources:
        errors.append("vlm_skill_source_chain_mismatch")
    if stream.get("lane") != "vlm_skill":
        errors.append("lane_not_vlm_skill")
    if len(events) == 5:
        for index in (3, 4):
            if events[index].get("assistance") != {"used": True, "source": "scripted_skill"}:
                errors.append(f"event[{index}]:scripted_assistance_missing")
        if events[2].get("parents") != [events[1].get("id")] or events[3].get("parents") != [events[2].get("id")]:
            errors.append("skill_parent_chain_mismatch")
        if events[4].get("payload") != execution.get("outcome"):
            errors.append("skill_outcome_drift")
    if execution.get("actions_executed", 0) < 1:
        errors.append("no_controller_actions_executed")
    if execution.get("outcome", {}).get("measured") is not True:
        errors.append("outcome_not_measured")
    return {"valid": not errors, "errors": errors, "events": len(events), "actions_executed": execution.get("actions_executed", 0)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vlm-record", type=Path, required=True)
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--sidecar", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--events", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    vlm_record = json.loads(args.vlm_record.read_text(encoding="utf-8"))
    sidecar = json.loads(args.sidecar.read_text(encoding="utf-8"))
    execution = execute_canonical_skill(vlm_record=vlm_record, dataset_root=args.dataset_root, sidecar=sidecar)
    stream = build_vlm_skill_stream(vlm_record=vlm_record, execution=execution, sidecar=sidecar)
    report = validate_vlm_skill_trace(stream, execution)
    if not report["valid"]:
        raise ValueError(f"VLM skill trace failed validation: {report['errors']}")
    for path, value in ((args.result, execution), (args.events, stream), (args.report, report)):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({**report, "outcome": execution["outcome"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
