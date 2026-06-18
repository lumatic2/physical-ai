"""Stance-constrained residual finetuning rewards for the G1 visible squat."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import jax
import jax.numpy as jp
from ml_collections import config_dict


ROOT = Path(__file__).resolve().parents[2]
EXP80 = ROOT / "experiments/80-g1-corridor-curriculum-training"
if str(EXP80) not in sys.path:
    sys.path.insert(0, str(EXP80))

from g1_corridor_curriculum_env import CorridorCurriculumSquat, corridor_scales  # noqa: E402


def stance_residual_scales() -> config_dict.ConfigDict:
    scales = corridor_scales()
    scales.corridor_visible_drop = 6.0
    scales.corridor_knee_flexion = 8.0
    scales.corridor_hip_pitch = 3.0
    scales.corridor_support_margin = 22.0
    scales.corridor_terminal_stand = 16.0
    scales.stance_contact_gate = 22.0
    scales.stance_slip_health = 26.0
    scales.stance_support_health = 22.0
    scales.stance_return_height_gate = 16.0
    scales.stance_action_smoothness = 6.0
    scales.stance_residual_budget = 10.0
    return scales


class StanceConstrainedResidualSquat(CorridorCurriculumSquat):
    """Finetunes visible squat geometry with stance/contact as hard residual budget."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._config.reward_config.scales = stance_residual_scales()

    def reset(self, rng: jax.Array):
        state = super().reset(rng)
        for key in [
            "stance_contact_gate",
            "stance_slip_health",
            "stance_support_health",
            "stance_return_height_gate",
            "stance_action_smoothness",
            "stance_residual_budget",
        ]:
            state.metrics[key] = jp.zeros(())
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
        _, _, cmd = self._command_target_pose(info["step"])
        support_margin = self._support_margin(data)
        foot_slip = self._foot_slip(data, info)
        both_feet = jp.min(contact.astype(jp.float32))
        support_health = jp.clip((support_margin - self._support_floor) / 0.04, 0.0, 1.0)
        slip_health = jp.clip(1.0 - foot_slip / jp.asarray(self._slip_limit, dtype=jp.float32), 0.0, 1.0)
        return_phase = cmd[1]
        height_gate = jp.exp(-120.0 * jp.square(data.qpos[2] - self.stand_height))
        smooth = jp.exp(-4.0 * jp.mean(jp.square(action - info["last_act"])))
        contact_gate = both_feet * support_health
        residual_budget = jp.exp(-3.0 * jp.mean(jp.square(action - info["last_act"]))) * slip_health * support_health

        rewards.update({
            "stance_contact_gate": contact_gate,
            "stance_slip_health": slip_health,
            "stance_support_health": support_health,
            "stance_return_height_gate": return_phase * height_gate,
            "stance_action_smoothness": smooth,
            "stance_residual_budget": residual_budget,
        })
        metrics["stance_contact_gate"] = contact_gate
        metrics["stance_slip_health"] = slip_health
        metrics["stance_support_health"] = support_health
        metrics["stance_return_height_gate"] = return_phase * height_gate
        metrics["stance_action_smoothness"] = smooth
        metrics["stance_residual_budget"] = residual_budget
        return rewards
