"""Future-reference command target for G1 visible squat PPO."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import jax
import jax.numpy as jp


ROOT = Path(__file__).resolve().parents[2]
EXP103 = ROOT / "experiments/103-g1-explicit-reference-command-tracker"
if str(EXP103) not in sys.path:
    sys.path.insert(0, str(EXP103))

from g1_explicit_reference_command_env import ExplicitReferenceCommandSquat  # noqa: E402


class FutureReferenceCommandSquat(ExplicitReferenceCommandSquat):
    """Expose a short-horizon reference command while keeping obs shape compatible."""

    def __init__(
        self,
        *args,
        lookahead_s: float = 0.45,
        anticipatory_action_mix: float = 0.45,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self._lookahead_steps = max(1, round(float(lookahead_s) / float(self.dt)))
        self._anticipatory_action_mix = float(anticipatory_action_mix)

    def _future_fraction(self, step: jax.Array) -> jax.Array:
        future_step = step + jp.asarray(self._lookahead_steps, dtype=jp.int32)
        return self._target_fraction(future_step)

    def _return_phase(self, step: jax.Array) -> jax.Array:
        t = jp.asarray(step, dtype=jp.float32) * self.dt
        return_start = jp.asarray(self._descend_s + self._hold_s, dtype=jp.float32)
        return jp.clip((t - return_start) / jp.asarray(self._return_s, dtype=jp.float32), 0.0, 1.0)

    def _squat_command(self, step: jax.Array) -> jax.Array:
        current = self._target_fraction(step)
        future = self._future_fraction(step)
        return_phase = self._return_phase(step)
        return jp.array([current, future, return_phase], dtype=jp.float32)

    def _command_target_pose(self, step: jax.Array):
        cmd = self._squat_command(step)
        target_drop = cmd[0] * jp.asarray(self._reference_drop, dtype=jp.float32)
        target_height = jp.asarray(self.stand_height, dtype=jp.float32) - target_drop
        target_pose = jp.asarray(self._default_pose, dtype=jp.float32) + cmd[0] * self._explicit_visible_delta
        return target_pose, target_height, cmd

    def reset(self, rng: jax.Array):
        state = super().reset(rng)
        state.metrics["future_reference_fraction"] = jp.zeros(())
        state.metrics["future_anticipatory_action"] = jp.zeros(())
        return state

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
        cmd = self._squat_command(info["step"])
        future_pose = jp.asarray(self._default_pose, dtype=jp.float32) + cmd[1] * self._explicit_visible_delta
        current_pose, _, _ = self._command_target_pose(info["step"])
        blended_pose = (
            (1.0 - self._anticipatory_action_mix) * current_pose
            + self._anticipatory_action_mix * future_pose
        )
        desired_action = jp.clip((blended_pose - self._default_pose) / self._config.action_scale, -1.0, 1.0)
        anticipatory = jp.exp(-4.0 * jp.mean(jp.square(action - desired_action)))
        rewards["command_action_target"] = jp.maximum(rewards["command_action_target"], anticipatory)
        metrics["future_reference_fraction"] = cmd[1]
        metrics["future_anticipatory_action"] = anticipatory
        return rewards
