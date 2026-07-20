#!/usr/bin/env python3
"""LeRobot v3 writer adapter for successful LIBERO controller steps."""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any, Callable

import numpy as np

from episode_profile import validate_profile


MAIN_CAMERA_KEY = "agentview_image"
MAIN_FEATURE = "observation.images.image"
WRIST_FEATURE = "observation.images.image2"
WRIST_CAMERA_CANDIDATES = (
    "robot0_eye_in_hand_image",
    "eye_in_hand_image",
    "robot0_eye_in_hand",
)
STATE_NAMES = (
    "eef_x",
    "eef_y",
    "eef_z",
    "eef_axis_x",
    "eef_axis_y",
    "eef_axis_z",
    "gripper_left",
    "gripper_right",
)
ACTION_NAMES = ("dx", "dy", "dz", "droll", "dpitch", "dyaw", "gripper")


def quaternion_to_axis_angle(quaternion: Any) -> np.ndarray:
    quat = np.asarray(quaternion, dtype=np.float64)
    if quat.shape != (4,) or not np.isfinite(quat).all():
        raise ValueError("robot0_eef_quat must be a finite 4D quaternion")
    norm = float(np.linalg.norm(quat))
    if norm <= 1e-12:
        raise ValueError("robot0_eef_quat must have non-zero norm")
    quat = quat / norm
    if quat[3] < 0:
        quat = -quat
    scalar = float(np.clip(quat[3], -1.0, 1.0))
    denominator = math.sqrt(max(1.0 - scalar * scalar, 0.0))
    if denominator <= 1e-8:
        return np.zeros(3, dtype=np.float32)
    return ((quat[:3] * (2.0 * math.acos(scalar))) / denominator).astype(np.float32)


def build_robot_state(observation: dict[str, Any]) -> np.ndarray:
    required = ("robot0_eef_pos", "robot0_eef_quat", "robot0_gripper_qpos")
    missing = [key for key in required if key not in observation]
    if missing:
        raise ValueError(f"missing robot state keys: {', '.join(missing)}")
    state = np.concatenate(
        (
            np.asarray(observation["robot0_eef_pos"], dtype=np.float32),
            quaternion_to_axis_angle(observation["robot0_eef_quat"]),
            np.asarray(observation["robot0_gripper_qpos"], dtype=np.float32),
        )
    ).astype(np.float32)
    if state.shape != (8,) or not np.isfinite(state).all():
        raise ValueError("LIBERO robot state must be finite and 8D")
    return state


def discover_wrist_camera_key(observation: dict[str, Any]) -> str:
    for key in WRIST_CAMERA_CANDIDATES:
        if key in observation:
            return key
    inferred = sorted(
        key
        for key in observation
        if "eye_in_hand" in key.lower() and "image" in key.lower()
    )
    if len(inferred) == 1:
        return inferred[0]
    if not inferred:
        raise ValueError("LIBERO wrist camera observation is missing")
    raise ValueError(f"LIBERO wrist camera observation is ambiguous: {', '.join(inferred)}")


def _finite_vector(value: Any, shape: tuple[int, ...], name: str) -> np.ndarray:
    vector = np.asarray(value, dtype=np.float32)
    if vector.shape != shape or not np.isfinite(vector).all():
        raise ValueError(f"{name} must be finite with shape {shape}")
    return vector


def _uint8_image(value: Any, shape: tuple[int, int, int], name: str) -> np.ndarray:
    image = np.asarray(value)
    if image.shape != shape:
        raise ValueError(f"{name} must have shape {shape}, got {image.shape}")
    if image.dtype != np.uint8:
        raise ValueError(f"{name} must use uint8 HWC pixels")
    return np.ascontiguousarray(image)


def _action_hash(action: np.ndarray) -> str:
    return hashlib.sha256(np.asarray(action, dtype="<f4").tobytes()).hexdigest()


def build_features(image_shape: tuple[int, int, int]) -> dict[str, dict[str, Any]]:
    if len(image_shape) != 3 or image_shape[2] != 3:
        raise ValueError("LeRobot RGB cameras require HWC shape with 3 channels")
    return {
        MAIN_FEATURE: {
            "dtype": "video",
            "shape": image_shape,
            "names": ["height", "width", "channels"],
            "info": {"is_depth_map": False},
        },
        WRIST_FEATURE: {
            "dtype": "video",
            "shape": image_shape,
            "names": ["height", "width", "channels"],
            "info": {"is_depth_map": False},
        },
        "observation.state": {
            "dtype": "float32",
            "shape": (8,),
            "names": list(STATE_NAMES),
        },
        "action": {
            "dtype": "float32",
            "shape": (7,),
            "names": list(ACTION_NAMES),
        },
    }


