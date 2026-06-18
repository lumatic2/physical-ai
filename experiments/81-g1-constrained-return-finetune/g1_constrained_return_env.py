"""Return-constrained finetuning rewards for the G1 visible squat."""

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


def constrained_return_scales() -> config_dict.ConfigDict:
    scales = corridor_scales()
    scales.corridor_visible_drop = 4.0
    scales.corridor_knee_flexion = 3.0
    scales.corridor_hip_pitch = 2.0
    scales.corridor_support_margin = 16.0
    scales.corridor_terminal_stand = 12.0
    scales.return_contact_gate = 14.0
    scales.return_slip_health = 16.0
    scales.return_support_health = 12.0
    scales.return_height_gate = 10.0
    scales.return_action_smoothness = 4.0
    return scales


class ConstrainedReturnSquat(CorridorCurriculumSquat):
    """Finetunes visible squat geometry toward contact-preserving return."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._config.reward_config.scales = constrained_return_scales()

    def reset(self, rng: jax.Array):
        state = super().reset(rng)
        for key in [
            "return_contact_gate",
            "return_slip_health",
            "return_support_health",
            "return_height_gate",
            "return_action_smoothness",
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

        rewards.update({
            "return_contact_gate": contact_gate,
            "return_slip_health": slip_health,
            "return_support_health": support_health,
            "return_height_gate": return_phase * height_gate,
            "return_action_smoothness": smooth,
        })
        metrics["return_contact_gate"] = contact_gate
        metrics["return_slip_health"] = slip_health
        metrics["return_support_health"] = support_health
        metrics["return_height_gate"] = return_phase * height_gate
        metrics["return_action_smoothness"] = smooth
        return rewards
