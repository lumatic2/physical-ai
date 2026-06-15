"""G1 squat recovery env with stricter fall-aware rewards.

This keeps the repo-local subclass pattern from exp18, but makes the training
contract closer to native diagnostic: low base height and poor torso upright are
terminal, not just post-hoc evaluation failures.
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
    cfg.episode_length = 450
    cfg.noise_config.level = 0.0
    cfg.push_config.enable = False
    cfg.command_config.a = [0.0, 0.0, 0.0]
    cfg.command_config.b = [0.0, 0.0, 0.0]
    cfg.reward_config.scales = config_dict.create(
        alive=1.0,
        pose_tracking=1.0,
        height_tracking=1.5,
        height_floor=2.0,
        torso_upright=3.0,
        pelvis_upright=1.0,
        base_stability=0.5,
        feet_contact=0.2,
        action_smooth=0.2,
        action_magnitude=-0.02,
        energy=-0.02,
        termination=-200.0,
    )
    return cfg


class G1SquatRecovery(joystick.Joystick):
    """Fall-aware shallow squat target for recovery PPO smoke."""

    min_base_height = 0.50
    min_torso_up = 0.25

    def __init__(self, config_overrides: dict[str, Any] | None = None):
        super().__init__(
            task="flat_terrain",
            config=default_config(),
            config_overrides=config_overrides,
        )
        self._squat_pose = self._default_pose.at[0].set(-0.28)
        self._squat_pose = self._squat_pose.at[3].set(0.55)
        self._squat_pose = self._squat_pose.at[4].set(-0.28)
        self._squat_pose = self._squat_pose.at[6].set(-0.28)
        self._squat_pose = self._squat_pose.at[9].set(0.55)
        self._squat_pose = self._squat_pose.at[10].set(-0.28)
        self._squat_pose = self._squat_pose.at[14].set(0.06)

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
            "phase_dt": 2 * jp.pi * self.dt * gait_freq,
            "phase": phase,
            "push": jp.array([0.0, 0.0]),
            "push_step": 0,
            "push_interval_steps": jp.array(10_000, dtype=jp.int32),
        }
        metrics = {f"reward/{key}": jp.zeros(()) for key in self._config.reward_config.scales.keys()}
        metrics["swing_peak"] = jp.zeros(())
        metrics["target_height"] = jp.zeros(())
        metrics["pose_error"] = jp.zeros(())
        metrics["torso_up"] = jp.zeros(())

        contact = jp.array([
            data.sensordata[self._mj_model.sensor_adr[sensorid]] > 0
            for sensorid in self._feet_floor_found_sensor
        ])
        obs = self._get_obs(data, info, contact)
        reward, done = jp.zeros(2)
        return mjx_env.State(data, obs, reward, done, metrics, info)

    def _squat_alpha(self, step: jax.Array) -> jax.Array:
        step_f = jp.asarray(step, dtype=jp.float32)
        hold_stand = 50.0
        descend = jp.clip((step_f - hold_stand) / 150.0, 0.0, 1.0)
        ascend = jp.clip((step_f - 300.0) / 150.0, 0.0, 1.0)
        return descend * (1.0 - ascend)

    def _target_pose_and_height(self, step: jax.Array) -> tuple[jax.Array, jax.Array]:
        alpha = self._squat_alpha(step)
        pose = self._default_pose * (1.0 - alpha) + self._squat_pose * alpha
        height = 0.755 * (1.0 - alpha) + 0.68 * alpha
        return pose, height

    def _get_termination(self, data: mjx.Data) -> jax.Array:
        base_too_low = data.qpos[2] < self.min_base_height
        torso_up = self.get_gravity(data, "torso")[-1]
        torso_fallen = torso_up < self.min_torso_up
        return super()._get_termination(data) | base_too_low | torso_fallen

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
        torso_gravity = self.get_gravity(data, "torso")
        pelvis_gravity = self.get_gravity(data, "pelvis")
        torso_upright_error = jp.sum(jp.square(torso_gravity[:2]))
        pelvis_upright_error = jp.sum(jp.square(pelvis_gravity[:2]))
        linvel_xy = self.get_global_linvel(data, "pelvis")[:2]
        angvel_xy = self.get_global_angvel(data, "torso")[:2]
        stability_cost = jp.sum(jp.square(linvel_xy)) + 0.25 * jp.sum(jp.square(angvel_xy))
        height_floor = jp.clip((data.qpos[2] - self.min_base_height) / 0.20, 0.0, 1.0)
        metrics["target_height"] = target_height
        metrics["pose_error"] = pose_error
        metrics["torso_up"] = torso_gravity[-1]
        return {
            "alive": jp.ones(()),
            "pose_tracking": jp.exp(-4.0 * pose_error),
            "height_tracking": jp.exp(-30.0 * height_error),
            "height_floor": height_floor,
            "torso_upright": jp.exp(-6.0 * torso_upright_error),
            "pelvis_upright": jp.exp(-4.0 * pelvis_upright_error),
            "base_stability": jp.exp(-0.5 * stability_cost),
            "feet_contact": jp.mean(contact.astype(jp.float32)),
            "action_smooth": jp.exp(-jp.mean(jp.square(action - info["last_act"]))),
            "action_magnitude": jp.mean(jp.square(action)),
            "energy": 1e-5 * jp.sum(jp.square(data.actuator_force)),
            "termination": done,
        }
