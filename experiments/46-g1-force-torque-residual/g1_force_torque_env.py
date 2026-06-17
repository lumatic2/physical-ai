"""Force/torque-aware G1 squat residual environment."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

import jax
import jax.numpy as jp
from ml_collections import config_dict


ROOT = Path(__file__).resolve().parents[2]
EXP28_PATH = ROOT / "experiments/28-g1-controlled-squat-stage0p74/run_controlled_squat.py"


def load_exp28():
    spec = importlib.util.spec_from_file_location("exp28_controlled_squat", EXP28_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {EXP28_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EXP28 = load_exp28()


def force_torque_scales() -> config_dict.ConfigDict:
    scales = EXP28.contact_aware_config().reward_config.scales
    scales.contact_force_balance = 5.0
    scales.lower_torque_limit = 2.5
    scales.torque_rate_limit = 1.0
    scales.depth_force_gate = 4.0
    return scales


class ForceTorqueAwareSquat(EXP28.ContactAwareSquat):
    """Contact-aware squat env with foot-force balance and torque proxy rewards."""

    force_balance_eps = 1e-3
    lower_torque_scale = 55.0
    torque_rate_scale = 40.0

    def __init__(
        self,
        *args,
        config_overrides: dict[str, Any] | None = None,
        **kwargs,
    ):
        super().__init__(*args, config_overrides=config_overrides, **kwargs)
        self._config.reward_config.scales = force_torque_scales()

    def reset(self, rng: jax.Array):
        state = super().reset(rng)
        state.metrics["contact_force_balance"] = jp.zeros(())
        state.metrics["contact_force_imbalance"] = jp.zeros(())
        state.metrics["contact_force_total"] = jp.zeros(())
        state.metrics["lower_torque_rms"] = jp.zeros(())
        state.metrics["lower_torque_limit"] = jp.zeros(())
        state.metrics["torque_rate_rms"] = jp.zeros(())
        state.metrics["torque_rate_limit"] = jp.zeros(())
        state.metrics["depth_force_gate"] = jp.zeros(())
        state.info["last_lower_torque"] = jp.zeros(15)
        return state

    def _foot_force_balance(self, data) -> tuple[jax.Array, jax.Array, jax.Array]:
        left = jp.abs(data.sensordata[self._mj_model.sensor_adr[self._feet_floor_found_sensor[0]]])
        right = jp.abs(data.sensordata[self._mj_model.sensor_adr[self._feet_floor_found_sensor[1]]])
        total = left + right
        imbalance = jp.abs(left - right) / (total + self.force_balance_eps)
        return jp.exp(-3.0 * jp.square(imbalance)), imbalance, total

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
        ref_joints, ref_height = self._reference(info["step"])
        del ref_joints
        balance_reward, imbalance, total_force = self._foot_force_balance(data)
        lower_torque = data.actuator_force[:15]
        torque_rms = jp.sqrt(jp.mean(jp.square(lower_torque)))
        torque_rate = jp.sqrt(jp.mean(jp.square(lower_torque - info["last_lower_torque"])))
        torque_reward = jp.exp(-jp.square(torque_rms / self.lower_torque_scale))
        torque_rate_reward = jp.exp(-jp.square(torque_rate / self.torque_rate_scale))
        at_depth = data.qpos[2] <= ref_height + 0.015
        depth_force_gate = jp.where(at_depth, balance_reward * torque_reward, 0.25 + 0.75 * balance_reward)

        metrics["contact_force_balance"] = balance_reward
        metrics["contact_force_imbalance"] = imbalance
        metrics["contact_force_total"] = total_force
        metrics["lower_torque_rms"] = torque_rms
        metrics["lower_torque_limit"] = torque_reward
        metrics["torque_rate_rms"] = torque_rate
        metrics["torque_rate_limit"] = torque_rate_reward
        metrics["depth_force_gate"] = depth_force_gate
        info["last_lower_torque"] = lower_torque
        rewards["contact_force_balance"] = balance_reward
        rewards["lower_torque_limit"] = torque_reward
        rewards["torque_rate_limit"] = torque_rate_reward
        rewards["depth_force_gate"] = depth_force_gate
        return rewards
