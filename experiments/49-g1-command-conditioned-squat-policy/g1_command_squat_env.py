"""Command-conditioned G1 visible squat environment."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import jax
import jax.numpy as jp
from ml_collections import config_dict


ROOT = Path(__file__).resolve().parents[2]
EXP46 = ROOT / "experiments/46-g1-force-torque-residual"
if str(EXP46) not in sys.path:
    sys.path.insert(0, str(EXP46))

from g1_force_torque_env import ForceTorqueAwareSquat  # noqa: E402


EXP45_BEST = ROOT / "experiments/45-g1-stance-stable-manifold/verify/attempts/drop-0p12-com12-posture0p3/result.json"


def command_scales() -> config_dict.ConfigDict:
    scales = ForceTorqueAwareSquat(config_overrides={"impl": "jax"})._config.reward_config.scales
    scales.command_pose_tracking = 8.0
    scales.command_height_tracking = 10.0
    scales.command_action_target = 7.0
    scales.command_return = 4.0
    scales.command_progress = 3.0
    scales.command_support_gate = 5.0
    return scales


def load_visible_delta(default_pose) -> tuple[jax.Array, float]:
    payload = json.loads(EXP45_BEST.read_text(encoding="utf-8"))
    lower = jp.asarray(payload["native"]["target"]["lower_body_target"], dtype=jp.float32)
    target = jp.asarray(default_pose, dtype=jp.float32)
    target = target.at[:15].set(lower)
    nominal_drop = float(payload["native"]["target"].get("pelvis_drop", 0.12))
    return target - jp.asarray(default_pose, dtype=jp.float32), nominal_drop


class CommandConditionedSquat(ForceTorqueAwareSquat):
    """Squat policy that observes a target command instead of receiving target injection."""

    foot_half_x = 0.09
    foot_half_y = 0.03

    def __init__(
        self,
        *args,
        target_drop: float = 0.08,
        descend_s: float = 2.6,
        hold_s: float = 0.4,
        return_s: float = 1.4,
        **kwargs,
    ):
        super().__init__(
            *args,
            stage_height=0.67,
            controller_blend=0.0,
            freeze_phase=True,
            blend_schedule="squat",
            reference_scale=1.0,
            **kwargs,
        )
        self._target_drop = float(target_drop)
        self._descend_s = float(descend_s)
        self._hold_s = float(hold_s)
        self._return_s = float(return_s)
        self._visible_delta, self._nominal_visible_drop = load_visible_delta(self._default_pose)
        self._config.reward_config.scales = command_scales()

    def _target_fraction(self, step: jax.Array) -> jax.Array:
        t = jp.asarray(step, dtype=jp.float32) * self.dt
        descend = jp.clip(t / jp.asarray(self._descend_s, dtype=jp.float32), 0.0, 1.0)
        return_start = jp.asarray(self._descend_s + self._hold_s, dtype=jp.float32)
        return_phase = jp.clip((t - return_start) / jp.asarray(self._return_s, dtype=jp.float32), 0.0, 1.0)
        return jp.where(t < return_start, descend, 1.0 - return_phase)

    def _squat_command(self, step: jax.Array) -> jax.Array:
        fraction = self._target_fraction(step)
        t = jp.asarray(step, dtype=jp.float32) * self.dt
        return_phase = jp.clip(
            (t - jp.asarray(self._descend_s + self._hold_s, dtype=jp.float32)) / jp.asarray(self._return_s, dtype=jp.float32),
            0.0,
            1.0,
        )
        visible_gain = fraction * jp.asarray(self._target_drop / self._nominal_visible_drop, dtype=jp.float32)
        return jp.array([fraction, return_phase, visible_gain], dtype=jp.float32)

    def _command_target_pose(self, step: jax.Array) -> tuple[jax.Array, jax.Array, jax.Array]:
        cmd = self._squat_command(step)
        target_drop = cmd[0] * jp.asarray(self._target_drop, dtype=jp.float32)
        target_height = jp.asarray(self.stand_height, dtype=jp.float32) - target_drop
        target_pose = self._default_pose + cmd[2] * self._visible_delta
        return target_pose, target_height, cmd

    def reset(self, rng: jax.Array):
        state = super().reset(rng)
        state.info["command"] = self._squat_command(jp.asarray(0, dtype=jp.int32))
        state.metrics["command_target_fraction"] = jp.zeros(())
        state.metrics["command_return_phase"] = jp.zeros(())
        state.metrics["command_visible_gain"] = jp.zeros(())
        state.metrics["command_target_height"] = jp.zeros(())
        state.metrics["command_pose_tracking"] = jp.zeros(())
        state.metrics["command_height_tracking"] = jp.zeros(())
        state.metrics["command_action_target"] = jp.zeros(())
        state.metrics["command_progress"] = jp.zeros(())
        state.metrics["command_support_gate"] = jp.zeros(())
        state.metrics["command_support_margin"] = jp.zeros(())
        return state.replace(obs=self._get_obs(state.data, state.info, state.info["last_contact"]))

    def step(self, state, action: jax.Array):
        state.info["command"] = self._squat_command(state.info["step"])
        return super().step(state, action)

    def _support_margin(self, data) -> jax.Array:
        feet_xy = data.site_xpos[self._feet_site_id, :2]
        min_xy = jp.min(feet_xy, axis=0) - jp.array([self.foot_half_x, self.foot_half_y])
        max_xy = jp.max(feet_xy, axis=0) + jp.array([self.foot_half_x, self.foot_half_y])
        com_xy = data.subtree_com[0, :2]
        margins = jp.array([
            com_xy[0] - min_xy[0],
            max_xy[0] - com_xy[0],
            com_xy[1] - min_xy[1],
            max_xy[1] - com_xy[1],
        ])
        return jp.min(margins)

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
        target_pose, target_height, cmd = self._command_target_pose(info["step"])
        lower_error = jp.mean(jp.square(data.qpos[7:22] - target_pose[:15]))
        height_error = jp.square(data.qpos[2] - target_height)
        desired_action = jp.clip((target_pose - self._default_pose) / self._config.action_scale, -1.0, 1.0)
        action_error = jp.mean(jp.square(action - desired_action))
        actual_drop = jp.clip(jp.asarray(self.stand_height, dtype=jp.float32) - data.qpos[2], 0.0, self._target_drop)
        target_drop = jp.maximum(cmd[0] * self._target_drop, 1e-3)
        progress = jp.clip(actual_drop / target_drop, 0.0, 1.0)
        return_reward = jp.exp(-80.0 * jp.square(data.qpos[2] - self.stand_height))
        support_margin = self._support_margin(data)
        support_gate = jp.where(support_margin >= 0.0, 1.0, 0.0)

        pose_reward = jp.exp(-10.0 * lower_error)
        height_reward = jp.exp(-120.0 * height_error)
        action_reward = jp.exp(-6.0 * action_error)
        rewards.update({
            "command_pose_tracking": pose_reward,
            "command_height_tracking": height_reward,
            "command_action_target": action_reward,
            "command_return": cmd[1] * return_reward,
            "command_progress": jp.where(cmd[0] > 0.05, progress, 0.25 + 0.75 * return_reward),
            "command_support_gate": support_gate,
        })
        metrics["command_target_fraction"] = cmd[0]
        metrics["command_return_phase"] = cmd[1]
        metrics["command_visible_gain"] = cmd[2]
        metrics["command_target_height"] = target_height
        metrics["command_pose_tracking"] = pose_reward
        metrics["command_height_tracking"] = height_reward
        metrics["command_action_target"] = action_reward
        metrics["command_progress"] = progress
        metrics["command_support_gate"] = support_gate
        metrics["command_support_margin"] = support_margin
        return rewards
