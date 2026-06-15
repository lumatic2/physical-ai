"""Export Barkour PPO params to ONNX and write obs_spec.json.

Usage:
  python export_onnx.py <run_dir>
"""
import functools
import json
import os
import pickle
import re
import sys

import jax
import jax.numpy as jp
import numpy as np
from brax.training.acme import running_statistics
from brax.training.agents.ppo import networks as ppo_networks
from mujoco_playground import registry
from mujoco_playground.config import locomotion_params


RUN = sys.argv[1] if len(sys.argv) > 1 else "/home/yusun/playground-go1/runs/barkour"
ENV = "BarkourJoystick"
OBS_DIM = 465
ACT_DIM = 12

with open(os.path.join(RUN, "params.pkl"), "rb") as f:
    params = pickle.load(f)
normalizer_params, policy_params = params[0], params[1]

ppo_params = locomotion_params.brax_ppo_config(ENV)
nets = ppo_networks.make_ppo_networks(
    observation_size=OBS_DIM,
    action_size=ACT_DIM,
    preprocess_observations_fn=running_statistics.normalize,
    **ppo_params.network_factory,
)
make_inf = ppo_networks.make_inference_fn(nets)
jpolicy = make_inf((normalizer_params, policy_params), deterministic=True)


def jax_infer(obs):
    act, _ = jpolicy(jp.asarray(obs, jp.float32)[None], jax.random.PRNGKey(0))
    return np.asarray(act[0], np.float32)


def layer_index(name):
    match = re.fullmatch(r"hidden_(\d+)", name)
    return int(match.group(1)) if match else None


P = policy_params["params"]
layer_names = sorted(
    [name for name in P if layer_index(name) is not None],
    key=layer_index,
)
if not layer_names:
    raise RuntimeError(f"No hidden_N layers found: {list(P)}")
W = [np.asarray(P[name]["kernel"], np.float32) for name in layer_names]
B = [np.asarray(P[name]["bias"], np.float32) for name in layer_names]
mean = np.asarray(normalizer_params.mean, np.float32)
std = np.asarray(normalizer_params.std, np.float32)
if mean.shape != (OBS_DIM,):
    mean = np.asarray(normalizer_params.mean["state"], np.float32)
    std = np.asarray(normalizer_params.std["state"], np.float32)
assert mean.shape == (OBS_DIM,), mean.shape

env = registry.load(ENV, config_overrides={"impl": "jax"})
model = env.mj_model
default_pose = np.asarray(model.keyframe("home").qpos[7:], np.float32)
assert default_pose.shape == (ACT_DIM,), default_pose.shape


def silu(x):
    return x / (1.0 + np.exp(-x))


def np_infer(obs):
    x = (np.asarray(obs, np.float32) - mean) / std
    for kernel, bias in zip(W[:-1], B[:-1]):
        x = silu(x @ kernel + bias)
    x = x @ W[-1] + B[-1]
    return np.tanh(x[:ACT_DIM])


errs = [
    np.max(np.abs(np_infer(obs) - jax_infer(obs)))
    for obs in np.random.randn(20, OBS_DIM).astype(np.float32)
]
print(f"[np vs jax] max abs err = {max(errs):.2e}")

from onnx import TensorProto, checker, helper, numpy_helper
import onnx


def init(name, arr):
    return numpy_helper.from_array(arr.astype(np.float32), name)


nodes = [
    helper.make_node("Sub", ["obs", "mean"], ["n0"]),
    helper.make_node("Div", ["n0", "std"], ["x0"]),
]
prev = "x0"
inits = [init("mean", mean), init("std", std)]
for i, (kernel, bias) in enumerate(zip(W, B)):
    inits.extend([init(f"W{i}", kernel), init(f"B{i}", bias)])
    nodes.append(helper.make_node("MatMul", [prev, f"W{i}"], [f"m{i}"]))
    nodes.append(helper.make_node("Add", [f"m{i}", f"B{i}"], [f"a{i}"]))
    if i < len(W) - 1:
        nodes.append(helper.make_node("Sigmoid", [f"a{i}"], [f"s{i}"]))
        nodes.append(helper.make_node("Mul", [f"a{i}", f"s{i}"], [f"h{i}"]))
        prev = f"h{i}"
    else:
        prev = f"a{i}"

nodes.extend(
    [
        helper.make_node("Slice", [prev, "s_start", "s_end", "s_axis"], ["loc"]),
        helper.make_node("Tanh", ["loc"], ["action"]),
    ]
)
inits.extend(
    [
        numpy_helper.from_array(np.array([0], np.int64), "s_start"),
        numpy_helper.from_array(np.array([ACT_DIM], np.int64), "s_end"),
        numpy_helper.from_array(np.array([1], np.int64), "s_axis"),
    ]
)

graph = helper.make_graph(
    nodes,
    "barkour_policy",
    [helper.make_tensor_value_info("obs", TensorProto.FLOAT, [1, OBS_DIM])],
    [helper.make_tensor_value_info("action", TensorProto.FLOAT, [1, ACT_DIM])],
    initializer=inits,
)
onnx_model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 17)])
onnx_model.ir_version = 10
checker.check_model(onnx_model)
onnx_path = os.path.join(RUN, "barkour_policy.onnx")
onnx.save(onnx_model, onnx_path)

import onnxruntime as ort

sess = ort.InferenceSession(onnx_path, providers=["CPUExecutionProvider"])


def onnx_infer(obs):
    return sess.run(None, {"obs": np.asarray(obs, np.float32)[None]})[0][0]


errs2 = [
    np.max(np.abs(onnx_infer(obs) - jax_infer(obs)))
    for obs in np.random.randn(50, OBS_DIM).astype(np.float32)
]
mx = float(max(errs2))
print(f"[onnx vs jax] max abs err over 50 obs = {mx:.2e}")
assert mx < 1e-4, f"PARITY FAIL: {mx}"

spec = {
    "env": ENV,
    "obs_dim": OBS_DIM,
    "act_dim": ACT_DIM,
    "layout": [
        ["yaw_rate_z_scaled", 1],
        ["upvector", 3],
        ["command_scaled", 3],
        ["joint_angles_minus_default", 12],
        ["last_act", 12],
    ],
    "history": "15 frames x 31 current obs = 465. New frame is inserted at indices 0:31 after jp.roll(obs_history, 31).",
    "normalization": "(obs - mean) / std, baked into onnx",
    "mean": mean.tolist(),
    "std": std.tolist(),
    "default_pose": default_pose.tolist(),
    "action": "motor_targets = clip(default_pose + action * 0.3, lowers, uppers); ctrl_dt=0.02; sim_dt=0.004",
    "activation": "silu",
    "policy_layers": [list(w.shape) for w in W],
    "onnx": "barkour_policy.onnx (input obs[1,465] -> action[1,12] in [-1,1])",
}
with open(os.path.join(RUN, "obs_spec.json"), "w", encoding="utf-8") as f:
    json.dump(spec, f, indent=2)

print("PARITY PASS -> saved", onnx_path)
print("wrote obs_spec.json")
