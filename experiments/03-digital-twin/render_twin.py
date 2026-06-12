"""Offscreen render of a digital-twin experiment replaying its recorded trajectory -> mp4.
Kinematic playback of the experiment's trajectory (set qpos + mj_forward per frame) so the
mp4 matches the web replay exactly. No GUI window (mujoco.Renderer offscreen). Windows
native GL. Camera comes from the experiment config. Run after the trajectory exists:

  python render_twin.py [experiment] [out.mp4]
"""
import sys
import json
from pathlib import Path
import numpy as np
import mujoco
import imageio.v2 as imageio
from harness import get_experiment, HERE

args = sys.argv[1:]
out_arg = next((a for a in args if a.endswith(".mp4")), None)
exp_arg = next((a for a in args if not a.endswith(".mp4")), None)
exp = get_experiment(exp_arg)

XML = exp["scene_path"]
TRAJ = exp["trajectory_path"]
OUT = out_arg or str(HERE / exp.get("render_out", f"media/{exp['name']}.mp4"))
W, H = 1280, 960

model = mujoco.MjModel.from_xml_path(str(XML))
data = mujoco.MjData(model)
renderer = mujoco.Renderer(model, height=H, width=W)
print(f"== experiment '{exp['name']}' — Renderer OK ({W}x{H})")

traj = json.loads(Path(TRAJ).read_text())
qpos = np.asarray(traj["qpos"], dtype=float)
FPS = traj["fps"]
print(f"== trajectory: {len(qpos)} frames @ {FPS}fps ({len(qpos)/FPS:.1f}s)")

c = exp["camera"]
cam = mujoco.MjvCamera()
mujoco.mjv_defaultFreeCamera(model, cam)
cam.lookat[:] = c["lookat"]
cam.distance = c["distance"]
cam.azimuth = c["azimuth"]
cam.elevation = c["elevation"]

frames = []
for q in qpos:
    data.qpos[:model.nq] = q
    mujoco.mj_forward(model, data)
    renderer.update_scene(data, camera=cam)
    frames.append(renderer.render())

Path(OUT).parent.mkdir(parents=True, exist_ok=True)
imageio.mimsave(OUT, frames, fps=FPS, quality=8)
print(f"== wrote {OUT}: {len(frames)} frames @ {FPS}fps ({len(frames)/FPS:.1f}s), {W}x{H}")
