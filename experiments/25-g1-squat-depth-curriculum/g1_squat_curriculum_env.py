"""Stage-conditioned G1 squat depth curriculum env."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jax
import jax.numpy as jp
from ml_collections import config_dict
from mujoco import mjx

from mujoco_playground._src import mjx_env
from mujoco_playground._src.locomotion.g1 import joystick


ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "experiments/17-motion-to-policy-loop/verify/g1_squat_reference.compiled.json"


def default_config() -> config_dict.ConfigDict:
    cfg = joystick.default_config()
    cfg.episode_length = 300
    cfg.noise_config.level = 0.0
    cfg.push_config.enable = False
    cfg.command_config.a = [0.0, 0.0, 0.0]
    cfg.command_config.b = [0.0, 0.0, 0.0]
    cfg.reward_config.scales = config_dict.create(
        alive=0.4,
        staged_reference_tracking=2.5,
        arm_still=0.25,
        staged_height_tracking=8.0,
        controlled_depth=5.0,
        return_to_stand=1.5,
        torso_upright=2.5,
        pelvis_upright=0.8,
        foot_contact=0.8,
        base_stability=0.2,
        action_smooth=0.2,
        residual_magnitude=-0.025,
        residual_delta=-0.02,
        energy=-0.015,
        termination=-220.0,
    )
    return cfg


def load_reference() -> tuple[jax.Array, jax.Array]:
    compiled = json.loads(REFERENCE.read_text(encoding="utf-8"))
    samples = compiled["trajectory"]["samples"]
    joint_targets = jp.asarray([sample["joint_targets"] for sample in samples], dtype=jp.float32)
    heights = jp.asarray([sample["base_height"] for sample in samples], dtype=jp.float32)
    return joint_targets, heights


class G1SquatCurriculum(joystick.Joystick):
    """Squat reference tracking with a per-stage minimum target height."""

    min_base_height = 0.45
    min_torso_up = 0.20
    stand_height = 0.755

    def __init__(
        self,
        stage_height: float = 0.74,
        config_overrides: dict[str, Any] | None = None,
    ):
        super().__init__(
            task="flat_terrain",
            config=default_config(),
            config_overrides=config_overrides,
        )
        ref_joints, ref_heights = load_reference()
        self._raw_ref_joints = ref_joints
        self._raw_ref_heights = ref_heights
        self._stage_height = float(stage_height)
        self._ref_heights = jp.maximum(ref_heights, self._stage_height)
        default_lower = jp.asarray(self._default_pose[:15], dtype=jp.float32)
        raw_drop = jp.maximum(self.stand_height - ref_heights, 1e-4)
        staged_drop = jp.clip(self.stand_height - self._ref_heights, 0.0, None)
        blend = jp.clip(staged_drop / raw_drop, 0.0, 1.0)[:, None]
        self._ref_joints = default_lower + blend * (ref_joints - default_lower)
        self._ref_len = int(self._ref_heights.shape[0])

    @property
    def stage_height(self) -> float:
        return self._stage_height

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
        metrics["stage_height"] = jp.asarray(self._stage_height, dtype=jp.float32)
        metrics["target_height"] = jp.zeros(())
        metrics["reference_error"] = jp.zeros(())
        metrics["height_error"] = jp.zeros(())
        metrics["torso_up"] = jp.zeros(())
        metrics["depth_progress"] = jp.zeros(())

        contact = jp.array([
            data.sensordata[self._mj_model.sensor_adr[sensorid]] > 0
            for sensorid in self._feet_floor_found_sensor
        ])
        obs = self._get_obs(data, info, contact)
        reward, done = jp.zeros(2)
        return mjx_env.State(data, obs, reward, done, metrics, info)

    def _reference(self, step: jax.Array) -> tuple[jax.Array, jax.Array]:
        index = jp.minimum(jp.asarray(step, dtype=jp.int32), self._ref_len - 1)
        return self._ref_joints[index], self._ref_heights[index]

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
        ref_joints, ref_height = self._reference(info["step"])
        joint_error = jp.mean(jp.square(data.qpos[7:22] - ref_joints))
        arm_error = jp.mean(jp.square(data.qpos[22:] - self._default_pose[15:]))
        height_error = jp.square(data.qpos[2] - ref_height)
        target_drop = jp.maximum(self.stand_height - ref_height, 1e-3)
        actual_drop = jp.clip(self.stand_height - data.qpos[2], 0.0, target_drop)
        depth_progress = actual_drop / target_drop
        hold_band = jp.asarray(0.015, dtype=jp.float32)
        at_depth = data.qpos[2] <= ref_height + hold_band
        final_phase = info["step"] > jp.asarray(self._ref_len - 40, dtype=jp.int32)
        return_reward = jp.where(final_phase, jp.exp(-80.0 * jp.square(data.qpos[2] - self.stand_height)), 0.0)

        torso_gravity = self.get_gravity(data, "torso")
        pelvis_gravity = self.get_gravity(data, "pelvis")
        torso_upright_error = jp.sum(jp.square(torso_gravity[:2]))
        pelvis_upright_error = jp.sum(jp.square(pelvis_gravity[:2]))
        linvel_xy = self.get_global_linvel(data, "pelvis")[:2]
        angvel_xy = self.get_global_angvel(data, "torso")[:2]
        stability_cost = jp.sum(jp.square(linvel_xy)) + 0.25 * jp.sum(jp.square(angvel_xy))
        both_feet = jp.all(contact)
        action_delta = jp.mean(jp.square(action - info["last_act"]))

        metrics["target_height"] = ref_height
        metrics["reference_error"] = joint_error
        metrics["height_error"] = height_error
        metrics["torso_up"] = torso_gravity[-1]
        metrics["depth_progress"] = depth_progress
        return {
            "alive": jp.ones(()),
            "staged_reference_tracking": jp.exp(-8.0 * joint_error),
            "arm_still": jp.exp(-4.0 * arm_error),
            "staged_height_tracking": jp.exp(-120.0 * height_error),
            "controlled_depth": jp.where(at_depth, 1.0, depth_progress),
            "return_to_stand": return_reward,
            "torso_upright": jp.exp(-6.0 * torso_upright_error),
            "pelvis_upright": jp.exp(-4.0 * pelvis_upright_error),
            "foot_contact": both_feet.astype(jp.float32),
            "base_stability": jp.exp(-0.4 * stability_cost),
            "action_smooth": jp.exp(-action_delta),
            "residual_magnitude": jp.mean(jp.square(action)),
            "residual_delta": action_delta,
            "energy": 1e-5 * jp.sum(jp.square(data.actuator_force)),
            "termination": done,
        }
