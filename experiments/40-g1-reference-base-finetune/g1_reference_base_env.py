"""Reference-base action target G1 squat environment."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import jax
import jax.numpy as jp
from mujoco_playground._src import mjx_env


ROOT = Path(__file__).resolve().parents[2]
EXP38 = ROOT / "experiments/38-g1-support-aware-depth-finetune"
if str(EXP38) not in sys.path:
    sys.path.insert(0, str(EXP38))

from g1_support_depth_env import G1SupportAwareDepth  # noqa: E402


class G1ReferenceBaseDepth(G1SupportAwareDepth):
    """Support-aware squat env with motor targets around a moving reference pose."""

    def __init__(
        self,
        stage_height: float = 0.74,
        reference_gain: float = 0.35,
        ramp_s: float = 3.0,
        residual_scale: float = 1.0,
        config_overrides: dict[str, Any] | None = None,
    ):
        super().__init__(stage_height=stage_height, config_overrides=config_overrides)
        self._reference_gain = float(reference_gain)
        self._ramp_s = float(ramp_s)
        self._residual_scale = float(residual_scale)

    def reset(self, rng: jax.Array):
        state = super().reset(rng)
        state.metrics["reference_gain"] = jp.asarray(self._reference_gain, dtype=jp.float32)
        state.metrics["reference_blend"] = jp.zeros(())
        state.metrics["residual_scale"] = jp.asarray(self._residual_scale, dtype=jp.float32)
        return state

    def _reference_blend(self, step: jax.Array) -> jax.Array:
        t = jp.asarray(step, dtype=jp.float32) * self.dt
        return jp.asarray(self._reference_gain, dtype=jp.float32) * jp.clip(
            t / jp.maximum(jp.asarray(self._ramp_s, dtype=jp.float32), self.dt),
            0.0,
            1.0,
        )

    def _motor_targets(self, action: jax.Array, step: jax.Array) -> jax.Array:
        ref_joints, _ = self._reference(step)
        reference_pose = self._default_pose.at[:15].set(ref_joints)
        blend = self._reference_blend(step)
        moving_pose = self._default_pose + blend * (reference_pose - self._default_pose)
        return moving_pose + self._residual_scale * action * self._config.action_scale

    def step(self, state: mjx_env.State, action: jax.Array) -> mjx_env.State:
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

        obs = self._get_obs(data, state.info, contact)
        done = self._get_termination(data)
        rewards = self._get_reward(data, action, state.info, state.metrics, done, first_contact, contact)
        rewards = {k: v * self._config.reward_config.scales[k] for k, v in rewards.items()}
        reward = sum(rewards.values()) * self.dt

        state.info["push"] = push
        state.info["step"] += 1
        state.info["push_step"] += 1
        phase_tp1 = state.info["phase"] + state.info["phase_dt"]
        state.info["phase"] = jp.fmod(phase_tp1 + jp.pi, 2 * jp.pi) - jp.pi
        state.info["last_last_act"] = state.info["last_act"]
        state.info["last_act"] = action
        state.info["rng"], cmd_rng = jax.random.split(state.info["rng"])
        state.info["command"] = jp.where(state.info["step"] > 500, self.sample_command(cmd_rng), state.info["command"])
        state.info["step"] = jp.where(done | (state.info["step"] > 500), 0, state.info["step"])
        state.info["feet_air_time"] *= ~contact
        state.info["last_contact"] = contact
        state.info["swing_peak"] *= ~contact

        for key, value in rewards.items():
            state.metrics[f"reward/{key}"] = value
        state.metrics["swing_peak"] = jp.mean(state.info["swing_peak"])
        state.metrics["reference_blend"] = self._reference_blend(state.info["step"])
        state.metrics["reference_gain"] = jp.asarray(self._reference_gain, dtype=jp.float32)
        state.metrics["residual_scale"] = jp.asarray(self._residual_scale, dtype=jp.float32)

        done = done.astype(reward.dtype)
        return state.replace(data=data, obs=obs, reward=reward, done=done)
