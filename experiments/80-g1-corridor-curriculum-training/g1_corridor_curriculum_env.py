"""Corridor curriculum rewards for the G1 visible squat gate."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import jax
import jax.numpy as jp
from ml_collections import config_dict


ROOT = Path(__file__).resolve().parents[2]
EXP50 = ROOT / "experiments/50-g1-stance-constrained-curriculum-ppo"
if str(EXP50) not in sys.path:
    sys.path.insert(0, str(EXP50))

from g1_stance_constrained_env import StanceConstrainedCommandSquat, stance_scales  # noqa: E402


def corridor_scales() -> config_dict.ConfigDict:
    scales = stance_scales()
    scales.corridor_visible_drop = 12.0
    scales.corridor_knee_flexion = 8.0
    scales.corridor_hip_pitch = 5.0
    scales.corridor_support_margin = 4.0
    scales.corridor_terminal_stand = 3.0
    return scales


class CorridorCurriculumSquat(StanceConstrainedCommandSquat):
    """Keeps exp50 compatibility while rewarding the exp29 visible-squat corridor."""

    def __init__(
        self,
        *args,
        target_drop: float = 0.078,
        target_knee_delta: float = 0.60,
        target_hip_delta: float = 0.35,
        **kwargs,
    ):
        super().__init__(*args, target_drop=target_drop, **kwargs)
        self._target_knee_delta = float(target_knee_delta)
        self._target_hip_delta = float(target_hip_delta)
        self._config.reward_config.scales = corridor_scales()
        self._start_qpos = jp.asarray(self._mj_model.keyframe("knees_bent").qpos, dtype=jp.float32)
        self._start_height = float(self._mj_model.keyframe("knees_bent").qpos[2])
        self._left_knee_qpos = int(self._mj_model.jnt_qposadr[self._mj_model.joint("left_knee_joint").id])
        self._right_knee_qpos = int(self._mj_model.jnt_qposadr[self._mj_model.joint("right_knee_joint").id])
        self._left_hip_qpos = int(self._mj_model.jnt_qposadr[self._mj_model.joint("left_hip_pitch_joint").id])
        self._right_hip_qpos = int(self._mj_model.jnt_qposadr[self._mj_model.joint("right_hip_pitch_joint").id])

    def reset(self, rng: jax.Array):
        state = super().reset(rng)
        for key in [
            "corridor_visible_drop",
            "corridor_knee_flexion",
            "corridor_hip_pitch",
            "corridor_support_margin",
            "corridor_terminal_stand",
            "corridor_drop_m",
            "corridor_knee_delta_rad",
            "corridor_hip_delta_rad",
            "corridor_target_pose_norm",
        ]:
            state.metrics[key] = jp.zeros(())
        return state

    def _pose_deltas(self, data) -> tuple[jax.Array, jax.Array]:
        knee_delta = jp.maximum(
            jp.abs(data.qpos[self._left_knee_qpos] - self._start_qpos[self._left_knee_qpos]),
            jp.abs(data.qpos[self._right_knee_qpos] - self._start_qpos[self._right_knee_qpos]),
        )
        hip_delta = jp.maximum(
            jp.abs(data.qpos[self._left_hip_qpos] - self._start_qpos[self._left_hip_qpos]),
            jp.abs(data.qpos[self._right_hip_qpos] - self._start_qpos[self._right_hip_qpos]),
        )
        return knee_delta, hip_delta

    def _get_reward(
        self,
        data,
        action: jax.Array,
        info: dict[str, Any],
        metrics: dict[str, Any],
        done: jax.Array,
        first_contact: jax.Array,
        contact: jax.Array,
    ) -> dict[str, jax.Array]:
        rewards = super()._get_reward(data, action, info, metrics, done, first_contact, contact)
        knee_delta, hip_delta = self._pose_deltas(data)
        visible_drop = jp.clip(jp.asarray(self._start_height, dtype=jp.float32) - data.qpos[2], 0.0, 0.20)
        drop_progress = jp.clip(visible_drop / jp.asarray(self._target_drop, dtype=jp.float32), 0.0, 1.0)
        knee_progress = jp.clip(knee_delta / jp.asarray(self._target_knee_delta, dtype=jp.float32), 0.0, 1.0)
        hip_progress = jp.clip(hip_delta / jp.asarray(self._target_hip_delta, dtype=jp.float32), 0.0, 1.0)
        support_margin = self._support_margin(data)
        support_progress = jp.clip((support_margin - self._support_floor) / 0.035, 0.0, 1.0)
        target_pose, _, cmd = self._command_target_pose(info["step"])
        terminal_stand = cmd[1] * jp.exp(-90.0 * jp.square(data.qpos[2] - self.stand_height))

        rewards.update({
            "corridor_visible_drop": drop_progress * drop_progress,
            "corridor_knee_flexion": knee_progress * knee_progress,
            "corridor_hip_pitch": hip_progress * hip_progress,
            "corridor_support_margin": support_progress,
            "corridor_terminal_stand": terminal_stand,
        })
        metrics["corridor_visible_drop"] = rewards["corridor_visible_drop"]
        metrics["corridor_knee_flexion"] = rewards["corridor_knee_flexion"]
        metrics["corridor_hip_pitch"] = rewards["corridor_hip_pitch"]
        metrics["corridor_support_margin"] = support_progress
        metrics["corridor_terminal_stand"] = terminal_stand
        metrics["corridor_drop_m"] = visible_drop
        metrics["corridor_knee_delta_rad"] = knee_delta
        metrics["corridor_hip_delta_rad"] = hip_delta
        metrics["corridor_target_pose_norm"] = jp.linalg.norm(target_pose)
        return rewards
