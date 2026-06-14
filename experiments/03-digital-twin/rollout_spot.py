"""M11 (Spot) — closed-loop ONNX rollout on the bundled Spot policy scene + golden byte-parity.

rollout_g1.py 의 Spot 버전. 차이: obs 81-d = [gyro, gravity_projected(upvector sensor),
joints(12)-default, qpos_error_history(36, stateful), feet_pos(12, FL/FR/HL/HR framepos rel imu),
last_act, command]. gait clock 없음. motor_targets = clip(default + act*0.3, lowers, uppers).
번들 씬 obs == 학습 golden(verify_native) 검증 → spot_walk_trajectory.json 덤프 →
policy.indices(gyro/upvector/feet adrs, lowers/uppers, default_pose) experiments.json 박제.

  python rollout_spot.py [seconds]
"""
import sys, json
import numpy as np
import mujoco
import onnxruntime as ort
from harness import get_experiment, REGISTRY

SECONDS = float(sys.argv[1]) if len(sys.argv) > 1 else 12.0
exp = get_experiment("spot-walk")
pol = exp["policy"]
scene_dir = exp["scene_path"].parent

model = mujoco.MjModel.from_xml_path(str(exp["scene_path"]))
data = mujoco.MjData(model)
key = model.keyframe("home")
qj, vj = pol["qpos_joint_start"], pol["qvel_joint_start"]
default_pose = np.asarray(key.qpos[qj:], np.float64)
ACT = pol["act_dim"]
HL = pol["history_len"]
A = pol["action_scale"]
ctrl_dt, n_sub = pol["ctrl_dt"], pol["n_substeps"]

gy_a = int(model.sensor(pol["sensors"]["gyro"]).adr[0])
gv_a = int(model.sensor(pol["sensors"]["gravity"]).adr[0])
feet_a = [int(model.sensor(s).adr[0]) for s in pol["sensors"]["feet"]]   # [FL,FR,HL,HR] order
lowers = model.actuator_ctrlrange[:, 0].astype(np.float64)
uppers = model.actuator_ctrlrange[:, 1].astype(np.float64)
cmd = np.asarray(pol["command"], np.float64)
print(f"== spot-walk scene: nq={model.nq} nu={model.nu} nv={model.nv} | gyro={gy_a} upvector={gv_a} "
      f"feet={feet_a} | n_sub={n_sub}")


def build_obs(d, last_act, history):
    gyro = d.sensordata[gy_a:gy_a + 3]
    grav = d.sensordata[gv_a:gv_a + 3]
    jang = d.qpos[qj:] - default_pose
    feet = np.concatenate([d.sensordata[a:a + 3] for a in feet_a])   # 12, [FL,FR,HL,HR]
    return np.concatenate([gyro, grav, jang, history, feet, last_act, cmd]).astype(np.float32)


sess = ort.InferenceSession(str(scene_dir / pol["onnx"]), providers=["CPUExecutionProvider"])
def infer(obs):
    return sess.run(None, {"obs": obs[None].astype(np.float32)})[0][0]

# --- PARITY 1 (obs 조립 순서): golden obs == concat(슬롯, 순서대로) ---
golden = json.loads((scene_dir / pol["golden"]).read_text(encoding="utf-8"))["samples"]
asm_err = 0.0
for s in golden:
    sl = s["slots"]
    assembled = np.concatenate([
        sl["gyro"], sl["gravity_projected"], sl["joint_angles_minus_default"],
        sl["qpos_error_history"], sl["feet_pos"], s["last_act"], s["command"]]).astype(np.float32)
    asm_err = max(asm_err, float(np.max(np.abs(assembled - np.asarray(s["obs"], np.float32)))))
print(f"[parity:layout] obs == concat(slots): max err = {asm_err:.2e}")
assert asm_err < 1e-6, f"OBS LAYOUT MISMATCH {asm_err}"

# --- closed-loop rollout on BUNDLED scene (+ PARITY 2: 번들 == 학습 씬) ---
mujoco.mj_resetData(model, data)
data.qpos[:] = key.qpos
data.ctrl[:] = default_pose
mujoco.mj_forward(model, data)
T = int(SECONDS / ctrl_dt)
last_act = np.zeros(ACT, np.float32)
history = np.zeros(HL * 12, np.float32)
motor_targets = np.zeros(ACT, np.float64)
qpos_frames, obs_seq = [], []
fell = -1
for t in range(T):
    history = np.roll(history, 12)
    history[:12] = (data.qpos[qj:] - motor_targets).astype(np.float32)
    obs = build_obs(data, last_act, history)
    obs_seq.append(obs.copy())
    act = infer(obs)
    last_act = act
    motor_targets = np.clip(default_pose + act * A, lowers, uppers)
    data.ctrl[:] = motor_targets
    for _ in range(n_sub):
        mujoco.mj_step(model, data)
    qpos_frames.append([float(x) for x in data.qpos])
    if float(data.sensordata[gv_a + 2]) < 0 and fell < 0:   # upvector z flips -> tipped
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
    "gyro_adr": gy_a, "upvector_adr": gv_a, "feet_adrs": feet_a,
    "lowers": [float(x) for x in lowers], "uppers": [float(x) for x in uppers],
    "nq": int(model.nq), "nu": int(model.nu), "nv": int(model.nv),
    "default_pose": [float(x) for x in default_pose],
}
REGISTRY.write_text(json.dumps(reg, indent=2, ensure_ascii=False), encoding="utf-8")
print("[emit] wrote policy.indices into experiments.json")
