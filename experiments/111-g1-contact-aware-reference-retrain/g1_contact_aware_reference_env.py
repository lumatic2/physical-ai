"""Contact-aware future-reference tracker for G1 visible squat PPO."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import jax
import jax.numpy as jp


ROOT = Path(__file__).resolve().parents[2]
EXP105 = ROOT / "experiments/105-g1-future-reference-observation-tracker"
if str(EXP105) not in sys.path:
    sys.path.insert(0, str(EXP105))

from g1_future_reference_env import FutureReferenceCommandSquat  # noqa: E402


def contact_reference_scales(base):
    scales = base
    scales.corridor_visible_drop = 10.0
    scales.corridor_knee_flexion = 12.0
    scales.corridor_hip_pitch = 7.0
    scales.corridor_support_margin = 10.0
    scales.corridor_terminal_stand = 6.0
    scales.command_pose_tracking = 8.0
    scales.command_height_tracking = 8.0
    scales.command_action_target = 2.0
    scales.stance_lock_action_prior = 14.0
    scales.foot_slip_gate = 18.0
    scales.support_termination_margin = 12.0
    scales.two_foot_contact_gate = 14.0
    scales.contact_aware_action_smoothness = 5.0
    scales.slip_scaled_reference = 7.0
    return scales


class ContactAwareReferenceSquat(FutureReferenceCommandSquat):
    """A policy-compatible future-reference tracker with harder stance/contact rewards."""

    def __init__(
        self,
        *args,
        contact_action_scale: float = 0.55,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self._contact_action_scale = float(contact_action_scale)
        self._config.reward_config.scales = contact_reference_scales(self._config.reward_config.scales)

    def reset(self, rng: jax.Array):
        state = super().reset(rng)
        state.metrics["two_foot_contact_gate"] = jp.zeros(())
        state.metrics["contact_aware_action_smoothness"] = jp.zeros(())
        state.metrics["slip_scaled_reference"] = jp.zeros(())
        state.metrics["contact_health"] = jp.zeros(())
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
        support_margin = self._support_margin(data)
        foot_slip = self._foot_slip(data, info)
        support_health = jp.clip((support_margin - self._support_floor) / 0.045, 0.0, 1.0)
        slip_health = jp.clip(1.0 - foot_slip / self._slip_limit, 0.0, 1.0)
        two_foot_contact = jp.all(contact).astype(jp.float32)
        contact_health = support_health * slip_health * two_foot_contact

        target_pose, _, cmd = self._command_target_pose(info["step"])
        raw_desired = jp.clip((target_pose - self._default_pose) / self._config.action_scale, -1.0, 1.0)
        scaled_desired = self._contact_action_scale * contact_health * cmd[0] * raw_desired
        smooth = jp.exp(-5.0 * jp.mean(jp.square(action - info["last_act"])))
        slip_scaled_reference = jp.exp(-4.0 * jp.mean(jp.square(action - scaled_desired)))

        rewards["two_foot_contact_gate"] = two_foot_contact
        rewards["contact_aware_action_smoothness"] = smooth
        rewards["slip_scaled_reference"] = slip_scaled_reference
        metrics["two_foot_contact_gate"] = two_foot_contact
        metrics["contact_aware_action_smoothness"] = smooth
        metrics["slip_scaled_reference"] = slip_scaled_reference
        metrics["contact_health"] = contact_health
        return rewards
