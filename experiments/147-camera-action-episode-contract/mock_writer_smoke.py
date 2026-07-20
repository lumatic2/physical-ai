#!/usr/bin/env python3
"""Create and load a bounded synthetic episode through the official LeRobot backend."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from episode_profile import validate_profile
from libero_writer import LeRobotEpisodeWriter


REV_A = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
REV_B = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
REV_C = "cccccccccccccccccccccccccccccccccccccccc"


def synthetic_observation(frame_index: int, image_size: int) -> dict:
    main = np.zeros((image_size, image_size, 3), dtype=np.uint8)
    wrist = np.zeros_like(main)
    main[..., 0] = frame_index * 60
    wrist[..., 1] = 255 - frame_index * 60
    return {
        "agentview_image": main,
        "robot0_eye_in_hand_image": wrist,
        "robot0_eef_pos": np.array([0.1 + frame_index * 0.01, 0.2, 0.3], dtype=np.float32),
        "robot0_eef_quat": np.array([0.0, 0.0, 0.0, 1.0], dtype=np.float32),
        "robot0_gripper_qpos": np.array([0.01, 0.02], dtype=np.float32),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    from lerobot.datasets import LeRobotDataset

    image_size = 32
    repo_id = "physical-ai/lab1-writer-smoke"
    writer = LeRobotEpisodeWriter.create(
        root=args.root,
        repo_id=repo_id,
        fps=10,
        image_shape=(image_size, image_size, 3),
        dataset_revision=REV_A,
        environment_revision=REV_B,
        policy_revision=REV_C,
    )
    for frame_index in range(3):
        raw_action = np.linspace(0, 0.6, 7, dtype=np.float32) + frame_index * 0.01
        writer.add_executed_step(
            observation=synthetic_observation(frame_index, image_size),
            raw_policy_action=raw_action,
            executed_action=np.clip(raw_action, -1, 1),
            instruction="move the gripper toward the red marker",
            request_latency_ms=5.0 + frame_index,
        )
    sidecar_path = writer.save_episode(success=False, termination="timeout", reward=0.0)
    writer.close()

    info_path = args.root / "meta" / "info.json"
    info = json.loads(info_path.read_text(encoding="utf-8"))
    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    profile = validate_profile(info, sidecar, require_provenance=True)
    dataset = LeRobotDataset(repo_id, root=args.root, episodes=[0], video_backend="pyav", return_uint8=True)
    sample = dataset[0]
    report = {
        "pass": bool(profile["valid"] and len(dataset) == 3),
        "frames": len(dataset),
        "camera_keys": list(dataset.meta.camera_keys),
        "main_shape": list(sample["observation.images.image"].shape),
        "wrist_shape": list(sample["observation.images.image2"].shape),
        "state_shape": list(sample["observation.state"].shape),
        "action_shape": list(sample["action"].shape),
        "instruction": sample["task"],
        "video_backend": "pyav",
        "profile": profile,
        "sidecar": sidecar_path.relative_to(args.root).as_posix(),
    }
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
