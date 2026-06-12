"""Offscreen render of the SO-100 twin doing a joint sweep -> mp4.
No GUI window (uses mujoco.Renderer offscreen). Works on Windows native GL.
Run after setup.sh:  python render_twin.py [out.mp4]"""
import sys
from pathlib import Path
import numpy as np
import mujoco
import imageio.v2 as imageio

HERE = Path(__file__).resolve().parent
XML = HERE / "vendor" / "mujoco_menagerie" / "trs_so_arm100" / "scene_twin.xml"
OUT = sys.argv[1] if len(sys.argv) > 1 else str(HERE / "media" / "so100_twin.mp4")
W, H, FPS, DUR = 1280, 960, 30, 6.0

model = mujoco.MjModel.from_xml_path(str(XML))
data = mujoco.MjData(model)
renderer = mujoco.Renderer(model, height=H, width=W)
print(f"== Renderer OK ({W}x{H})")

lo = model.actuator_ctrlrange[:, 0].copy()
hi = model.actuator_ctrlrange[:, 1].copy()
mid = (lo + hi) / 2.0
amp = (hi - lo) / 2.0 * 0.7  # stay inside joint limits

cam = mujoco.MjvCamera()
mujoco.mjv_defaultFreeCamera(model, cam)
cam.lookat[:] = [0.08, -0.05, 0.16]
cam.distance = 0.95
cam.azimuth = 135
cam.elevation = -18

steps_per_frame = max(1, int(round((1.0 / FPS) / model.opt.timestep)))
frames = []
for f in range(int(FPS * DUR)):
    t = f / FPS
    for j in range(model.nu):
        data.ctrl[j] = mid[j] + amp[j] * np.sin(2 * np.pi * 0.25 * t + j * 0.7)
    for _ in range(steps_per_frame):
        mujoco.mj_step(model, data)
    renderer.update_scene(data, camera=cam)
    frames.append(renderer.render())

Path(OUT).parent.mkdir(parents=True, exist_ok=True)
imageio.mimsave(OUT, frames, fps=FPS, quality=8)
print(f"== wrote {OUT}: {len(frames)} frames @ {FPS}fps ({DUR}s), {W}x{H}")
