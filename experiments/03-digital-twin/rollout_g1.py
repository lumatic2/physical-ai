"""Phase 2 (G1) — closed-loop ONNX rollout on the bundled G1 scene + golden parity.

rollout_policy.py 의 G1 버전. 차이: obs 레이아웃이 [linvel, gyro, gravity, command, joints(29),
joint_vel(29), last_act(29), phase_cos_sin(4)] = 103 이고, gait phase clock(2-vec, 매 ctrl step
전진)을 JS 와 동일하게 유지한다. init = keyframe("knees_bent"). 번들 씬 obs == 학습 golden 검증 →
g1_walk_trajectory.json 덤프 → policy.indices 를 experiments.json 에 박제.

  python rollout_g1.py [seconds]
"""
import sys, json
import numpy as np
import mujoco
import onnxruntime as ort
from harness import get_experiment, REGISTRY

SECONDS = float(sys.argv[1]) if len(sys.argv) > 1 else 12.0
exp = get_experiment("g1-walk")
pol = exp["policy"]
scene_dir = exp["scene_path"].parent

model = mujoco.MjModel.from_xml_path(str(exp["scene_path"]))
data = mujoco.MjData(model)
key = model.keyframe("knees_bent")
qj, vj = pol["qpos_joint_start"], pol["qvel_joint_start"]
default_pose = np.asarray(key.qpos[qj:], np.float64)
gy_a = int(model.sensor(pol["sensors"]["gyro"]).adr[0])
lv_a = int(model.sensor(pol["sensors"]["local_linvel"]).adr[0])
imu_site = int(model.site(pol["imu_site"]).id)
cmd = np.asarray(pol["command"], np.float64)
g_down = np.array([0, 0, -1.0])
ACT = pol["act_dim"]
ctrl_dt, n_sub = pol["ctrl_dt"], pol["n_substeps"]
gait_freq = pol["gait"].get("gait_freq", 1.375)
phase_dt = 2 * np.pi * ctrl_dt * gait_freq
print(f"== g1-walk scene: nq={model.nq} nu={model.nu} nv={model.nv} | gyro={gy_a} linvel={lv_a} "
      f"imu_site={imu_site} | n_sub={n_sub} phase_dt={phase_dt:.4f}")


def build_obs(d, last_act, phase):
    gyro = d.sensordata[gy_a:gy_a + 3]
    linvel = d.sensordata[lv_a:lv_a + 3]
    gravity = d.site_xmat[imu_site].reshape(3, 3).T @ g_down
    jang = d.qpos[qj:] - default_pose
    jvel = d.qvel[vj:]
    pcs = np.array([np.cos(phase[0]), np.cos(phase[1]), np.sin(phase[0]), np.sin(phase[1])])
    return np.concatenate([linvel, gyro, gravity, cmd, jang, jvel, last_act, pcs]).astype(np.float32)


sess = ort.InferenceSession(str(scene_dir / pol["onnx"]), providers=["CPUExecutionProvider"])
def infer(obs):
    return sess.run(None, {"obs": obs[None].astype(np.float32)})[0][0]

# --- PARITY 1 (obs 조립 순서): golden obs == concat(슬롯, 순서대로) ---
golden = json.loads((scene_dir / pol["golden"]).read_text(encoding="utf-8"))["samples"]
asm_err = 0.0
for s in golden:
    sl = s["slots"]
    assembled = np.concatenate([
        sl["local_linvel"], sl["gyro"], sl["gravity"], s["command"],
        sl["joint_angles_minus_default"], sl["joint_vel"], s["last_act"],
        sl["phase_cos_sin"]]).astype(np.float32)
    asm_err = max(asm_err, float(np.max(np.abs(assembled - np.asarray(s["obs"], np.float32)))))
print(f"[parity:layout] obs == concat(slots): max err = {asm_err:.2e}")
assert asm_err < 1e-6, f"OBS LAYOUT MISMATCH {asm_err}"

# --- closed-loop rollout (+ PARITY 2: 번들 씬 == 학습 씬) ---
mujoco.mj_resetData(model, data)
data.qpos[:] = key.qpos
data.ctrl[:] = default_pose
mujoco.mj_forward(model, data)
phase = np.array([0.0, np.pi])
T = int(SECONDS / ctrl_dt)
last_act = np.zeros(ACT, np.float32)
qpos_frames, obs_seq = [], []
fell = -1
for t in range(T):
    obs = build_obs(data, last_act, phase)
    obs_seq.append(obs.copy())
    act = infer(obs)
    last_act = act
    data.ctrl[:] = default_pose + act * pol["action_scale"]
    for _ in range(n_sub):
        mujoco.mj_step(model, data)
    phase = np.fmod(phase + phase_dt + np.pi, 2 * np.pi) - np.pi
    qpos_frames.append([float(x) for x in data.qpos])
    up_z = -float((data.site_xmat[imu_site].reshape(3, 3).T @ g_down)[2])
    if up_z < 0 and fell < 0:
        fell = t
forward = qpos_frames[-1][0] - qpos_frames[0][0]
walked = (fell if fell >= 0 else T) * ctrl_dt

scene_err = max(float(np.max(np.abs(obs_seq[i] - np.asarray(golden[i]["obs"], np.float32))))
                for i in range(len(golden)))
print(f"[parity:scene] bundled rollout first {len(golden)} obs vs training golden: max err = {scene_err:.2e}")
assert scene_err < 1e-3, f"SCENE PARITY FAIL {scene_err} — bundled scene != training scene"
print(f"[rollout] fell={'never' if fell < 0 else f'{fell*ctrl_dt:.1f}s'} | "
      f"upright={walked:.1f}s | forward={forward:.2f}m | frames={len(qpos_frames)}")

exp["trajectory_path"].write_text(
    json.dumps({"fps": round(1 / ctrl_dt), "qpos": qpos_frames}), encoding="utf-8")
print(f"[traj] wrote {exp['trajectory_path'].name}: {len(qpos_frames)} frames @ {round(1/ctrl_dt)}fps")

reg = json.loads(REGISTRY.read_text(encoding="utf-8"))
reg["experiments"][exp["name"]]["policy"]["indices"] = {
    "gyro_adr": gy_a, "local_linvel_adr": lv_a, "imu_site_id": imu_site,
    "nq": int(model.nq), "nu": int(model.nu), "nv": int(model.nv),
    "default_pose": [float(x) for x in default_pose],
}
REGISTRY.write_text(json.dumps(reg, indent=2, ensure_ascii=False), encoding="utf-8")
print("[emit] wrote policy.indices into experiments.json")
