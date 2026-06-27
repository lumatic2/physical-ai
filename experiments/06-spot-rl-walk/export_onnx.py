"""S3 — 학습 params.pkl -> spot_policy.onnx + obs_spec.json (numerics 채움).

exp04 export의 일반화: Spot 정책망은 hidden 4층(128⁴)+출력 = hidden_0..hidden_4 (5층)이라
exp04의 고정 4블록 그래프가 안 맞는다. 여기선 hidden_i 개수를 세서 ONNX 그래프를 동적으로 쌓는다.
정책 추론(deterministic) = tanh( silu_MLP( (obs-mean)/std )[:12] ). onnxruntime 출력 ==
jax make_inference_fn 출력을 난수 obs 50개에서 비교(assert<1e-4)해 parity 증명.

실행: python export_onnx.py <run_dir> [spec_out.json]   (run_dir/params.pkl 필요)
"""
import json, os, pickle, sys
import numpy as np
import jax, jax.numpy as jp
from brax.training.agents.ppo import networks as ppo_networks
from brax.training.acme import running_statistics
from mujoco_playground import registry
from mujoco_playground.config import locomotion_params

RUN = sys.argv[1] if len(sys.argv) > 1 else "/home/<user>/playground-go1/runs/spotflat"
SPEC_OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(RUN, "obs_spec.json")
ENV = "SpotFlatTerrainJoystick"
OBS = 81
OBS_SIZE = {"state": (OBS,), "privileged_state": (167,)}
ACT = 12

with open(os.path.join(RUN, "params.pkl"), "rb") as f:
    params = pickle.load(f)
normalizer_params, policy_params = params[0], params[1]

# rebuild ground-truth inference fn (same factory as training)
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

# extract N layers dynamically (hidden_0..hidden_{n-1}; last is the linear output -> 2*ACT)
P = policy_params["params"]
nlayers = sum(1 for k in P if k.startswith("hidden_"))
W = [np.asarray(P[f"hidden_{i}"]["kernel"], np.float32) for i in range(nlayers)]
B = [np.asarray(P[f"hidden_{i}"]["bias"], np.float32) for i in range(nlayers)]
mean = np.asarray(normalizer_params.mean["state"], np.float32)
std = np.asarray(normalizer_params.std["state"], np.float32)
print(f"layers={nlayers}  in={W[0].shape[0]}  out={W[-1].shape[1]} (=2*ACT)")
assert W[0].shape[0] == OBS and W[-1].shape[1] == 2 * ACT

_env = registry.load(ENV, config_overrides={"impl": "jax"})
default_pose = np.asarray(_env.mj_model.keyframe("home").qpos[7:], np.float32)
assert default_pose.shape == (ACT,), default_pose.shape

def silu(x):
    return x * (1.0 / (1.0 + np.exp(-x)))

def np_infer(o):
    x = (np.asarray(o, np.float32) - mean) / std
    for i in range(nlayers - 1):
        x = silu(x @ W[i] + B[i])
    x = x @ W[-1] + B[-1]            # output, no activation -> 2*ACT
    return np.tanh(x[:ACT])           # mode of NormalTanh = tanh(loc), loc = first ACT

errs = [np.max(np.abs(np_infer(o) - jax_infer(o)))
        for o in np.random.randn(20, OBS).astype(np.float32)]
print(f"[np vs jax] max abs err = {max(errs):.2e}")

# --- ONNX graph, built dynamically over nlayers ---
from onnx import helper, TensorProto, numpy_helper, checker
import onnx

nodes = [helper.make_node("Sub", ["obs", "mean"], ["n0"]),
         helper.make_node("Div", ["n0", "std"], ["x0"])]
inits = [numpy_helper.from_array(mean, "mean"), numpy_helper.from_array(std, "std")]
cur = "x0"
for i in range(nlayers):
    inits += [numpy_helper.from_array(W[i], f"W{i}"), numpy_helper.from_array(B[i], f"B{i}")]
    nodes.append(helper.make_node("MatMul", [cur, f"W{i}"], [f"m{i}"]))
    nodes.append(helper.make_node("Add", [f"m{i}", f"B{i}"], [f"a{i}"]))
    if i < nlayers - 1:              # silu = a * sigmoid(a)
        nodes.append(helper.make_node("Sigmoid", [f"a{i}"], [f"sg{i}"]))
        nodes.append(helper.make_node("Mul", [f"a{i}", f"sg{i}"], [f"h{i}"]))
        cur = f"h{i}"
    else:
        cur = f"a{i}"                # logits (2*ACT), no activation
nodes.append(helper.make_node("Slice", [cur, "s_start", "s_end", "s_axis"], ["loc"]))
nodes.append(helper.make_node("Tanh", ["loc"], ["action"]))
inits += [numpy_helper.from_array(np.array([0], np.int64), "s_start"),
          numpy_helper.from_array(np.array([ACT], np.int64), "s_end"),
          numpy_helper.from_array(np.array([1], np.int64), "s_axis")]

graph = helper.make_graph(
    nodes, "spot_policy",
    [helper.make_tensor_value_info("obs", TensorProto.FLOAT, [1, OBS])],
    [helper.make_tensor_value_info("action", TensorProto.FLOAT, [1, ACT])],
    initializer=inits,
)
model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 17)])
model.ir_version = 10
checker.check_model(model)
onnx_path = os.path.join(RUN, "spot_policy.onnx")
onnx.save(model, onnx_path)

import onnxruntime as ort
sess = ort.InferenceSession(onnx_path, providers=["CPUExecutionProvider"])
def onnx_infer(o):
    return sess.run(None, {"obs": np.asarray(o, np.float32)[None]})[0][0]

errs2 = [np.max(np.abs(onnx_infer(o) - jax_infer(o)))
         for o in np.random.randn(50, OBS).astype(np.float32)]
mx = float(max(errs2))
print(f"[onnx vs jax] max abs err over 50 obs = {mx:.2e}")
assert mx < 1e-4, f"PARITY FAIL: {mx}"
print("PARITY PASS ->", onnx_path)

# --- obs_spec.json (web/native parity 진실원천) ---
spec = {
    "env": ENV, "obs_dim": OBS, "act_dim": ACT,
    "_source": "playground spot/joystick.py _get_obs state branch",
    "layout": [
        ["gyro", 3], ["gravity_projected", 3], ["joint_angles_minus_default", 12],
        ["qpos_error_history", 36], ["feet_pos", 12], ["last_act", 12], ["command", 3],
    ],
    "normalization": "(obs - mean) / std, baked into onnx",
    "mean": mean.tolist(), "std": std.tolist(),
    "default_pose": default_pose.tolist(),
    "action": "motor_targets = clip(default_pose + action*0.3, lowers, uppers); ctrl_dt=0.02; Kp=300",
    "activation": "silu", "policy_mlp": [int(W[i].shape[1]) for i in range(nlayers)],
    "onnx": "spot_policy.onnx (obs[1,81] -> action[1,12] in [-1,1])",
    "notes": {
        "no_phase_clock": "gait phase commented out in env — no external clock (unlike G1).",
        "no_linear_velocity": "policy state has NO local_linvel (critic-only).",
        "qpos_error_history": "history_len=3 -> 36. each step prepend (joint_angles - motor_targets). STATEFUL.",
        "feet_pos": "4 feet site_xpos raveled (12). resolve frame against bundled scene.",
    },
}
with open(SPEC_OUT, "w", encoding="utf-8") as f:
    json.dump(spec, f, indent=2, ensure_ascii=False)
print("wrote", SPEC_OUT)
