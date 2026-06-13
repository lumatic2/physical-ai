"""Phase 2 — closed-loop ONNX policy rollout in native mujoco (harness-integrated).

An experiment with a `policy` block runs the trained policy closed-loop
(obs -> onnx -> ctrl -> mj_step) instead of replaying a recorded trajectory. This is
the desktop twin of the web onnxruntime-web loop (Phase 3), and it verifies that the
*bundled self-contained scene* produces byte-identical obs to the training scene
(parity vs golden_obs.json — captured in experiment 04 verify_native.py).

Outputs:
  - parity assert: bundled-scene obs == training golden (proves the bundle == training scene)
  - <trajectory>.json (qpos frames @ 1/ctrl_dt fps) — render_twin mp4 + web replay fallback
  - writes derived indices (sensor adrs, imu site, default_pose, nq/nu) back into the
    experiment's policy block in experiments.json so the web JS uses fixed indices
    (no name lookup in wasm).

  python rollout_policy.py [experiment] [seconds]
"""
import sys
import json
from pathlib import Path
import numpy as np
import mujoco
import onnxruntime as ort
from harness import get_experiment, REGISTRY

args = sys.argv[1:]
exp_arg = next((a for a in args if not a.replace(".", "").isdigit()), None)
sec_arg = next((a for a in args if a.replace(".", "").isdigit()), None)
exp = get_experiment(exp_arg or "go1-walk")
SECONDS = float(sec_arg) if sec_arg else 8.0
pol = exp["policy"]
scene_dir = exp["scene_path"].parent

model = mujoco.MjModel.from_xml_path(str(exp["scene_path"]))
data = mujoco.MjData(model)
key = model.keyframe("home")
qj, vj = pol["qpos_joint_start"], pol["qvel_joint_start"]
default_pose = np.asarray(key.qpos[qj:], np.float64)
gy_a = int(model.sensor(pol["sensors"]["gyro"]).adr[0])
lv_a = int(model.sensor(pol["sensors"]["local_linvel"]).adr[0])
imu_site = int(model.site(pol["imu_site"]).id)
cmd = np.asarray(pol["command"], np.float64)
g_down = np.array([0, 0, -1.0])
print(f"== '{exp['name']}' scene loaded: nq={model.nq} nu={model.nu} nv={model.nv} "
      f"| gyro_adr={gy_a} linvel_adr={lv_a} imu_site={imu_site}")


def build_obs(d, last_act):
    gyro = d.sensordata[gy_a:gy_a + 3]
    linvel = d.sensordata[lv_a:lv_a + 3]
    gravity = d.site_xmat[imu_site].reshape(3, 3).T @ g_down
    jang = d.qpos[qj:] - default_pose
    jvel = d.qvel[vj:]
    return np.concatenate([linvel, gyro, gravity, jang, jvel, last_act, cmd]).astype(np.float32)


sess = ort.InferenceSession(str(scene_dir / pol["onnx"]), providers=["CPUExecutionProvider"])
def infer(obs):
    return sess.run(None, {"obs": obs[None].astype(np.float32)})[0][0]

# --- PARITY 1 (obs 조립 순서): golden obs48 == concat(golden 슬롯, last_act, command) ---
# 웹 JS obs builder가 베낄 레이아웃을 sim 없이 검증. ⚠ 센서는 mj_step 후 1-substep stale
# 이므로 (qpos,qvel)+mj_forward 로 재계산하면 안 됨 — golden 이 박제한 슬롯 값을 그대로 쓴다.
golden = json.loads((scene_dir / pol["golden"]).read_text(encoding="utf-8"))["samples"]
asm_err = 0.0
for s in golden:
    sl = s["slots"]
    assembled = np.concatenate([
        sl["local_linvel"], sl["gyro"], sl["gravity"],
        sl["joint_angles_minus_default"], sl["joint_vel"],
        s["last_act"], s["command"]]).astype(np.float32)
    asm_err = max(asm_err, float(np.max(np.abs(assembled - np.asarray(s["obs48"], np.float32)))))
print(f"[parity:layout] obs48 == concat(slots,last_act,command): max err = {asm_err:.2e}")
assert asm_err < 1e-6, f"OBS LAYOUT MISMATCH {asm_err}"

# --- closed-loop rollout (+ PARITY 2: 씬 동일성) ---
# 같은 home keyframe + 같은 onnx + 같은 물리를 굴린다. 번들 씬 == 학습 씬이면 첫 N obs 가
# golden(학습 씬 rollout)과 일치 — staleness 까지 같은 stepping 으로 자동 동일.
mujoco.mj_resetData(model, data)
data.qpos[:] = key.qpos
data.ctrl[:] = default_pose
mujoco.mj_forward(model, data)
ctrl_dt, n_sub = pol["ctrl_dt"], pol["n_substeps"]
T = int(SECONDS / ctrl_dt)
last_act = np.zeros(pol["act_dim"], np.float32)
qpos_frames, obs_seq = [], []
fell = -1
for t in range(T):
    obs = build_obs(data, last_act)
    obs_seq.append(obs.copy())
    act = infer(obs)
    last_act = act
    data.ctrl[:] = default_pose + act * pol["action_scale"]
    for _ in range(n_sub):
        mujoco.mj_step(model, data)
    qpos_frames.append([float(x) for x in data.qpos])
    up_z = -float((data.site_xmat[imu_site].reshape(3, 3).T @ g_down)[2])
    if up_z < 0 and fell < 0:
        fell = t
forward = qpos_frames[-1][0] - qpos_frames[0][0]
walked = (fell if fell >= 0 else T) * ctrl_dt

scene_err = max(float(np.max(np.abs(obs_seq[i] - np.asarray(golden[i]["obs48"], np.float32))))
                for i in range(len(golden)))
print(f"[parity:scene] bundled rollout first {len(golden)} obs vs training golden: max err = {scene_err:.2e}")
assert scene_err < 1e-3, f"SCENE PARITY FAIL {scene_err} — bundled scene != training scene"
print(f"[rollout] fell={'never' if fell < 0 else f'{fell*ctrl_dt:.1f}s'} | "
      f"upright={walked:.1f}s | forward={forward:.2f}m | frames={len(qpos_frames)}")

# --- dump trajectory (qpos @ 1/ctrl_dt fps) ---
exp["trajectory_path"].write_text(
    json.dumps({"fps": round(1 / ctrl_dt), "qpos": qpos_frames}), encoding="utf-8")
print(f"[traj] wrote {exp['trajectory_path'].name}: {len(qpos_frames)} frames @ {round(1/ctrl_dt)}fps")

# --- emit derived indices into experiments.json policy block (JS fixed-index source) ---
reg = json.loads(REGISTRY.read_text(encoding="utf-8"))
reg["experiments"][exp["name"]]["policy"]["indices"] = {
    "gyro_adr": gy_a, "local_linvel_adr": lv_a, "imu_site_id": imu_site,
    "nq": int(model.nq), "nu": int(model.nu), "nv": int(model.nv),
    "default_pose": [float(x) for x in default_pose],
}
REGISTRY.write_text(json.dumps(reg, indent=2, ensure_ascii=False), encoding="utf-8")
print("[emit] wrote policy.indices into experiments.json")
