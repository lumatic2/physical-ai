"""S3 (G1) — 학습 params.pkl -> g1_policy.onnx + obs_spec.json.

04-go1-rl-walk/export_onnx.py 의 G1 버전. 차이: obs/act 크기를 env에서 자동 유도(G1은 obs 103,
act 29), default_pose = keyframe("knees_bent").qpos[7:], MLP 출력 = 2*act_dim(앞 act_dim이 loc).
정책 추론(deterministic) = tanh( MLP_silu( (obs-mean)/std )[:act_dim] ). onnxruntime == jax parity assert.

실행: python export_onnx.py <run_dir>   (run_dir/params.pkl 필요)
"""
import json, os, pickle, sys
import numpy as np
import jax, jax.numpy as jp
from brax.training.agents.ppo import networks as ppo_networks
from brax.training.acme import running_statistics
from mujoco_playground import registry
from mujoco_playground.config import locomotion_params

RUN = sys.argv[1] if len(sys.argv) > 1 else "/home/yusun/playground-go1/runs/g1flat"
ENV = "G1JoystickFlatTerrain"

# --- derive obs/act sizes + default_pose from the env (no hardcoded dims) ---
_env = registry.load(ENV, config_overrides={"impl": "jax"})
obs_size = _env.observation_size                 # {"state":(103,), "privileged_state":(N,)}
STATE = int(obs_size["state"][0] if isinstance(obs_size["state"], tuple) else obs_size["state"])
ACT = int(_env.action_size)
default_pose = np.asarray(_env.mj_model.keyframe("knees_bent").qpos[7:], np.float32)
assert default_pose.shape == (ACT,), (default_pose.shape, ACT)
print(f"STATE={STATE} ACT={ACT}", flush=True)

# --- load trained params ---
with open(os.path.join(RUN, "params.pkl"), "rb") as f:
    params = pickle.load(f)
normalizer_params, policy_params = params[0], params[1]

# --- rebuild network + ground-truth inference fn (same factory as training) ---
ppo_params = locomotion_params.brax_ppo_config(ENV)
nets = ppo_networks.make_ppo_networks(
    observation_size=obs_size, action_size=ACT,
    preprocess_observations_fn=running_statistics.normalize,
    **ppo_params.network_factory,
)
make_inf = ppo_networks.make_inference_fn(nets)
jpolicy = make_inf((normalizer_params, policy_params), deterministic=True)

def jax_infer(o):
    act, _ = jpolicy({"state": jp.asarray(o, jp.float32)[None]}, jax.random.PRNGKey(0))
    return np.asarray(act[0], np.float32)

# --- extract weights for hand graph ---
P = policy_params["params"]
n_hidden = sum(1 for k in P if k.startswith("hidden_"))
W = [np.asarray(P[f"hidden_{i}"]["kernel"], np.float32) for i in range(n_hidden)]
B = [np.asarray(P[f"hidden_{i}"]["bias"], np.float32) for i in range(n_hidden)]
mean = np.asarray(normalizer_params.mean["state"], np.float32)
std = np.asarray(normalizer_params.std["state"], np.float32)

def silu(x):
    return x * (1.0 / (1.0 + np.exp(-x)))

def np_infer(o):
    x = (np.asarray(o, np.float32) - mean) / std
    for i in range(n_hidden - 1):
        x = silu(x @ W[i] + B[i])
    x = x @ W[-1] + B[-1]              # (2*ACT,) no activation
    return np.tanh(x[:ACT])            # mode of NormalTanh = tanh(loc)

errs = [np.max(np.abs(np_infer(o) - jax_infer(o)))
        for o in np.random.randn(20, STATE).astype(np.float32)]
print(f"[np vs jax] max abs err = {max(errs):.2e}", flush=True)

# --- build ONNX graph by hand ---
from onnx import helper, TensorProto, numpy_helper, checker
import onnx

def init(name, arr):
    return numpy_helper.from_array(arr.astype(np.float32), name)

