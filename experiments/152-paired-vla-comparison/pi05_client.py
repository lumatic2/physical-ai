#!/usr/bin/env python3
"""Execute one exact π0.5-LIBERO cell and record a canonical LeRobot episode."""

from __future__ import annotations

import argparse
import collections
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
from libero.libero import benchmark, get_libero_path
from libero.libero.envs import OffScreenRenderEnv
from openpi_client import image_tools, websocket_client_policy

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
LAB1_DIR = REPO_ROOT / "experiments" / "147-camera-action-episode-contract"
if str(LAB1_DIR) not in sys.path:
    sys.path.insert(0, str(LAB1_DIR))

from libero_writer import (  # noqa: E402
    LeRobotEpisodeWriter,
    build_robot_state,
)

DUMMY_ACTION = [0.0] * 6 + [-1.0]
WAIT_STEPS = 10
RESOLUTION = 256
REPLAN_STEPS = 5
CHECKPOINT_SNAPSHOT = "11e0f560ebc9ca0f65d26241dd08e2ac07c22ee91455f1789afc2fc5c0378d7b"

# PyTorch 2.6+ defaults to weights_only=True, but pinned LIBERO init files contain
# trusted local NumPy objects rather than model weights.
_ORIGINAL_TORCH_LOAD = torch.load
torch.load = lambda *args, **kwargs: _ORIGINAL_TORCH_LOAD(  # type: ignore[assignment]
    *args, **{**kwargs, "weights_only": False}
)


def get_env(task: Any, seed: int) -> OffScreenRenderEnv:
    bddl = Path(get_libero_path("bddl_files")) / task.problem_folder / task.bddl_file
    env = OffScreenRenderEnv(bddl_file_name=bddl, camera_heights=RESOLUTION, camera_widths=RESOLUTION)
    env.seed(seed)
    return env


def policy_element(observation: dict[str, Any], instruction: str) -> dict[str, Any]:
    main = np.ascontiguousarray(observation["agentview_image"][::-1, ::-1])
    wrist = np.ascontiguousarray(observation["robot0_eye_in_hand_image"][::-1, ::-1])
    return {
        "observation/image": image_tools.convert_to_uint8(image_tools.resize_with_pad(main, 224, 224)),
        "observation/wrist_image": image_tools.convert_to_uint8(image_tools.resize_with_pad(wrist, 224, 224)),
        "observation/state": build_robot_state(observation),
        "prompt": instruction,
    }


def patch_sidecar(sidecar_path: Path, frame_metadata: list[dict[str, Any]]) -> None:
    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    sidecar["producer"]["policy"] = {"name": "pi0.5-libero", "revision": CHECKPOINT_SNAPSHOT}
    for camera in sidecar["camera_roles"].values():
        camera["model_input"] = True
    if len(sidecar["action_events"]) != len(frame_metadata):
        raise ValueError("action event/chunk metadata count mismatch")
    for action_event, metadata in zip(sidecar["action_events"], frame_metadata, strict=True):
        action_event.update(metadata)
    sidecar["policy_interface"] = {
        "config": "pi05_libero",
        "raw_chunk_shape": [10, 32],
        "exposed_chunk_shape": [10, 7],
        "executed_prefix_steps": REPLAN_STEPS,
        "gripper_transform": "none_after_checkpoint_denormalization",
    }
    temporary = sidecar_path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(sidecar, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, sidecar_path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", choices=("libero_spatial", "libero_object", "libero_goal"), required=True)
    parser.add_argument("--task-id", type=int, required=True)
    parser.add_argument("--state-index", type=int, required=True)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--max-policy-steps", type=int, required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--record-root", type=Path, required=True)
    parser.add_argument("--record-repo-id", required=True)
    parser.add_argument("--dataset-revision", required=True)
    parser.add_argument("--environment-revision", required=True)
    args = parser.parse_args()

    np.random.seed(args.seed)
    suite = benchmark.get_benchmark_dict()[args.suite]()
    task = suite.get_task(args.task_id)
    initial_states = suite.get_task_init_states(args.task_id)
    if args.state_index < 0 or args.state_index >= len(initial_states):
        parser.error("state index outside official LIBERO initial states")
    instruction = str(task.language)
    env = get_env(task, args.seed)
    client = websocket_client_policy.WebsocketClientPolicy(args.host, args.port)
    writer: LeRobotEpisodeWriter | None = None
    frame_metadata: list[dict[str, Any]] = []
    action_plan: collections.deque[tuple[np.ndarray, dict[str, Any]]] = collections.deque()
    request_latencies: list[float] = []
    success = False
    reward = 0.0
    steps = 0
    try:
        env.reset()
        observation = env.set_init_state(initial_states[args.state_index])
        for _ in range(WAIT_STEPS):
            observation, _, _, _ = env.step(DUMMY_ACTION)
        request_index = 0
        while steps < args.max_policy_steps:
            if not action_plan:
                started = time.perf_counter()
                result = client.infer(policy_element(observation, instruction))
                latency_ms = (time.perf_counter() - started) * 1000.0
                request_latencies.append(latency_ms)
                chunk = np.asarray(result["actions"], dtype=np.float32)
                if chunk.shape != (10, 7) or not np.isfinite(chunk).all():
                    raise ValueError(f"π0.5 action chunk must be finite 10x7, got {chunk.shape}")
                request_id = f"request-{request_index:06d}"
                for chunk_index, action in enumerate(chunk[:REPLAN_STEPS]):
                    action_plan.append(
                        (
                            action,
                            {
                                "request_id": request_id,
                                "chunk_index": chunk_index,
                                "is_request_step": chunk_index == 0,
                                "predicted_chunk_length": int(chunk.shape[0]),
                            },
                        )
                    )
                request_index += 1
            action, metadata = action_plan.popleft()
            pre_step = observation
            frame_latency = request_latencies[-1] if metadata["is_request_step"] else 0.0
            observation, reward, success, _ = env.step(action.tolist())
            if writer is None:
                writer = LeRobotEpisodeWriter.create(
                    root=args.record_root,
                    repo_id=args.record_repo_id,
                    fps=10,
                    image_shape=(RESOLUTION, RESOLUTION, 3),
                    dataset_revision=args.dataset_revision,
                    environment_revision=args.environment_revision,
                    policy_revision=CHECKPOINT_SNAPSHOT,
                )
            writer.add_executed_step(
                observation=pre_step,
                raw_policy_action=action,
                executed_action=action,
                instruction=instruction,
                request_latency_ms=frame_latency,
            )
            frame_metadata.append(metadata)
            steps += 1
            if success:
                break
        if writer is None:
            raise ValueError("π0.5 rollout produced no executable action")
        sidecar_path = writer.save_episode(
            success=bool(success),
            termination="success" if success else "timeout",
            reward=float(reward),
            rollout_context={
                "suite": args.suite,
                "task_id": args.task_id,
                "init_state_index": args.state_index,
                "environment_seed": args.seed,
                "max_policy_steps": args.max_policy_steps,
            },
        )
        writer.close()
        patch_sidecar(sidecar_path, frame_metadata)
    finally:
        env.close()

    summary = {
        "success": bool(success),
        "termination": "success" if success else "timeout",
        "frames": steps,
        "request_count": len(request_latencies),
        "request_latency_ms": {
            "total": round(sum(request_latencies), 6),
            "minimum": round(min(request_latencies), 6),
            "maximum": round(max(request_latencies), 6),
        },
    }
    print("PI05_RESULT " + json.dumps(summary, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
