"""Support-aware staged G1 squat depth environment."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import jax
import jax.numpy as jp
from ml_collections import config_dict
from mujoco import mjx


ROOT = Path(__file__).resolve().parents[2]
EXP25 = ROOT / "experiments/25-g1-squat-depth-curriculum"
if str(EXP25) not in sys.path:
    sys.path.insert(0, str(EXP25))

from g1_squat_curriculum_env import G1SquatCurriculum  # noqa: E402


def support_scales() -> config_dict.ConfigDict:
    return config_dict.create(
        alive=0.35,
        staged_reference_tracking=2.0,
        arm_still=0.2,
        staged_height_tracking=7.0,
        controlled_depth=4.5,
        return_to_stand=1.5,
        torso_upright=2.5,
        pelvis_upright=1.0,
        foot_contact=1.0,
        support_margin=3.0,
        vertical_damping=2.0,
        base_stability=0.4,
        action_smooth=0.25,
        residual_magnitude=-0.03,
        residual_delta=-0.03,
        energy=-0.015,
        termination=-240.0,
    )


class G1SupportAwareDepth(G1SquatCurriculum):
    """Stage curriculum with approximate CoM support margin rewards."""

    foot_half_x = 0.09
    foot_half_y = 0.03
    support_margin_target = 0.015
    downward_velocity_limit = -0.28

    def __init__(
        self,
        stage_height: float = 0.74,
        config_overrides: dict[str, Any] | None = None,
    ):
        super().__init__(stage_height=stage_height, config_overrides=config_overrides)
        self._config.reward_config.scales = support_scales()

    def reset(self, rng: jax.Array):
        state = super().reset(rng)
        state.metrics["support_margin"] = jp.zeros(())
        state.metrics["vertical_velocity"] = jp.zeros(())
        state.metrics["support_inside"] = jp.zeros(())
        return state

    def _support_margin(self, data: mjx.Data) -> jax.Array:
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
        data: mjx.Data,
        action: jax.Array,
        info: dict[str, Any],
        metrics: dict[str, Any],
        done: jax.Array,
        first_contact: jax.Array,
        contact: jax.Array,
    ) -> dict[str, jax.Array]:
        reward = super()._get_reward(data, action, info, metrics, done, first_contact, contact)
        margin = self._support_margin(data)
        vertical_velocity = self.get_global_linvel(data, "pelvis")[2]
        support_margin_reward = jp.clip((margin + 0.02) / (self.support_margin_target + 0.02), 0.0, 1.0)
        vertical_damping = jp.exp(-12.0 * jp.square(jp.minimum(vertical_velocity - self.downward_velocity_limit, 0.0)))
        metrics["support_margin"] = margin
        metrics["vertical_velocity"] = vertical_velocity
        metrics["support_inside"] = (margin >= 0.0).astype(jp.float32)
        reward.update({
            "support_margin": support_margin_reward,
            "vertical_damping": vertical_damping,
        })
        return reward
