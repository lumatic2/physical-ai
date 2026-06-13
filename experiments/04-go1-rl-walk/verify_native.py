"""S4 — native mujoco-python closed-loop 검증 (학습 sim이 아닌 C 엔진).

go1_policy.onnx 를 onnxruntime 으로 돌려 obs->action->ctrl->mj_step(×5 @50Hz).
obs 는 obs_spec.md 와 동일: [local_linvel, gyro, gravity, qpos[7:]-default, qvel[6:], last_act, command].
성공 기준: command 전진 방향으로 >=10s 안 넘어지고(upvector z>0) 전진.

실행: python verify_native.py <run_dir> [seconds] [vx]
산출: <run_dir>/native_rollout.npy (qpos 궤적), 가능하면 native_rollout.mp4, 콘솔 메트릭.
"""
import os, sys, numpy as np, mujoco
import onnxruntime as ort
from mujoco_playground import registry

RUN = sys.argv[1] if len(sys.argv) > 1 else "/home/yusun/playground-go1/runs/go1flat"
SECONDS = float(sys.argv[2]) if len(sys.argv) > 2 else 12.0
VX = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
ENV = "Go1JoystickFlatTerrain"

env = registry.load(ENV, config_overrides={"impl": "jax"})
m = env.mj_model                      # native MjModel (학습과 동일 자산)
d = mujoco.MjData(m)
key = m.keyframe("home")
d.qpos[:] = key.qpos
default_pose = key.qpos[7:].copy()
d.ctrl[:] = default_pose
mujoco.mj_forward(m, d)

def sadr(name):
    s = m.sensor(name)
    return int(s.adr[0]), int(s.dim[0])
gy_a, _ = sadr("gyro")
lv_a, _ = sadr("local_linvel")
# imu site (gravity = site_xmat.T @ [0,0,-1])
try:
    imu_site = m.site("imu").id
except KeyError:
    imu_site = next(i for i in range(m.nsite)
                    if "imu" in (mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_SITE, i) or ""))

sess = ort.InferenceSession(os.path.join(RUN, "go1_policy.onnx"),
                            providers=["CPUExecutionProvider"])
cmd = np.array([VX, 0.0, 0.0], np.float32)
CTRL_DT, SIM_DT = 0.02, m.opt.timestep
n_sub = max(1, round(CTRL_DT / SIM_DT))
T = int(SECONDS / CTRL_DT)

last_act = np.zeros(12, np.float32)
qpos_traj = []
golden = []          # Phase 3 웹 obs-builder 검증용 (입력→obs 48 슬롯 박제)
fell_at = -1
g_down = np.array([0, 0, -1.0])
for t in range(T):
    gyro = d.sensordata[gy_a:gy_a + 3]
    linvel = d.sensordata[lv_a:lv_a + 3]
    xmat = d.site_xmat[imu_site].reshape(3, 3)
    gravity = xmat.T @ g_down
    jang = d.qpos[7:] - default_pose
    jvel = d.qvel[6:]
    obs = np.concatenate([linvel, gyro, gravity, jang, jvel, last_act, cmd]).astype(np.float32)
    act = sess.run(None, {"obs": obs[None]})[0][0]
    if t < 5:        # golden fixture: 처음 5스텝의 (입력, 슬롯, obs, action)
        golden.append({
            "step": t,
            "qpos": d.qpos.tolist(), "qvel": d.qvel.tolist(),
            "last_act": last_act.tolist(), "command": cmd.tolist(),
            "slots": {"local_linvel": linvel.tolist(), "gyro": gyro.tolist(),
                      "gravity": gravity.tolist(), "joint_angles_minus_default": jang.tolist(),
                      "joint_vel": jvel.tolist()},
            "obs48": obs.tolist(), "action": act.tolist(),
        })
    last_act = act
    d.ctrl[:] = default_pose + act * 0.5
    for _ in range(n_sub):
        mujoco.mj_step(m, d)
    qpos_traj.append(d.qpos.copy())
    up_z = -float(gravity[2])          # upvector z = -projected_gravity_z
    if up_z < 0 and fell_at < 0:
        fell_at = t

qpos_traj = np.array(qpos_traj)
np.save(os.path.join(RUN, "native_rollout.npy"), qpos_traj)

import json
with open(os.path.join(RUN, "golden_obs.json"), "w") as f:
    json.dump({"env": ENV, "note": "Phase 3 웹 obs-builder는 같은 (qpos,qvel,last_act,command)에서 동일 obs48을 재현해야 함",
               "samples": golden}, f, indent=2)

walked_steps = fell_at if fell_at >= 0 else T
walked_s = walked_steps * CTRL_DT
x0, xT = qpos_traj[0, 0], qpos_traj[walked_steps - 1, 0]
forward = float(xT - x0)
avg_vx = forward / max(walked_s, 1e-6)
final_h = float(qpos_traj[walked_steps - 1, 2])
print(f"n_substeps={n_sub} sim_dt={SIM_DT} T={T} steps ({SECONDS}s) cmd_vx={VX}")
print(f"FELL_AT={'never' if fell_at < 0 else f'{fell_at*CTRL_DT:.1f}s'} | "
      f"upright={walked_s:.1f}s | forward={forward:.2f}m | avg_vx={avg_vx:.2f}m/s | final_h={final_h:.3f}")
PASS = (fell_at < 0 or fell_at * CTRL_DT >= 10.0) and forward > 0.3
print("S4", "PASS" if PASS else "FAIL")

# best-effort mp4
try:
    os.environ.setdefault("MUJOCO_GL", "egl")
    import imageio.v2 as imageio
    ren = mujoco.Renderer(m, height=480, width=640)
    frames = []
    d2 = mujoco.MjData(m)
    for i in range(0, len(qpos_traj), 2):   # ~25fps
        d2.qpos[:] = qpos_traj[i]
        mujoco.mj_forward(m, d2)
        ren.update_scene(d2, camera="track" if any(
            mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_CAMERA, c) == "track"
            for c in range(m.ncam)) else -1)
        frames.append(ren.render())
    imageio.mimsave(os.path.join(RUN, "native_rollout.mp4"), frames, fps=25)
    print("wrote native_rollout.mp4", len(frames), "frames")
except Exception as e:
    print("mp4 skipped:", type(e).__name__, str(e)[:120])
