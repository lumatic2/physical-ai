"""Run contact-aware controlled G1 squat attempts for stage 0.74."""

from __future__ import annotations

import argparse
import functools
import importlib.util
import json
import pickle
import re
import sys
import time
from pathlib import Path
from typing import Any

import jax
import jax.numpy as jp
import mujoco
import numpy as np
from brax.training.acme import running_statistics
from brax.training.agents.ppo import networks as ppo_networks
from brax.training.agents.ppo import train as ppo
from ml_collections import config_dict
from mujoco_playground import wrapper
from mujoco_playground._src import mjx_env
from mujoco_playground.config import locomotion_params


EXP_DIR = Path(__file__).resolve().parent
ROOT = EXP_DIR.parents[1]
VERIFY = EXP_DIR / "verify"
STAGE_DIR = VERIFY / "stage-0p74"
EXP25_DIR = ROOT / "experiments/25-g1-squat-depth-curriculum"
EXP22_SOURCE = ROOT / "experiments/22-g1-squat-depth-finetune/verify/train/params.pkl"
EXP21_SOURCE = ROOT / "experiments/21-g1-stabilizer-init-probe/verify/train/params.pkl"

sys.path.insert(0, str(EXP25_DIR))


def load_exp25_module():
    module_path = EXP25_DIR / "g1_squat_curriculum_env.py"
    spec = importlib.util.spec_from_file_location("exp25_g1_squat_curriculum_env", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EXP25 = load_exp25_module()
EXP25_DEFAULT_CONFIG = EXP25.default_config


def contact_aware_config() -> config_dict.ConfigDict:
    cfg = EXP25_DEFAULT_CONFIG()
    cfg.reward_config.scales = config_dict.create(
        alive=0.4,
        staged_reference_tracking=3.0,
        arm_still=0.25,
        staged_height_tracking=12.0,
        controlled_depth=7.0,
        contact_at_depth=7.0,
        pose_prior=5.0,
        height_push=4.0,
        action_target=6.0,
        return_to_stand=3.0,
        torso_upright=3.5,
        pelvis_upright=1.2,
        foot_contact=5.0,
        base_stability=0.8,
        action_smooth=0.3,
        residual_magnitude=-0.035,
        residual_delta=-0.04,
        energy=-0.02,
        termination=-260.0,
    )
    return cfg


EXP25.default_config = contact_aware_config


class ContactAwareSquat(EXP25.G1SquatCurriculum):
    """Stage squat env with an explicit contact-at-depth term."""

    def __init__(
        self,
        *args,
        controller_blend: float = 0.0,
        freeze_phase: bool = False,
        blend_schedule: str = "fixed",
        reference_scale: float | None = None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self._controller_blend = float(controller_blend)
        self._freeze_phase = bool(freeze_phase)
        self._blend_schedule = blend_schedule
        self._reference_scale = reference_scale
        if reference_scale is not None:
            default_lower = jp.asarray(self._default_pose[:15], dtype=jp.float32)
            scale = jp.asarray(reference_scale, dtype=jp.float32)
            self._ref_joints = default_lower + scale * (self._raw_ref_joints - default_lower)

    def reset(self, rng: jax.Array):
        state = super().reset(rng)
        state.metrics["contact_at_depth"] = jp.zeros(())
        state.metrics["pose_prior"] = jp.zeros(())
        state.metrics["height_push"] = jp.zeros(())
        state.metrics["action_target"] = jp.zeros(())
        state.metrics["controller_blend"] = jp.asarray(self._controller_blend, dtype=jp.float32)
        state.metrics["freeze_phase"] = jp.asarray(float(self._freeze_phase), dtype=jp.float32)
        state.metrics["effective_controller_blend"] = jp.zeros(())
        state.metrics["reference_scale"] = jp.asarray(0.0 if self._reference_scale is None else self._reference_scale, dtype=jp.float32)
        if self._freeze_phase:
            state.info["phase"] = jp.ones(2) * jp.pi
        return state

    def _effective_controller_blend(self, step: jax.Array) -> jax.Array:
        blend = jp.asarray(self._controller_blend, dtype=jp.float32)
        if self._blend_schedule != "squat":
            return blend
        t = jp.asarray(step, dtype=jp.float32) * self.dt
        ramp_up_end = jp.asarray(1.2, dtype=jp.float32)
        hold_end = jp.asarray(3.4, dtype=jp.float32)
        ramp_down_end = jp.asarray(4.2, dtype=jp.float32)
        ramp_up = blend * jp.clip(t / ramp_up_end, 0.0, 1.0)
        ramp_down = blend * jp.clip(1.0 - (t - hold_end) / (ramp_down_end - hold_end), 0.0, 1.0)
        return jp.where(t < ramp_up_end, ramp_up, jp.where(t < hold_end, blend, jp.where(t < ramp_down_end, ramp_down, 0.0)))

    def _motor_targets(self, action: jax.Array, step: jax.Array) -> jax.Array:
        policy_targets = self._default_pose + action * self._config.action_scale
        ref_joints, _ = self._reference(step)
        staged_pose = self._default_pose.at[:15].set(ref_joints)
        blend = self._effective_controller_blend(step)
        return (1.0 - blend) * policy_targets + blend * staged_pose

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
        phase_next = jp.fmod(phase_tp1 + jp.pi, 2 * jp.pi) - jp.pi
        state.info["phase"] = jp.where(self._freeze_phase, jp.ones(2) * jp.pi, phase_next)
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
        state.metrics["controller_blend"] = jp.asarray(self._controller_blend, dtype=jp.float32)
        state.metrics["freeze_phase"] = jp.asarray(float(self._freeze_phase), dtype=jp.float32)
        state.metrics["effective_controller_blend"] = self._effective_controller_blend(state.info["step"])
        state.metrics["reference_scale"] = jp.asarray(0.0 if self._reference_scale is None else self._reference_scale, dtype=jp.float32)

        done = done.astype(reward.dtype)
        return state.replace(data=data, obs=obs, reward=reward, done=done)

    def _get_reward(
        self,
        data: Any,
        action: jax.Array,
        info: dict[str, Any],
        metrics: dict[str, Any],
        done: jax.Array,
        first_contact: jax.Array,
        contact: jax.Array,
    ) -> dict[str, jax.Array]:
        rewards = super()._get_reward(data, action, info, metrics, done, first_contact, contact)
        ref_joints, ref_height = self._reference(info["step"])
        both_feet = jp.all(contact)
        at_depth = data.qpos[2] <= ref_height + 0.015
        contact_at_depth = jp.where(at_depth, both_feet.astype(jp.float32), 0.25 * both_feet.astype(jp.float32))
        pose_error = jp.mean(jp.square(data.qpos[7:22] - ref_joints))
        target_pose = data.qpos[7:]
        target_pose = target_pose.at[:15].set(ref_joints)
        desired_action = (target_pose - self._default_pose) / self._config.action_scale
        desired_action = jp.clip(desired_action, -1.0, 1.0)
        action_target = jp.exp(-6.0 * jp.mean(jp.square(action - desired_action)))
        target_drop = jp.maximum(self.stand_height - ref_height, 1e-3)
        actual_drop = jp.clip(self.stand_height - data.qpos[2], 0.0, target_drop)
        height_push = actual_drop / target_drop
        rewards["contact_at_depth"] = contact_at_depth
        rewards["pose_prior"] = jp.exp(-16.0 * pose_error)
        rewards["height_push"] = height_push
        rewards["action_target"] = action_target
        metrics["contact_at_depth"] = contact_at_depth
        metrics["pose_prior"] = rewards["pose_prior"]
        metrics["height_push"] = height_push
        metrics["action_target"] = action_target
        return rewards


def stage_slug(stage_height: float) -> str:
    return f"stage-{stage_height:.2f}".replace(".", "p")


def default_source() -> Path:
    return EXP22_SOURCE if EXP22_SOURCE.exists() else EXP21_SOURCE


def ppo_config(timesteps: int):
    params = locomotion_params.brax_ppo_config("G1JoystickFlatTerrain")
    params.num_timesteps = timesteps
    params.num_envs = 512
    params.num_evals = 3
    params.num_minibatches = 8
    params.batch_size = 128
    params.episode_length = 300
    params.learning_rate = 2e-5
    params.network_factory.policy_hidden_layer_sizes = (512, 256, 128)
    params.network_factory.value_hidden_layer_sizes = (512, 256, 128)
    return params


def layer_shapes(params: Any) -> dict[str, dict[str, list[int]]]:
    return {
        name: {key: list(value.shape) for key, value in layer.items()}
        for name, layer in params[1]["params"].items()
    }


def compatibility(
    source: Path,
    stage_height: float,
    controller_blend: float,
    freeze_phase: bool,
    blend_schedule: str,
    reference_scale: float | None,
) -> dict:
    env = ContactAwareSquat(
        stage_height=stage_height,
        controller_blend=controller_blend,
        freeze_phase=freeze_phase,
        blend_schedule=blend_schedule,
        reference_scale=reference_scale,
        config_overrides={"impl": "jax"},
    )
    cfg = ppo_config(1)
    networks = ppo_networks.make_ppo_networks(
        observation_size=env.observation_size,
        action_size=env.action_size,
        **cfg.network_factory,
    )
    target = networks.policy_network.init(jax.random.PRNGKey(0))
    with source.open("rb") as f:
        source_params = pickle.load(f)
    target_shapes = {
        name: {key: list(value.shape) for key, value in layer.items()}
        for name, layer in target["params"].items()
    }
    source_shapes = layer_shapes(source_params)
    return {
        "stage_height": stage_height,
        "controller_blend": controller_blend,
        "freeze_phase": freeze_phase,
        "blend_schedule": blend_schedule,
        "reference_scale": reference_scale,
        "source_params": str(source),
        "source_exists": source.exists(),
        "obs_size": env.observation_size,
        "action_size": env.action_size,
        "policy_shape_match": source_shapes == target_shapes,
    }


def rollout_smoke(
    stage_height: float,
    controller_blend: float,
    freeze_phase: bool,
    blend_schedule: str,
    reference_scale: float | None,
    steps: int = 20,
) -> dict:
    env = ContactAwareSquat(
        stage_height=stage_height,
        controller_blend=controller_blend,
        freeze_phase=freeze_phase,
        blend_schedule=blend_schedule,
        reference_scale=reference_scale,
        config_overrides={"impl": "jax"},
    )
    reset_fn = jax.jit(env.reset)
    step_fn = jax.jit(env.step)
    state = reset_fn(jax.random.PRNGKey(0))
    zero = jp.zeros(env.action_size)
    heights = []
    rewards = []
    target_heights = []
    contacts = []
    pose_priors = []
    height_pushes = []
    action_targets = []
    dones = []
    for _ in range(steps):
        state = step_fn(state, zero)
        heights.append(float(state.data.qpos[2]))
        rewards.append(float(state.reward))
        target_heights.append(float(state.metrics["target_height"]))
        contacts.append(float(state.metrics["contact_at_depth"]))
        pose_priors.append(float(state.metrics["pose_prior"]))
        height_pushes.append(float(state.metrics["height_push"]))
        action_targets.append(float(state.metrics["action_target"]))
        dones.append(float(state.done))
    return {
        "stage_height": stage_height,
        "controller_blend": controller_blend,
        "freeze_phase": freeze_phase,
        "blend_schedule": blend_schedule,
        "reference_scale": reference_scale,
        "rollout_steps": steps,
        "reward_first": rewards[0],
        "reward_last": rewards[-1],
        "height_min": min(heights),
        "target_height_min": min(target_heights),
        "contact_at_depth_max": max(contacts),
        "pose_prior_max": max(pose_priors),
        "height_push_max": max(height_pushes),
        "action_target_max": max(action_targets),
        "done_any": any(v > 0 for v in dones),
    }


def build_policy(env: ContactAwareSquat, params_path: Path):
    with params_path.open("rb") as f:
        params = pickle.load(f)
    normalizer_params, policy_params = params[0], params[1]
    cfg = ppo_config(1)
    networks = ppo_networks.make_ppo_networks(
        observation_size=env.observation_size,
        action_size=env.action_size,
        preprocess_observations_fn=running_statistics.normalize,
        **cfg.network_factory,
    )
    return ppo_networks.make_inference_fn(networks)((normalizer_params, policy_params), deterministic=True)


def sensor_adr(model: mujoco.MjModel, name: str) -> int:
    return int(model.sensor(name).adr[0])


def joint_limit_violation(model: mujoco.MjModel, data: mujoco.MjData) -> float:
    worst = 0.0
    for jid in range(model.njnt):
        if model.jnt_type[jid] == mujoco.mjtJoint.mjJNT_FREE:
            continue
        qadr = model.jnt_qposadr[jid]
        lo, hi = model.jnt_range[jid]
        q = data.qpos[qadr]
        if q < lo:
            worst = max(worst, float(lo - q))
        elif q > hi:
            worst = max(worst, float(q - hi))
    return worst


def native_eval(
    stage_height: float,
    controller_blend: float,
    freeze_phase: bool,
    blend_schedule: str,
    reference_scale: float | None,
    params_path: Path,
    seconds: float,
    out_dir: Path,
) -> dict:
    env = ContactAwareSquat(
        stage_height=stage_height,
        controller_blend=controller_blend,
        freeze_phase=freeze_phase,
        blend_schedule=blend_schedule,
        reference_scale=reference_scale,
        config_overrides={"impl": "jax"},
    )
    policy = build_policy(env, params_path)
    ref_joints = np.asarray(env._ref_joints, dtype=np.float32)
    ref_heights = np.asarray(env._ref_heights, dtype=np.float32)
    model = env.mj_model
    data = mujoco.MjData(model)
    key = model.keyframe("knees_bent")
    data.qpos[:] = key.qpos
    default_pose = key.qpos[7:].astype(np.float32).copy()
    data.ctrl[:] = default_pose
    mujoco.mj_forward(model, data)

    gyro_adr = sensor_adr(model, "gyro_pelvis")
    linvel_adr = sensor_adr(model, "local_linvel_pelvis")
    imu_site = model.site("imu_in_pelvis").id
    ctrl_dt = float(env.dt)
    sim_dt = float(model.opt.timestep)
    n_substeps = max(1, round(ctrl_dt / sim_dt))
    total_steps = int(seconds / ctrl_dt)
    phase = np.ones(2, dtype=np.float32) * np.pi if freeze_phase else np.array([0.0, np.pi], dtype=np.float32)
    phase_dt = float(2 * np.pi * ctrl_dt * 1.375)
    last_action = np.zeros(env.action_size, dtype=np.float32)
    command = np.zeros(3, dtype=np.float32)
    gravity_down = np.array([0.0, 0.0, -1.0], dtype=np.float32)
    rng = jax.random.PRNGKey(0)
    foot_site_ids = np.asarray(env._feet_site_id)
    initial_foot_xy = data.site_xpos[foot_site_ids, :2].copy()
    foot_contact_sensor_ids = list(env._feet_floor_found_sensor)

    fell_at = None
    min_height = float("inf")
    final_height = None
    torso_up_min = float("inf")
    max_reference_error = 0.0
    max_height_error = 0.0
    max_joint_violation = 0.0
    action_delta_sum = 0.0
    both_feet_contact_count = 0
    hold_count = 0
    max_foot_slip = 0.0
    samples = []

    def native_effective_blend(step: int) -> float:
        if blend_schedule != "squat":
            return controller_blend
        t = step * ctrl_dt
        if t < 1.2:
            return controller_blend * min(max(t / 1.2, 0.0), 1.0)
        if t < 3.4:
            return controller_blend
        if t < 4.2:
            return controller_blend * min(max(1.0 - (t - 3.4) / 0.8, 0.0), 1.0)
        return 0.0

    for step in range(total_steps):
        gyro = data.sensordata[gyro_adr : gyro_adr + 3]
        linvel = data.sensordata[linvel_adr : linvel_adr + 3]
        gravity = data.site_xmat[imu_site].reshape(3, 3).T @ gravity_down
        obs = np.concatenate([
            linvel,
            gyro,
            gravity,
            command,
            data.qpos[7:] - default_pose,
            data.qvel[6:],
            last_action,
            np.concatenate([np.cos(phase), np.sin(phase)]),
        ]).astype(np.float32)
        rng, action_rng = jax.random.split(rng)
        action, _ = policy({"state": jp.asarray(obs, dtype=jp.float32)[None]}, action_rng)
        action_np = np.asarray(action[0], dtype=np.float32)

        ref_index = min(step, len(ref_heights) - 1)
        reference_error = float(np.mean(np.square(data.qpos[7:22] - ref_joints[ref_index])))
        height = float(data.qpos[2])
        final_height = height
        height_error = float((height - float(ref_heights[ref_index])) ** 2)
        quat = data.qpos[3:7]
        mat = np.empty(9)
        mujoco.mju_quat2Mat(mat, quat)
        up_z = float(mat.reshape(3, 3)[2, 2])
        contacts = [
            float(data.sensordata[model.sensor_adr[sensor_id]]) > 0
            for sensor_id in foot_contact_sensor_ids
        ]
        both_feet = all(contacts)
        both_feet_contact_count += int(both_feet)
        if height <= stage_height + 0.005 and both_feet:
            hold_count += 1
        foot_slip = float(np.max(np.linalg.norm(data.site_xpos[foot_site_ids, :2] - initial_foot_xy, axis=1)))
        fallen = height < 0.45 or up_z < 0.30
        if fallen and fell_at is None:
            fell_at = round(step * ctrl_dt, 3)

        min_height = min(min_height, height)
        torso_up_min = min(torso_up_min, up_z)
        max_reference_error = max(max_reference_error, reference_error)
        max_height_error = max(max_height_error, height_error)
        max_joint_violation = max(max_joint_violation, joint_limit_violation(model, data))
        action_delta_sum += float(np.mean(np.square(action_np - last_action)))
        max_foot_slip = max(max_foot_slip, foot_slip)
        effective_blend = native_effective_blend(step)
        policy_targets = default_pose + action_np * float(env._config.action_scale)
        staged_pose = default_pose.copy()
        staged_pose[:15] = ref_joints[ref_index]
        data.ctrl[:] = (1.0 - effective_blend) * policy_targets + effective_blend * staged_pose
        for _ in range(n_substeps):
            mujoco.mj_step(model, data)
        if freeze_phase:
            phase = np.ones(2, dtype=np.float32) * np.pi
        else:
            phase = np.fmod(phase + phase_dt + np.pi, 2 * np.pi) - np.pi
        last_action = action_np

        if step % max(1, int(0.2 / ctrl_dt)) == 0:
            samples.append({
                "t": round(step * ctrl_dt, 3),
                "base_height": height,
                "target_height": float(ref_heights[ref_index]),
                "reference_error": reference_error,
                "height_error": height_error,
                "up_z": up_z,
                "both_feet_contact": both_feet,
                "foot_slip_distance": foot_slip,
                "effective_controller_blend": effective_blend,
            })

    hold_duration = hold_count * ctrl_dt
    foot_contact_ratio = both_feet_contact_count / max(1, total_steps)
    return_to_stand = final_height is not None and final_height >= 0.74
    pass_gate = (
        fell_at is None
        and min_height <= stage_height + 0.005
        and hold_duration >= 0.5
        and return_to_stand
        and foot_contact_ratio >= 0.90
        and max_joint_violation <= 0.05
    )
    reached_depth = min_height <= stage_height + 0.005
    held_depth = hold_duration >= 0.5
    if pass_gate:
        verdict = "PASS_CONTROLLED_SQUAT"
    elif fell_at is not None:
        verdict = "FAIL_FALL"
    elif not reached_depth:
        verdict = "DEPTH_PENDING"
    elif not held_depth:
        verdict = "HOLD_PENDING"
    elif foot_contact_ratio < 0.90:
        verdict = "CONTACT_GATE_PENDING"
    elif not return_to_stand:
        verdict = "RETURN_PENDING"
    else:
        verdict = "GATE_PENDING"
    native = {
        "stage_height": stage_height,
        "controller_blend": controller_blend,
        "freeze_phase": freeze_phase,
        "blend_schedule": blend_schedule,
        "reference_scale": reference_scale,
        "params_path": str(params_path),
        "seconds": seconds,
        "fell_at": fell_at,
        "upright_s": seconds if fell_at is None else fell_at,
        "min_height": min_height,
        "hold_duration_at_or_below_stage": hold_duration,
        "final_height": final_height,
        "return_to_stand": return_to_stand,
        "torso_up_min": torso_up_min,
        "foot_contact_ratio": foot_contact_ratio,
        "foot_slip_distance": max_foot_slip,
        "max_reference_error": max_reference_error,
        "max_height_error": max_height_error,
        "max_joint_limit_violation": max_joint_violation,
        "mean_action_delta": action_delta_sum / max(1, total_steps),
        "pass_gate": pass_gate,
        "reached_depth": reached_depth,
        "held_depth": held_depth,
        "verdict": verdict,
        "samples": samples,
    }
    (out_dir / "native-eval.json").write_text(json.dumps(native, indent=2), encoding="utf-8")
    return native


def train(
    source: Path,
    stage_height: float,
    controller_blend: float,
    freeze_phase: bool,
    blend_schedule: str,
    reference_scale: float | None,
    timesteps: int,
    attempt_dir: Path,
    seed: int,
) -> dict:
    env = ContactAwareSquat(
        stage_height=stage_height,
        controller_blend=controller_blend,
        freeze_phase=freeze_phase,
        blend_schedule=blend_schedule,
        reference_scale=reference_scale,
        config_overrides={"impl": "jax"},
    )
    eval_env = ContactAwareSquat(
        stage_height=stage_height,
        controller_blend=controller_blend,
        freeze_phase=freeze_phase,
        blend_schedule=blend_schedule,
        reference_scale=reference_scale,
        config_overrides={"impl": "jax"},
    )
    cfg = ppo_config(timesteps)
    with source.open("rb") as f:
        source_params = pickle.load(f)
    network_factory = functools.partial(ppo_networks.make_ppo_networks, **cfg.network_factory)
    train_params = dict(cfg)
    train_params.pop("network_factory", None)
    num_eval_envs = train_params.pop("num_eval_envs", 128)
    rewards: list[tuple[int, float]] = []

    def progress(step, metrics):
        reward = metrics.get("eval/episode_reward")
        if reward is not None:
            rewards.append((int(step), float(reward)))
            print(f"{step}: reward={reward:.3f}", flush=True)

    start = time.monotonic()
    make_inference_fn, learned_params, _ = ppo.train(
        environment=env,
        eval_env=eval_env,
        **train_params,
        network_factory=network_factory,
        seed=seed,
        wrap_env_fn=wrapper.wrap_for_brax_training,
        num_eval_envs=num_eval_envs,
        progress_fn=progress,
        restore_params=source_params,
        restore_value_fn=True,
    )
    del make_inference_fn
    elapsed = time.monotonic() - start
    out_dir = attempt_dir / "train"
    out_dir.mkdir(parents=True, exist_ok=True)
    params_path = out_dir / "params.pkl"
    with params_path.open("wb") as f:
        pickle.dump(learned_params, f)
    rewards_path = out_dir / "rewards.txt"
    rewards_path.write_text(
        "\n".join([
            f"# stage_height={stage_height}",
            f"# controller_blend={controller_blend}",
            f"# freeze_phase={freeze_phase}",
            f"# blend_schedule={blend_schedule}",
            f"# reference_scale={reference_scale}",
            f"# timesteps={timesteps} train_min={elapsed/60:.2f} seed={seed} source={source}",
            *[f"{s}\t{r}" for s, r in rewards],
        ]) + "\n",
        encoding="utf-8",
    )
    return {
        "stage_height": stage_height,
        "controller_blend": controller_blend,
        "freeze_phase": freeze_phase,
        "blend_schedule": blend_schedule,
        "reference_scale": reference_scale,
        "timesteps": timesteps,
        "train_min": elapsed / 60,
        "seed": seed,
        "reward_points": rewards,
        "source_params": str(source),
        "params_path": str(params_path.relative_to(EXP_DIR)),
        "rewards_path": str(rewards_path.relative_to(EXP_DIR)),
    }


def next_attempt_dir(stage_dir: Path, attempt_name: str | None) -> Path:
    attempts = stage_dir / "attempts"
    attempts.mkdir(parents=True, exist_ok=True)
    if attempt_name:
        return attempts / attempt_name
    existing = []
    for path in attempts.glob("attempt-*"):
        match = re.fullmatch(r"attempt-(\d+)", path.name)
        if match:
            existing.append(int(match.group(1)))
    return attempts / f"attempt-{(max(existing) + 1 if existing else 1):03d}"


def score(native: dict) -> tuple[int, float, float, float]:
    return (
        int(native["pass_gate"]),
        float(native["foot_contact_ratio"]),
        -abs(float(native["min_height"]) - 0.74),
        float(native["hold_duration_at_or_below_stage"]),
    )


def update_best(stage_dir: Path, result: dict) -> None:
    best_path = stage_dir / "best.json"
    if best_path.exists():
        best = json.loads(best_path.read_text(encoding="utf-8"))
        if score(result["native"]) <= score(best["native"]):
            write_summary(stage_dir, best)
            return
    best_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    write_summary(stage_dir, result)


def write_summary(stage_dir: Path, result: dict) -> None:
    native = result["native"]
    lines = [
        "# G1 Controlled Squat Stage 0.74 Summary",
        "",
        f"- Best attempt: `{result['attempt']}`",
        f"- Verdict: {native['verdict']}",
        f"- Pass gate: {native['pass_gate']}",
        "",
        "| Metric | Value | Gate |",
        "|---|---:|---:|",
        f"| fell_at | {native['fell_at']} | None |",
        f"| min_height | {native['min_height']:.4f} | <= 0.745 |",
        f"| hold_duration | {native['hold_duration_at_or_below_stage']:.2f}s | >= 0.50s |",
        f"| final_height | {native['final_height']:.4f} | >= 0.740 |",
        f"| foot_contact_ratio | {native['foot_contact_ratio']:.2f} | >= 0.90 |",
        f"| joint_limit_violation | {native['max_joint_limit_violation']:.4f} | <= 0.05 |",
        "",
    ]
    (stage_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=None)
    parser.add_argument("--stage-height", type=float, default=0.74)
    parser.add_argument("--seconds", type=float, default=6.0)
    parser.add_argument("--controller-blend", type=float, default=0.0)
    parser.add_argument("--freeze-phase", action="store_true")
    parser.add_argument("--blend-schedule", choices=["fixed", "squat"], default="fixed")
    parser.add_argument("--reference-scale", type=float, default=None)
    parser.add_argument("--train", action="store_true")
    parser.add_argument("--timesteps", type=int, default=20_000)
    parser.add_argument("--seed", type=int, default=8)
    parser.add_argument("--attempt", default=None)
    args = parser.parse_args()

    source = args.source or default_source()
    stage_dir = VERIFY / stage_slug(args.stage_height)
    attempt_dir = next_attempt_dir(stage_dir, args.attempt)
    attempt_dir.mkdir(parents=True, exist_ok=True)
    result = {
        "planning_gate": {
            "team_validation_mode": "manual-pass",
            "spec_delta": "stage 0.74 controlled squat PASS as a single experiment with attempts",
            "dod": [
                "compatibility and reward smoke execute",
                "native controlled squat gate evaluated",
                "attempt result plus best summary produced",
            ],
        },
        "attempt": attempt_dir.name,
        "stage_height": args.stage_height,
        "controller_blend": args.controller_blend,
        "freeze_phase": args.freeze_phase,
        "blend_schedule": args.blend_schedule,
        "reference_scale": args.reference_scale,
        "source_params": str(source),
        "compatibility": compatibility(
            source,
            args.stage_height,
            args.controller_blend,
            args.freeze_phase,
            args.blend_schedule,
            args.reference_scale,
        ),
        "rollout": rollout_smoke(
            args.stage_height,
            args.controller_blend,
            args.freeze_phase,
            args.blend_schedule,
            args.reference_scale,
        ),
    }
    if not result["compatibility"]["policy_shape_match"]:
        raise SystemExit("source and target policy shapes do not match")
    if args.train:
        result["train"] = train(
            source,
            args.stage_height,
            args.controller_blend,
            args.freeze_phase,
            args.blend_schedule,
            args.reference_scale,
            args.timesteps,
            attempt_dir,
            args.seed,
        )
        params_path = attempt_dir / "train" / "params.pkl"
    else:
        params_path = source
    result["native"] = native_eval(
        args.stage_height,
        args.controller_blend,
        args.freeze_phase,
        args.blend_schedule,
        args.reference_scale,
        params_path,
        args.seconds,
        attempt_dir,
    )
    result["verdict"] = result["native"]["verdict"]
    (attempt_dir / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    update_best(stage_dir, result)
    print(result["verdict"], json.dumps(result["native"], indent=2), flush=True)


if __name__ == "__main__":
    main()