nodes = [helper.make_node("Sub", ["obs", "mean"], ["n0"]),
         helper.make_node("Div", ["n0", "std"], ["x0"])]
prev = "x0"
inits = [init("mean", mean), init("std", std)]
for i in range(n_hidden):
    inits += [init(f"W{i}", W[i]), init(f"B{i}", B[i])]
    nodes.append(helper.make_node("MatMul", [prev, f"W{i}"], [f"m{i}"]))
    nodes.append(helper.make_node("Add", [f"m{i}", f"B{i}"], [f"a{i}"]))
    if i < n_hidden - 1:
        nodes.append(helper.make_node("Sigmoid", [f"a{i}"], [f"s{i}"]))
        nodes.append(helper.make_node("Mul", [f"a{i}", f"s{i}"], [f"h{i}"]))
        prev = f"h{i}"
    else:
        nodes.append(helper.make_node("Slice", ["a%d" % i, "s_start", "s_end", "s_axis"], ["loc"]))
        nodes.append(helper.make_node("Tanh", ["loc"], ["action"]))
inits += [numpy_helper.from_array(np.array([0], np.int64), "s_start"),
          numpy_helper.from_array(np.array([ACT], np.int64), "s_end"),
          numpy_helper.from_array(np.array([1], np.int64), "s_axis")]

graph = helper.make_graph(
    nodes, "g1_policy",
    [helper.make_tensor_value_info("obs", TensorProto.FLOAT, [1, STATE])],
    [helper.make_tensor_value_info("action", TensorProto.FLOAT, [1, ACT])],
    initializer=inits,
)
model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 17)])
model.ir_version = 10
checker.check_model(model)
onnx_path = os.path.join(RUN, "g1_policy.onnx")
onnx.save(model, onnx_path)

import onnxruntime as ort
sess = ort.InferenceSession(onnx_path, providers=["CPUExecutionProvider"])
def onnx_infer(o):
    return sess.run(None, {"obs": np.asarray(o, np.float32)[None]})[0][0]

errs2 = [np.max(np.abs(onnx_infer(o) - jax_infer(o)))
         for o in np.random.randn(50, STATE).astype(np.float32)]
mx = float(max(errs2))
print(f"[onnx vs jax] max abs err over 50 obs = {mx:.2e}", flush=True)
assert mx < 1e-4, f"PARITY FAIL: {mx}"
print("PARITY PASS -> saved", onnx_path, flush=True)

# --- obs_spec.json (web/desktop parity 진실원천) ---
spec = {
    "env": ENV, "obs_dim": STATE, "act_dim": ACT,
    "layout": [
        ["local_linvel", 3], ["gyro", 3], ["gravity_projected", 3], ["command", 3],
        ["joint_angles_minus_default", ACT], ["joint_vel", ACT], ["last_act", ACT],
        ["phase_cos_sin", 4],
    ],
    "normalization": "(obs - mean) / std, baked into onnx",
    "mean": mean.tolist(), "std": std.tolist(),
    "default_pose": default_pose.tolist(),   # knees_bent keyframe qpos[7:] (29)
    "gait": {"phase_init": [0.0, 3.141592653589793], "gait_freq_hz": 1.375,
             "phase_dt": "2*pi*ctrl_dt*gait_freq", "note": "phase(2) advances each ctrl step; obs uses concat([cos(phase),sin(phase)])"},
    "action": "motor_targets = default_pose + action * 0.5; ctrl_dt=0.02 (50Hz); n_substeps=5",
    "activation": "silu", "policy_mlp": list(ppo_params.network_factory.policy_hidden_layer_sizes) + [2 * ACT],
    "gravity_site": "imu_in_pelvis", "gyro_sensor": "gyro", "local_linvel_sensor": "local_linvel",
    "onnx": f"g1_policy.onnx (input obs[1,{STATE}] -> action[1,{ACT}] in [-1,1])",
}
with open(os.path.join(RUN, "obs_spec.json"), "w") as f:
    json.dump(spec, f, indent=2)
print("wrote obs_spec.json", flush=True)
