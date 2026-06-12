"""Offscreen render of the SO-100 twin replaying the scripted pick-and-place -> mp4.
Kinematic playback of pick_trajectory.json (set qpos + mj_forward per frame) so the
mp4 matches the web replay exactly. No GUI window (mujoco.Renderer offscreen). Windows
native GL. Run after make_pick_trajectory.py:  python render_twin.py [out.mp4]"""
import sys
import json
from pathlib import Path
import numpy as np
import mujoco
import imageio.v2 as imageio

HERE = Path(__file__).resolve().parent
XML = HERE / "vendor" / "mujoco_menagerie" / "trs_so_arm100" / "scene_twin.xml"
TRAJ = HERE / "pick_trajectory.json"
OUT = sys.argv[1] if len(sys.argv) > 1 else str(HERE / "media" / "so100_twin.mp4")
W, H = 1280, 960

model = mujoco.MjModel.from_xml_path(str(XML))
data = mujoco.MjData(model)
renderer = mujoco.Renderer(model, height=H, width=W)
print(f"== Renderer OK ({W}x{H})")

traj = json.loads(TRAJ.read_text())
qpos = np.asarray(traj["qpos"], dtype=float)
FPS = traj["fps"]
print(f"== trajectory: {len(qpos)} frames @ {FPS}fps ({len(qpos)/FPS:.1f}s)")

cam = mujoco.MjvCamera()
mujoco.mjv_defaultFreeCamera(model, cam)
cam.lookat[:] = [0.12, -0.18, 0.08]
cam.distance = 0.85
cam.azimuth = 150
cam.elevation = -20

frames = []
for q in qpos:
    data.qpos[:model.nq] = q
    mujoco.mj_forward(model, data)
    renderer.update_scene(data, camera=cam)
    frames.append(renderer.render())

Path(OUT).parent.mkdir(parents=True, exist_ok=True)
imageio.mimsave(OUT, frames, fps=FPS, quality=8)
print(f"== wrote {OUT}: {len(frames)} frames @ {FPS}fps ({len(frames)/FPS:.1f}s), {W}x{H}")
