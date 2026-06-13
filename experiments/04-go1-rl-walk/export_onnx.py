"""S3 — 학습 params.pkl -> go1_policy.onnx + obs_spec.json.

정책 추론(deterministic) = tanh( MLP_silu( (obs-mean)/std )[:12] ).
손으로 ONNX 그래프를 구성한 뒤, **onnxruntime 출력 == jax make_inference_fn 출력**을
난수 obs 50개에서 수치 비교(assert < 1e-4)해 parity를 증명한다(이 assert가 안전망 —
정규화 순서/activation 가정이 틀리면 여기서 잡힌다).

실행: python export_onnx.py <run_dir>   (run_dir/params.pkl 필요)
"""
import functools, json, os, pickle, sys
import numpy as np
import jax, jax.numpy as jp
from brax.training.agents.ppo import networks as ppo_networks
from brax.training.acme import running_statistics
from mujoco_playground import registry
from mujoco_playground.config import locomotion_params

RUN = sys.argv[1] if len(sys.argv) > 1 else "/home/yusun/playground-go1/runs/go1flat"
ENV = "Go1JoystickFlatTerrain"
OBS_SIZE = {"state": (48,), "privileged_state": (123,)}
ACT = 12

# --- load trained params ---
with open(os.path.join(RUN, "params.pkl"), "rb") as f:
    params = pickle.load(f)
normalizer_params, policy_params = params[0], params[1]

# --- rebuild network + ground-truth inference fn (same factory as training) ---
ppo_params = locomotion_params.brax_ppo_config(ENV)
nets = ppo_networks.make_ppo_networks(
    observation_size=OBS_SIZE, action_size=ACT,
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
W = [np.asarray(P[f"hidden_{i}"]["kernel"], np.float32) for i in range(4)]
B = [np.asarray(P[f"hidden_{i}"]["bias"], np.float32) for i in range(4)]
mean = np.asarray(normalizer_params.mean["state"], np.float32)
std = np.asarray(normalizer_params.std["state"], np.float32)

# default_pose (home keyframe) — obs/ctrl 재구성에 필수 (Phase 2/3 진실원천)
_env = registry.load(ENV, config_overrides={"impl": "jax"})
default_pose = np.asarray(_env.mj_model.keyframe("home").qpos[7:], np.float32)
assert default_pose.shape == (ACT,), default_pose.shape

def silu(x):
    return x * (1.0 / (1.0 + np.exp(-x)))

def np_infer(o):
    x = (np.asarray(o, np.float32) - mean) / std
    x = silu(x @ W[0] + B[0])
    x = silu(x @ W[1] + B[1])
    x = silu(x @ W[2] + B[2])
    x = x @ W[3] + B[3]            # (24,) no activation
    return np.tanh(x[:ACT])         # mode of NormalTanh = tanh(loc), loc = first 12

# sanity: numpy vs jax
errs = [np.max(np.abs(np_infer(o) - jax_infer(o)))
        for o in np.random.randn(20, 48).astype(np.float32)]
print(f"[np vs jax] max abs err = {max(errs):.2e}")

# --- build ONNX graph by hand ---
from onnx import helper, TensorProto, numpy_helper, checker
import onnx

def init(name, arr):
    return numpy_helper.from_array(arr.astype(np.float32), name)

nodes = [
    helper.make_node("Sub", ["obs", "mean"], ["n0"]),
    helper.make_node("Div", ["n0", "std"], ["x0"]),
    # layer 0
    helper.make_node("MatMul", ["x0", "W0"], ["m0"]),
    helper.make_node("Add", ["m0", "B0"], ["a0"]),
    helper.make_node("Sigmoid", ["a0"], ["s0"]),
    helper.make_node("Mul", ["a0", "s0"], ["h0"]),
    # layer 1
    helper.make_node("MatMul", ["h0", "W1"], ["m1"]),
    helper.make_node("Add", ["m1", "B1"], ["a1"]),
    helper.make_node("Sigmoid", ["a1"], ["s1"]),
    helper.make_node("Mul", ["a1", "s1"], ["h1"]),
    # layer 2
    helper.make_node("MatMul", ["h1", "W2"], ["m2"]),
    helper.make_node("Add", ["m2", "B2"], ["a2"]),
    helper.make_node("Sigmoid", ["a2"], ["s2"]),
    helper.make_node("Mul", ["a2", "s2"], ["h2"]),
    # output layer (no activation) -> 24
    helper.make_node("MatMul", ["h2", "W3"], ["m3"]),
    helper.make_node("Add", ["m3", "B3"], ["logits"]),
    # take first 12 (loc) then tanh
    helper.make_node("Slice", ["logits", "s_start", "s_end", "s_axis"], ["loc"]),
    helper.make_node("Tanh", ["loc"], ["action"]),
]
# Slice needs int64 starts/ends/axes as initializers
inits = [
    init("mean", mean), init("std", std),
    init("W0", W[0]), init("B0", B[0]),
    init("W1", W[1]), init("B1", B[1]),
    init("W2", W[2]), init("B2", B[2]),
    init("W3", W[3]), init("B3", B[3]),
    numpy_helper.from_array(np.array([0], np.int64), "s_start"),
    numpy_helper.from_array(np.array([ACT], np.int64), "s_end"),
    numpy_helper.from_array(np.array([1], np.int64), "s_axis"),  # feature axis (batched [1,24])
]

graph = helper.make_graph(
    nodes, "go1_policy",
    [helper.make_tensor_value_info("obs", TensorProto.FLOAT, [1, 48])],
    [helper.make_tensor_value_info("action", TensorProto.FLOAT, [1, ACT])],
    initializer=inits,
)
model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 17)])
model.ir_version = 10
checker.check_model(model)
onnx_path = os.path.join(RUN, "go1_policy.onnx")
onnx.save(model, onnx_path)

# --- validate onnxruntime vs jax ---
import onnxruntime as ort
sess = ort.InferenceSession(onnx_path, providers=["CPUExecutionProvider"])
def onnx_infer(o):
    return sess.run(None, {"obs": np.asarray(o, np.float32)[None]})[0][0]

errs2 = [np.max(np.abs(onnx_infer(o) - jax_infer(o)))
         for o in np.random.randn(50, 48).astype(np.float32)]
mx = float(max(errs2))
print(f"[onnx vs jax] max abs err over 50 obs = {mx:.2e}")
assert mx < 1e-4, f"PARITY FAIL: {mx}"
print("PARITY PASS -> saved", onnx_path)

# --- obs_spec.json (web/desktop parity 진실원천) ---
spec = {
    "env": ENV, "obs_dim": 48, "act_dim": ACT,
    "layout": [
        ["local_linvel", 3], ["gyro", 3], ["gravity_projected", 3],
        ["joint_angles_minus_default", 12], ["joint_vel", 12],
        ["last_act", 12], ["command", 3],
    ],
    "normalization": "(obs - mean) / std, baked into onnx",
    "mean": mean.tolist(), "std": std.tolist(),
    "default_pose": default_pose.tolist(),  # home keyframe qpos[7:] (12)
    "action": "motor_targets = default_pose + action * 0.5; ctrl_dt=0.02 (50Hz); n_substeps=5",
    "activation": "silu", "policy_mlp": [512, 256, 128, 24],
    "onnx": "go1_policy.onnx (input obs[1,48] -> action[1,12] in [-1,1])",
}
with open(os.path.join(RUN, "obs_spec.json"), "w") as f:
    json.dump(spec, f, indent=2)
print("wrote obs_spec.json")
