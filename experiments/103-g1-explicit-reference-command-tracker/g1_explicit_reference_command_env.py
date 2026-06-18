"""Explicit foot-fixed visible reference command target for G1 squat PPO."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import jax
import jax.numpy as jp
from ml_collections import config_dict


ROOT = Path(__file__).resolve().parents[2]
EXP36_PATH = ROOT / "experiments/36-g1-wbc-ik-squat-prototype/run_ik_squat.py"
EXP80 = ROOT / "experiments/80-g1-corridor-curriculum-training"
if str(EXP80) not in sys.path:
    sys.path.insert(0, str(EXP80))

from g1_corridor_curriculum_env import CorridorCurriculumSquat  # noqa: E402


def load_exp36():
    spec = importlib.util.spec_from_file_location("exp36_wbc_ik", EXP36_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {EXP36_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EXP36 = load_exp36()


def explicit_reference_scales() -> config_dict.ConfigDict:
    scales = CorridorCurriculumSquat(config_overrides={"impl": "jax"})._config.reward_config.scales
    scales.corridor_visible_drop = 10.0
    scales.corridor_knee_flexion = 14.0
    scales.corridor_hip_pitch = 8.0
    scales.corridor_support_margin = 7.0
    scales.corridor_terminal_stand = 5.0
    scales.command_pose_tracking = 12.0
    scales.command_height_tracking = 10.0
    scales.command_action_target = 3.0
    scales.foot_slip_gate = 10.0
    scales.support_termination_margin = 5.0
    return scales


class ExplicitReferenceCommandSquat(CorridorCurriculumSquat):
    """Checkpoint-compatible command policy trained against an explicit visible reference."""

    def __init__(
        self,
        *args,
        reference_drop: float = 0.09,
        target_knee_delta: float = 0.64,
        target_hip_delta: float = 0.38,
        **kwargs,
    ):
        super().__init__(
            *args,
            target_drop=reference_drop,
            target_knee_delta=target_knee_delta,
            target_hip_delta=target_hip_delta,
            **kwargs,
        )
        self._reference_drop = float(reference_drop)
        self._target_knee_delta = float(target_knee_delta)
        self._target_hip_delta = float(target_hip_delta)
        key = self._mj_model.keyframe("knees_bent")
        foot_site_ids = self._feet_site_id
        ik = EXP36.solve_foot_fixed_target(self._mj_model, key.qpos.copy(), foot_site_ids, self._reference_drop)
        target = jp.asarray(self._default_pose, dtype=jp.float32)
        target = target.at[:15].set(jp.asarray(ik["lower_body_target"], dtype=jp.float32))
        target = target.at[3].set(self._default_pose[3] + self._target_knee_delta)
        target = target.at[9].set(self._default_pose[9] + self._target_knee_delta)
        target = target.at[0].set(self._default_pose[0] - self._target_hip_delta)
        target = target.at[6].set(self._default_pose[6] - self._target_hip_delta)
        lo = jp.asarray(self._mj_model.actuator_ctrlrange[:, 0], dtype=jp.float32)
        hi = jp.asarray(self._mj_model.actuator_ctrlrange[:, 1], dtype=jp.float32)
        target = jp.clip(target, lo, hi)
        self._explicit_visible_delta = target - jp.asarray(self._default_pose, dtype=jp.float32)
        self._explicit_target_height = float(ik["target_height"])
        self._config.reward_config.scales = explicit_reference_scales()

    def reset(self, rng: jax.Array):
        state = super().reset(rng)
        state.metrics["explicit_reference_drop"] = jp.zeros(())
        state.metrics["explicit_target_height"] = jp.zeros(())
        return state

    def _command_target_pose(self, step: jax.Array):
        cmd = self._squat_command(step)
        target_drop = cmd[0] * jp.asarray(self._reference_drop, dtype=jp.float32)
        target_height = jp.asarray(self.stand_height, dtype=jp.float32) - target_drop
        target_pose = jp.asarray(self._default_pose, dtype=jp.float32) + cmd[2] * self._explicit_visible_delta
        return target_pose, target_height, cmd

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
        support_margin = self._support_margin(data)
        foot_slip = self._foot_slip(data, info)
        rewards["foot_slip_gate"] = jp.where(foot_slip <= self._slip_limit, 1.0, 0.0)
        rewards["support_termination_margin"] = jp.where(support_margin >= self._support_floor, 1.0, 0.0)
        metrics["explicit_reference_drop"] = jp.asarray(self._reference_drop, dtype=jp.float32)
        metrics["explicit_target_height"] = jp.asarray(self._explicit_target_height, dtype=jp.float32)
        return rewards
