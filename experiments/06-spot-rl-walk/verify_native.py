"""S4 (Spot) — native mujoco-python closed-loop 검증 + golden_obs 박제.

spot_policy.onnx 를 onnxruntime 으로 돌려 obs(81)->action(12)->motor_targets->mj_step(xN).
obs 레이아웃: [gyro, upvector(=gravity_projected), qpos[7:]-default, qpos_error_history(36),
feet_pos(4×3, trunk-relative sensors), last_act, command]. 전부 센서/qpos 에서 재구성 —
phase clock·linear velocity 없음. qpos_error_history 는 stateful(3스텝 롤링: qpos[7:]-motor_targets).

성공: command 전진으로 >=10s 안 넘어지고 전진. golden_obs.json = 웹 빌더 byte-parity 기준.

실행: python verify_native.py <run_dir> [seconds] [vx]
"""
import os, sys, json, numpy as np, mujoco
import onnxruntime as ort
from mujoco_playground import registry

RUN = sys.argv[1] if len(sys.argv) > 1 else "/home/yusun/playground-go1/runs/spotflat"
SECONDS = float(sys.argv[2]) if len(sys.argv) > 2 else 12.0
VX = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
ENV = "SpotFlatTerrainJoystick"
ACTION_SCALE = 0.3
HISTORY_LEN = 3

env = registry.load(ENV, config_overrides={"impl": "jax"})
m = env.mj_model
d = mujoco.MjData(m)
key = m.keyframe("home")
d.qpos[:] = key.qpos
default_pose = key.qpos[7:].copy()
lowers = np.asarray(env._lowers, np.float32)
uppers = np.asarray(env._uppers, np.float32)
d.ctrl[:] = default_pose
mujoco.mj_forward(m, d)
ACT = m.nu

def sensor(name):
    s = m.sensor(name)
    a, dim = int(s.adr[0]), int(s.dim[0])
    return lambda: d.sensordata[a:a + dim].copy()
get_gyro = sensor("gyro")
get_grav = sensor("upvector")
feet_getters = [sensor(f"{f}_pos") for f in ("FL", "FR", "HL", "HR")]

sess = ort.InferenceSession(os.path.join(RUN, "spot_policy.onnx"), providers=["CPUExecutionProvider"])
cmd = np.array([VX, 0.0, 0.0], np.float32)
CTRL_DT = float(env.dt)
SIM_DT = float(m.opt.timestep)
n_sub = max(1, round(CTRL_DT / SIM_DT))
T = int(SECONDS / CTRL_DT)
print(f"ACT={ACT} CTRL_DT={CTRL_DT} SIM_DT={SIM_DT} n_sub={n_sub} T={T}", flush=True)

last_act = np.zeros(ACT, np.float32)
history = np.zeros(HISTORY_LEN * 12, np.float32)
motor_targets = default_pose.astype(np.float32).copy()  # env reset: info["motor_targets"]=0; first obs rolls qpos-0
motor_targets[:] = 0.0
qpos_traj, golden = [], []
fell_at = -1
for t in range(T):
    # _get_obs (post-step) equivalent: roll history with (current joint angles - last motor_targets)
    history = np.roll(history, 12)
    history[:12] = (d.qpos[7:] - motor_targets).astype(np.float32)
    gyro = get_gyro(); gravity = get_grav()
    jang = (d.qpos[7:] - default_pose).astype(np.float32)
    feet = np.concatenate([g() for g in feet_getters]).astype(np.float32)  # 12
    obs = np.concatenate([gyro, gravity, jang, history, feet, last_act, cmd]).astype(np.float32)
    assert obs.shape == (81,), obs.shape
    act = sess.run(None, {"obs": obs[None]})[0][0]
    if t < 5:
        golden.append({
            "step": t, "qpos": d.qpos.tolist(), "command": cmd.tolist(),
            "last_act": last_act.tolist(), "motor_targets_prev": motor_targets.tolist(),
            "slots": {"gyro": gyro.tolist(), "gravity_projected": gravity.tolist(),
                      "joint_angles_minus_default": jang.tolist(),
                      "qpos_error_history": history.tolist(), "feet_pos": feet.tolist()},
            "obs": obs.tolist(), "action": act.tolist(),
        })
    last_act = act
    motor_targets = np.clip(default_pose + act * ACTION_SCALE, lowers, uppers).astype(np.float32)
    d.ctrl[:] = motor_targets
    for _ in range(n_sub):
        mujoco.mj_step(m, d)
    qpos_traj.append(d.qpos.copy())
    if float(gravity[2]) < 0 and fell_at < 0:   # upvector z flips negative -> tipped over
        fell_at = t

qpos_traj = np.array(qpos_traj)
np.save(os.path.join(RUN, "native_rollout.npy"), qpos_traj)
with open(os.path.join(RUN, "golden_obs.json"), "w", encoding="utf-8") as f:
    json.dump({"env": ENV, "action_scale": ACTION_SCALE, "history_len": HISTORY_LEN,
               "note": "웹 obs-builder는 같은 (qpos,sensors,last_act,motor_targets,command)에서 동일 obs(81) 재현 — byte-parity 기준",
               "samples": golden}, f, indent=2, ensure_ascii=False)

walked_steps = fell_at if fell_at >= 0 else T
walked_s = walked_steps * CTRL_DT
forward = float(qpos_traj[walked_steps - 1, 0] - qpos_traj[0, 0])
final_h = float(qpos_traj[walked_steps - 1, 2])
print(f"FELL_AT={'never' if fell_at < 0 else f'{fell_at*CTRL_DT:.1f}s'} | upright={walked_s:.1f}s | "
      f"forward={forward:.2f}m | avg_vx={forward/max(walked_s,1e-6):.2f}m/s | final_h={final_h:.3f}", flush=True)
PASS = (fell_at < 0 or fell_at * CTRL_DT >= 10.0) and forward > 0.3
print("S4", "PASS" if PASS else "FAIL", flush=True)

try:
    os.environ.setdefault("MUJOCO_GL", "egl")
    import imageio.v2 as imageio
    ren = mujoco.Renderer(m, height=480, width=640)
    frames, d2 = [], mujoco.MjData(m)
    for i in range(0, len(qpos_traj), 2):
        d2.qpos[:] = qpos_traj[i]
        mujoco.mj_forward(m, d2)
        ren.update_scene(d2, camera=-1)
        frames.append(ren.render())
    imageio.mimsave(os.path.join(RUN, "native_rollout.mp4"), frames, fps=25)
    print("wrote native_rollout.mp4", len(frames), "frames", flush=True)
except Exception as e:
    print("mp4 skipped:", type(e).__name__, str(e)[:120], flush=True)
