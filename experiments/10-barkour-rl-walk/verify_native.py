"""Native mujoco-python closed-loop verification for Barkour.

Usage:
  python verify_native.py <run_dir> [seconds] [vx]
"""
import json
import os
import sys

import mujoco
import numpy as np
import onnxruntime as ort
from mujoco_playground import registry


RUN = sys.argv[1] if len(sys.argv) > 1 else "/home/<user>/playground-go1/runs/barkour"
SECONDS = float(sys.argv[2]) if len(sys.argv) > 2 else 12.0
VX = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
ENV = "BarkourJoystick"
OBS_DIM = 465
ACT_DIM = 12
CURRENT_DIM = 31

env = registry.load(ENV, config_overrides={"impl": "jax"})
m = env.mj_model
d = mujoco.MjData(m)
key = m.keyframe("home")
d.qpos[:] = key.qpos
default_pose = key.qpos[7:].copy()
d.ctrl[:] = default_pose
mujoco.mj_forward(m, d)

sess = ort.InferenceSession(
    os.path.join(RUN, "barkour_policy.onnx"),
    providers=["CPUExecutionProvider"],
)

cmd = np.array([VX, 0.0, 0.0], np.float32)
CTRL_DT = 0.02
n_sub = max(1, round(CTRL_DT / m.opt.timestep))
T = int(SECONDS / CTRL_DT)
last_act = np.zeros(ACT_DIM, np.float32)
history = np.zeros(OBS_DIM, np.float32)
qpos_traj = []
golden = []
fell_at = -1
lowers = np.array([-0.7, -1.0, 0.05] * 4, np.float32)
uppers = np.array([0.52, 2.1, 2.1] * 4, np.float32)


def sensor(name):
    sid = m.sensor(name).id
    adr = m.sensor_adr[sid]
    dim = m.sensor_dim[sid]
    return d.sensordata[adr : adr + dim].copy()


for t in range(T):
    yaw_rate_z_scaled = np.array([sensor("gyro")[-1] * 0.25], np.float32)
    upvector = sensor("upvector").astype(np.float32)
    scaled_cmd = (cmd * np.array([2.0, 2.0, 0.25], np.float32)).astype(np.float32)
    joint_delta = (d.qpos[7:] - default_pose).astype(np.float32)
    current = np.concatenate(
        [yaw_rate_z_scaled, upvector, scaled_cmd, joint_delta, last_act]
    ).astype(np.float32)
    current = np.clip(current, -100.0, 100.0)
    history = np.roll(history, CURRENT_DIM)
    history[:CURRENT_DIM] = current
    obs = history.copy()
    act = sess.run(None, {"obs": obs[None]})[0][0].astype(np.float32)

    if t < 5:
        golden.append(
            {
                "step": t,
                "qpos": d.qpos.tolist(),
                "qvel": d.qvel.tolist(),
                "last_act": last_act.tolist(),
                "command": cmd.tolist(),
                "slots": {
                    "yaw_rate_z_scaled": yaw_rate_z_scaled.tolist(),
                    "upvector": upvector.tolist(),
                    "command_scaled": scaled_cmd.tolist(),
                    "joint_angles_minus_default": joint_delta.tolist(),
                    "last_act": last_act.tolist(),
                },
                "obs465": obs.tolist(),
                "action": act.tolist(),
            }
        )

    last_act = act
    d.ctrl[:] = np.clip(default_pose + act * 0.3, lowers, uppers)
    for _ in range(n_sub):
        mujoco.mj_step(m, d)
    qpos_traj.append(d.qpos.copy())
    if upvector[-1] < 0 and fell_at < 0:
        fell_at = t

qpos_traj = np.array(qpos_traj)
np.save(os.path.join(RUN, "native_rollout.npy"), qpos_traj)
with open(os.path.join(RUN, "golden_obs.json"), "w", encoding="utf-8") as f:
    json.dump(
        {
            "env": ENV,
            "note": "Browser obs builder must reproduce obs465 for the same qpos/qvel/last_act/command/history state.",
            "samples": golden,
        },
        f,
        indent=2,
    )

walked_steps = fell_at if fell_at >= 0 else T
walked_s = walked_steps * CTRL_DT
x0, xT = qpos_traj[0, 0], qpos_traj[walked_steps - 1, 0]
forward = float(xT - x0)
avg_vx = forward / max(walked_s, 1e-6)
final_h = float(qpos_traj[walked_steps - 1, 2])
print(f"n_substeps={n_sub} sim_dt={m.opt.timestep} T={T} steps ({SECONDS}s) cmd_vx={VX}")
print(
    f"FELL_AT={'never' if fell_at < 0 else f'{fell_at * CTRL_DT:.1f}s'} | "
    f"upright={walked_s:.1f}s | forward={forward:.2f}m | avg_vx={avg_vx:.2f}m/s | final_h={final_h:.3f}"
)
passed = (fell_at < 0 or fell_at * CTRL_DT >= 10.0) and forward > 0.3
print("S4", "PASS" if passed else "FAIL")

try:
    os.environ.setdefault("MUJOCO_GL", "egl")
    import imageio.v2 as imageio

    ren = mujoco.Renderer(m, height=480, width=640)
    frames = []
    d2 = mujoco.MjData(m)
    for i in range(0, len(qpos_traj), 2):
        d2.qpos[:] = qpos_traj[i]
        mujoco.mj_forward(m, d2)
        camera = "track" if any(
            mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_CAMERA, c) == "track"
            for c in range(m.ncam)
        ) else -1
        ren.update_scene(d2, camera=camera)
        frames.append(ren.render())
    imageio.mimsave(os.path.join(RUN, "native_rollout.mp4"), frames, fps=25)
    print("wrote native_rollout.mp4", len(frames), "frames")
except Exception as e:
    print("mp4 skipped:", type(e).__name__, str(e)[:120])
