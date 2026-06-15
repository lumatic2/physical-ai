"""G1 squat custom reward wrapper for short smoke tests.

The class lives in the repo instead of patching mujoco_playground's installed
package. It reuses the G1 Joystick observation/model plumbing and swaps the
reset, command, and reward contract for the first authored skill target.
"""

from __future__ import annotations

from typing import Any

import jax
import jax.numpy as jp
from ml_collections import config_dict
from mujoco import mjx

from mujoco_playground._src import mjx_env
from mujoco_playground._src.locomotion.g1 import joystick


def default_config() -> config_dict.ConfigDict:
    cfg = joystick.default_config()
    cfg.episode_length = 300
    cfg.noise_config.level = 0.0
    cfg.push_config.enable = False
    cfg.command_config.a = [0.0, 0.0, 0.0]
    cfg.command_config.b = [0.0, 0.0, 0.0]
    cfg.reward_config.scales = config_dict.create(
        alive=0.5,
        pose_tracking=2.0,
        height_tracking=1.5,
        upright=1.0,
        feet_contact=0.2,
        action_smooth=0.1,
        energy=-0.05,
        termination=-100.0,
    )
    return cfg


class G1Squat(joystick.Joystick):
    """Balance-stabilized squat target using the existing G1 MJX model."""

    def __init__(self, config_overrides: dict[str, Any] | None = None):
        super().__init__(
            task="flat_terrain",
            config=default_config(),
            config_overrides=config_overrides,
        )
        self._squat_pose = self._default_pose.at[0].set(-0.40)
        self._squat_pose = self._squat_pose.at[3].set(0.82)
        self._squat_pose = self._squat_pose.at[4].set(-0.42)
        self._squat_pose = self._squat_pose.at[6].set(-0.40)
        self._squat_pose = self._squat_pose.at[9].set(0.82)
        self._squat_pose = self._squat_pose.at[10].set(-0.42)
        self._squat_pose = self._squat_pose.at[14].set(0.10)

    def sample_command(self, rng: jax.Array) -> jax.Array:
        del rng
        return jp.zeros(3)

    def reset(self, rng: jax.Array) -> mjx_env.State:
        qpos = self._init_q
        qvel = jp.zeros(self.mjx_model.nv)
        data = mjx_env.make_data(
            self.mj_model,
            qpos=qpos,
            qvel=qvel,
            ctrl=qpos[7:],
            impl=self.mjx_model.impl.value,
            naconmax=self._config.naconmax,
            njmax=self._config.njmax,
        )
        data = mjx.forward(self.mjx_model, data)

        phase = jp.array([0, jp.pi])
        gait_freq = jp.array([1.375])
        phase_dt = 2 * jp.pi * self.dt * gait_freq
        info = {
            "rng": rng,
            "step": 0,
            "command": jp.zeros(3),
            "last_act": jp.zeros(self.mjx_model.nu),
            "last_last_act": jp.zeros(self.mjx_model.nu),
            "motor_targets": qpos[7:],
            "feet_air_time": jp.zeros(2),
            "last_contact": jp.zeros(2, dtype=bool),
            "swing_peak": jp.zeros(2),
            "phase_dt": phase_dt,
            "phase": phase,
            "push": jp.array([0.0, 0.0]),
            "push_step": 0,
            "push_interval_steps": jp.array(10_000, dtype=jp.int32),
        }
        metrics = {}
        for key in self._config.reward_config.scales.keys():
            metrics[f"reward/{key}"] = jp.zeros(())
        metrics["swing_peak"] = jp.zeros(())
        metrics["target_height"] = jp.zeros(())
        metrics["pose_error"] = jp.zeros(())

        contact = jp.array([
            data.sensordata[self._mj_model.sensor_adr[sensorid]] > 0
            for sensorid in self._feet_floor_found_sensor
        ])
        obs = self._get_obs(data, info, contact)
        reward, done = jp.zeros(2)
        return mjx_env.State(data, obs, reward, done, metrics, info)

    def _squat_alpha(self, step: jax.Array) -> jax.Array:
        step_f = jp.asarray(step, dtype=jp.float32)
        descend = jp.clip(step_f / 75.0, 0.0, 1.0)
        ascend = jp.clip((step_f - 125.0) / 125.0, 0.0, 1.0)
        return descend * (1.0 - ascend)

    def _target_pose_and_height(self, step: jax.Array) -> tuple[jax.Array, jax.Array]:
        alpha = self._squat_alpha(step)
        pose = self._default_pose * (1.0 - alpha) + self._squat_pose * alpha
        height = 0.755 * (1.0 - alpha) + 0.62 * alpha
        return pose, height

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
        del first_contact
        target_pose, target_height = self._target_pose_and_height(info["step"])
        pose_error = jp.mean(jp.square(data.qpos[7:] - target_pose))
        height_error = jp.square(data.qpos[2] - target_height)
        gravity = self.get_gravity(data, "torso")
        upright_error = jp.sum(jp.square(gravity[:2]))
        metrics["target_height"] = target_height
        metrics["pose_error"] = pose_error
        return {
            "alive": jp.ones(()),
            "pose_tracking": jp.exp(-8.0 * pose_error),
            "height_tracking": jp.exp(-20.0 * height_error),
            "upright": jp.exp(-5.0 * upright_error),
            "feet_contact": jp.mean(contact.astype(jp.float32)),
            "action_smooth": jp.exp(-jp.mean(jp.square(action - info["last_act"]))),
            "energy": 1e-5 * jp.sum(jp.square(data.actuator_force)),
            "termination": done,
        }
