"""S4 (G1) — native mujoco-python closed-loop 검증.

g1_policy.onnx 를 onnxruntime 으로 돌려 obs->action->ctrl->mj_step(xN @ ctrl_dt).
obs 레이아웃(G1, 103-d): [local_linvel(pelvis), gyro(pelvis), gravity(imu_in_pelvis site),
command, qpos[7:]-default, qvel[6:], last_act, phase(=concat[cos,sin] of 2-vec gait clock)].
default_pose = keyframe("knees_bent").qpos[7:]. 성공: command 전진으로 >=10s 안 넘어지고 전진.

실행: python verify_native.py <run_dir> [seconds] [vx] [gait_freq]
산출: <run_dir>/native_rollout.npy, golden_obs.json, (best-effort) native_rollout.mp4
"""
import os, sys, json, numpy as np, mujoco
import onnxruntime as ort
from mujoco_playground import registry

RUN = sys.argv[1] if len(sys.argv) > 1 else "/home/yusun/playground-go1/runs/g1flat"
SECONDS = float(sys.argv[2]) if len(sys.argv) > 2 else 12.0
VX = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
GAIT_FREQ = float(sys.argv[4]) if len(sys.argv) > 4 else 1.375
ENV = "G1JoystickFlatTerrain"

env = registry.load(ENV, config_overrides={"impl": "jax"})
m = env.mj_model
d = mujoco.MjData(m)
key = m.keyframe("knees_bent")
d.qpos[:] = key.qpos
default_pose = key.qpos[7:].copy()
d.ctrl[:] = default_pose
mujoco.mj_forward(m, d)
ACT = m.nu

def sadr(name):
    s = m.sensor(name)
    return int(s.adr[0])
gy_a = sadr("gyro_pelvis")
lv_a = sadr("local_linvel_pelvis")
imu_site = m.site("imu_in_pelvis").id

sess = ort.InferenceSession(os.path.join(RUN, "g1_policy.onnx"), providers=["CPUExecutionProvider"])
cmd = np.array([VX, 0.0, 0.0], np.float32)
CTRL_DT = float(env.dt)
SIM_DT = float(m.opt.timestep)
n_sub = max(1, round(CTRL_DT / SIM_DT))
T = int(SECONDS / CTRL_DT)
phase = np.array([0.0, np.pi])
phase_dt = 2 * np.pi * CTRL_DT * GAIT_FREQ
print(f"ACT={ACT} CTRL_DT={CTRL_DT} SIM_DT={SIM_DT} n_sub={n_sub} T={T} phase_dt={phase_dt:.4f}", flush=True)

last_act = np.zeros(ACT, np.float32)
qpos_traj, golden = [], []
fell_at = -1
g_down = np.array([0, 0, -1.0])
for t in range(T):
    gyro = d.sensordata[gy_a:gy_a + 3]
    linvel = d.sensordata[lv_a:lv_a + 3]
    gravity = d.site_xmat[imu_site].reshape(3, 3).T @ g_down
    jang = d.qpos[7:] - default_pose
    jvel = d.qvel[6:]
    phase_obs = np.concatenate([np.cos(phase), np.sin(phase)])
    obs = np.concatenate([linvel, gyro, gravity, cmd, jang, jvel, last_act, phase_obs]).astype(np.float32)
    act = sess.run(None, {"obs": obs[None]})[0][0]
    if t < 5:
        golden.append({
            "step": t, "qpos": d.qpos.tolist(), "qvel": d.qvel.tolist(),
            "last_act": last_act.tolist(), "command": cmd.tolist(), "phase": phase.tolist(),
            "slots": {"local_linvel": linvel.tolist(), "gyro": gyro.tolist(),
                      "gravity": gravity.tolist(), "joint_angles_minus_default": jang.tolist(),
                      "joint_vel": jvel.tolist(), "phase_cos_sin": phase_obs.tolist()},
            "obs": obs.tolist(), "action": act.tolist(),
        })
    last_act = act
    d.ctrl[:] = default_pose + act * 0.5
    for _ in range(n_sub):
        mujoco.mj_step(m, d)
    phase = np.fmod(phase + phase_dt + np.pi, 2 * np.pi) - np.pi
    qpos_traj.append(d.qpos.copy())
    if -float(gravity[2]) < 0 and fell_at < 0:
        fell_at = t

qpos_traj = np.array(qpos_traj)
np.save(os.path.join(RUN, "native_rollout.npy"), qpos_traj)
with open(os.path.join(RUN, "golden_obs.json"), "w") as f:
    json.dump({"env": ENV, "gait_freq": GAIT_FREQ,
               "note": "웹 obs-builder는 같은 (qpos,qvel,last_act,command,phase)에서 동일 obs(103)를 재현해야 함",
               "samples": golden}, f, indent=2)

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
