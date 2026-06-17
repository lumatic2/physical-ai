"""Stance-constrained command-conditioned G1 squat environment."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import jax
import jax.numpy as jp
from ml_collections import config_dict
from mujoco_playground._src import mjx_env


ROOT = Path(__file__).resolve().parents[2]
EXP49 = ROOT / "experiments/49-g1-command-conditioned-squat-policy"
if str(EXP49) not in sys.path:
    sys.path.insert(0, str(EXP49))

from g1_command_squat_env import CommandConditionedSquat  # noqa: E402


def stance_scales() -> config_dict.ConfigDict:
    scales = CommandConditionedSquat(target_drop=0.03, config_overrides={"impl": "jax"})._config.reward_config.scales
    scales.stance_lock_action_prior = 10.0
    scales.foot_slip_gate = 8.0
    scales.support_termination_margin = 0.0
    return scales


class StanceConstrainedCommandSquat(CommandConditionedSquat):
    """Adds support/slip termination and stance-lock action prior."""

    def __init__(
        self,
        *args,
        support_floor: float = -0.005,
        slip_limit: float = 0.08,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self._support_floor = float(support_floor)
        self._slip_limit = float(slip_limit)
        self._config.reward_config.scales = stance_scales()

    def reset(self, rng: jax.Array):
        state = super().reset(rng)
        state.info["initial_foot_xy"] = state.data.site_xpos[self._feet_site_id, :2]
        state.metrics["stance_foot_slip"] = jp.zeros(())
        state.metrics["stance_support_margin"] = jp.zeros(())
        state.metrics["stance_terminated"] = jp.zeros(())
        state.metrics["stance_lock_action_prior"] = jp.zeros(())
        state.metrics["foot_slip_gate"] = jp.zeros(())
        return state

    def _foot_slip(self, data, info: dict[str, Any]) -> jax.Array:
        foot_xy = data.site_xpos[self._feet_site_id, :2]
        return jp.max(jp.linalg.norm(foot_xy - info["initial_foot_xy"], axis=1))

    def _stance_done(self, data, info: dict[str, Any]) -> tuple[jax.Array, jax.Array, jax.Array]:
        support_margin = self._support_margin(data)
        foot_slip = self._foot_slip(data, info)
        done = (support_margin < self._support_floor) | (foot_slip > self._slip_limit)
        return done, support_margin, foot_slip

    def step(self, state, action: jax.Array):
        state.info["command"] = self._squat_command(state.info["step"])

        state.info["rng"], push1_rng, push2_rng = jax.random.split(state.info["rng"], 3)
        push_theta = jax.random.uniform(push1_rng, maxval=2 * jp.pi)
        push_magnitude = jax.random.uniform(
            push2_rng,
            minval=self._config.push_config.magnitude_range[0],
            maxval=self._config.push_config.magnitude_range[1],
        )
        push = jp.array([jp.cos(push_theta), jp.sin(push_theta)])
        push *= jp.mod(state.info["push_step"] + 1, state.info["push_interval_steps"]) == 0
        push *= self._config.push_config.enable
        qvel = state.data.qvel
        qvel = qvel.at[:2].set(push * push_magnitude + qvel[:2])
        data = state.data.replace(qvel=qvel)
        state = state.replace(data=data)

        motor_targets = self._motor_targets(action, state.info["step"])
        data = mjx_env.step(self.mjx_model, state.data, motor_targets, self.n_substeps)
        state.info["motor_targets"] = motor_targets

        contact = jp.array([
            data.sensordata[self._mj_model.sensor_adr[sensorid]] > 0
            for sensorid in self._feet_floor_found_sensor
        ])
        contact_filt = contact | state.info["last_contact"]
        first_contact = (state.info["feet_air_time"] > 0.0) * contact_filt
        state.info["feet_air_time"] += self.dt
        p_f = data.site_xpos[self._feet_site_id]
        p_fz = p_f[..., -1]
        state.info["swing_peak"] = jp.maximum(state.info["swing_peak"], p_fz)

        base_done = self._get_termination(data)
        stance_done, support_margin, foot_slip = self._stance_done(data, state.info)
        done = base_done | stance_done
        obs = self._get_obs(data, state.info, contact)
        rewards = self._get_reward(data, action, state.info, state.metrics, done, first_contact, contact)
        rewards = {k: v * self._config.reward_config.scales[k] for k, v in rewards.items()}
        reward = sum(rewards.values()) * self.dt

        state.info["push"] = push
        state.info["step"] += 1
        state.info["push_step"] += 1
        phase_tp1 = state.info["phase"] + state.info["phase_dt"]
        phase_next = jp.fmod(phase_tp1 + jp.pi, 2 * jp.pi) - jp.pi
        state.info["phase"] = jp.where(self._freeze_phase, jp.ones(2) * jp.pi, phase_next)
        state.info["last_last_act"] = state.info["last_act"]
        state.info["last_act"] = action
        state.info["rng"], cmd_rng = jax.random.split(state.info["rng"])
        state.info["command"] = jp.where(state.info["step"] > 500, self.sample_command(cmd_rng), state.info["command"])
        state.info["step"] = jp.where(done | (state.info["step"] > 500), 0, state.info["step"])
        state.info["initial_foot_xy"] = jp.where(done, data.site_xpos[self._feet_site_id, :2], state.info["initial_foot_xy"])
        state.info["feet_air_time"] *= ~contact
        state.info["last_contact"] = contact
        state.info["swing_peak"] *= ~contact

        for key, value in rewards.items():
            state.metrics[f"reward/{key}"] = value
        state.metrics["swing_peak"] = jp.mean(state.info["swing_peak"])
        state.metrics["controller_blend"] = jp.asarray(self._controller_blend, dtype=jp.float32)
        state.metrics["freeze_phase"] = jp.asarray(float(self._freeze_phase), dtype=jp.float32)
        state.metrics["effective_controller_blend"] = self._effective_controller_blend(state.info["step"])
        state.metrics["reference_scale"] = jp.asarray(0.0 if self._reference_scale is None else self._reference_scale, dtype=jp.float32)
        state.metrics["stance_foot_slip"] = foot_slip
        state.metrics["stance_support_margin"] = support_margin
        state.metrics["stance_terminated"] = stance_done.astype(jp.float32)

        done = done.astype(reward.dtype)
        return state.replace(data=data, obs=obs, reward=reward, done=done)

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
        target_pose, _, cmd = self._command_target_pose(info["step"])
        desired_action = jp.clip((target_pose - self._default_pose) / self._config.action_scale, -1.0, 1.0)
        support_margin = self._support_margin(data)
        foot_slip = self._foot_slip(data, info)
        support_health = jp.clip((support_margin - self._support_floor) / 0.04, 0.0, 1.0)
        slip_health = jp.clip(1.0 - foot_slip / self._slip_limit, 0.0, 1.0)
        health = support_health * slip_health
        stance_desired = health * cmd[0] * desired_action
        stance_prior = jp.exp(-6.0 * jp.mean(jp.square(action - stance_desired)))
        slip_gate = jp.where(foot_slip <= self._slip_limit, 1.0, 0.0)
        rewards["stance_lock_action_prior"] = stance_prior
        rewards["foot_slip_gate"] = slip_gate
        rewards["support_termination_margin"] = jp.where(support_margin >= self._support_floor, 1.0, 0.0)
        metrics["stance_lock_action_prior"] = stance_prior
        metrics["foot_slip_gate"] = slip_gate
        metrics["stance_foot_slip"] = foot_slip
        metrics["stance_support_margin"] = support_margin
        return rewards