class LeRobotEpisodeWriter:
    def __init__(
        self,
        *,
        dataset: Any,
        root: Path,
        repo_id: str,
        fps: int,
        image_shape: tuple[int, int, int],
        dataset_revision: str,
        environment_revision: str,
        policy_revision: str,
    ) -> None:
        self.dataset = dataset
        self.root = root
        self.repo_id = repo_id
        self.fps = fps
        self.image_shape = image_shape
        self.dataset_revision = dataset_revision
        self.environment_revision = environment_revision
        self.policy_revision = policy_revision
        self.episode_index = 0
        self.frame_count = 0
        self.action_events: list[dict[str, Any]] = []
        self.wrist_camera_key: str | None = None

    @classmethod
    def create(
        cls,
        *,
        root: Path,
        repo_id: str,
        fps: int,
        image_shape: tuple[int, int, int],
        dataset_revision: str,
        environment_revision: str,
        policy_revision: str,
        dataset_factory: Callable[..., Any] | None = None,
    ) -> "LeRobotEpisodeWriter":
        if dataset_factory is None:
            from lerobot.datasets import LeRobotDataset

            dataset_factory = LeRobotDataset.create
        root = Path(root)
        dataset = dataset_factory(
            repo_id=repo_id,
            fps=fps,
            features=build_features(image_shape),
            root=root,
            robot_type="libero-panda-sim",
            use_videos=True,
            image_writer_threads=0,
            video_backend="pyav",
        )
        return cls(
            dataset=dataset,
            root=root,
            repo_id=repo_id,
            fps=fps,
            image_shape=image_shape,
            dataset_revision=dataset_revision,
            environment_revision=environment_revision,
            policy_revision=policy_revision,
        )

    def add_executed_step(
        self,
        *,
        observation: dict[str, Any],
        raw_policy_action: Any,
        executed_action: Any,
        instruction: str,
        request_latency_ms: float,
    ) -> None:
        if not isinstance(instruction, str) or not instruction.strip():
            raise ValueError("instruction must be a non-empty string")
        if not math.isfinite(request_latency_ms) or request_latency_ms < 0:
            raise ValueError("request_latency_ms must be finite and non-negative")

        wrist_key = discover_wrist_camera_key(observation)
        if self.wrist_camera_key is None:
            self.wrist_camera_key = wrist_key
        elif wrist_key != self.wrist_camera_key:
            raise ValueError(
                f"wrist camera source changed from {self.wrist_camera_key} to {wrist_key}"
            )

        main_image = _uint8_image(observation[MAIN_CAMERA_KEY], self.image_shape, MAIN_CAMERA_KEY)
        wrist_image = _uint8_image(observation[wrist_key], self.image_shape, wrist_key)
        state = build_robot_state(observation)
        raw_action = _finite_vector(raw_policy_action, (7,), "raw_policy_action")
        controller_action = _finite_vector(executed_action, (7,), "executed_action")
        frame_index = self.frame_count

        self.dataset.add_frame(
            {
                MAIN_FEATURE: main_image,
                WRIST_FEATURE: wrist_image,
                "observation.state": state,
                "action": controller_action,
                "task": instruction.strip(),
            }
        )
        self.action_events.append(
            {
                "frame_index": frame_index,
                "timestamp_seconds": frame_index / self.fps,
                "raw_policy_action": raw_action.tolist(),
                "request_latency_ms": round(float(request_latency_ms), 6),
                "executed_action_sha256": _action_hash(controller_action),
            }
        )
        self.frame_count += 1

    def _profile_info(self) -> dict[str, Any]:
        features = build_features(self.image_shape)
        features["timestamp"] = {"dtype": "float32", "shape": [1], "names": None}
        features["task_index"] = {"dtype": "int64", "shape": [1], "names": None}
        return {
            "codebase_version": "v3.0",
            "fps": self.fps,
            "features": features,
        }

    def _sidecar(
        self,
        *,
        success: bool,
        termination: str,
        reward: float,
        error_code: str | None,
    ) -> dict[str, Any]:
        return {
            "schema_version": "physical-ai-provenance-v1",
            "episode": {
                "format": "lerobot-v3",
                "repo_id": self.repo_id,
                "revision": self.dataset_revision,
                "index": self.episode_index,
            },
            "producer": {
                "environment": {"name": "libero", "revision": self.environment_revision},
                "policy": {"name": "openvla", "revision": self.policy_revision},
            },
            "camera_roles": {
                MAIN_FEATURE: {
                    "role": "main",
                    "source_key": MAIN_CAMERA_KEY,
                    "model_input": True,
                },
                WRIST_FEATURE: {
                    "role": "wrist",
                    "source_key": self.wrist_camera_key,
                    "model_input": False,
                },
            },
            "claims": {"recording_mode": "recorded", "world": "simulation"},
            "action_events": self.action_events,
            "outcome": {
                "success": bool(success),
                "termination": termination,
                "reward": float(reward),
                "error_code": error_code,
            },
        }

    def save_episode(
        self,
        *,
        success: bool,
        termination: str,
        reward: float,
        error_code: str | None = None,
    ) -> Path:
        if self.frame_count == 0:
            raise ValueError("cannot save an empty LeRobot episode")
        if len(self.action_events) != self.frame_count:
            raise ValueError("camera/action timestep count mismatch")
        if termination not in {"success", "timeout", "error"}:
            raise ValueError("termination must be success, timeout, or error")
        if not math.isfinite(reward):
            raise ValueError("reward must be finite")
        sidecar = self._sidecar(
            success=success,
            termination=termination,
            reward=reward,
            error_code=error_code,
        )
        report = validate_profile(self._profile_info(), sidecar, require_provenance=True)
        if not report["valid"]:
            raise ValueError(f"provenance sidecar failed profile: {report['errors']}")

        # Windows process-spawn can strand the two-camera ProcessPool encoder.
        # Official API supports sequential encoding, which is slower but deterministic.
        self.dataset.save_episode(parallel_encoding=False)
        sidecar_dir = self.root / "meta" / "lab_provenance"
        sidecar_dir.mkdir(parents=True, exist_ok=True)
        sidecar_path = sidecar_dir / f"episode_{self.episode_index:06d}.json"
        temp_path = sidecar_path.with_suffix(".json.tmp")
        temp_path.write_text(json.dumps(sidecar, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(temp_path, sidecar_path)

        self.episode_index += 1
        self.frame_count = 0
        self.action_events = []
        return sidecar_path

    def abort_episode(self) -> None:
        if self.frame_count:
            self.dataset.clear_episode_buffer()
        self.frame_count = 0
        self.action_events = []

    def close(self) -> None:
        if self.frame_count:
            raise RuntimeError("unsaved frames remain; save or abort the episode before close")
        self.dataset.finalize()
