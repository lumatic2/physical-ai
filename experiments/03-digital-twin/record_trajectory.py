"""Generic physics-trajectory recorder — robot-agnostic, no IK/task knowledge.

Loads any experiment's scene, runs the simulator forward from its initial (keyframe 0
if present) state, and dumps qpos per frame in the same schema the scripted generators
produce ({fps, qpos}). This is the harness's proof of generality: a new embodiment can
get a replayable trajectory with zero bespoke code (settle / drop / free dynamics).
Bespoke tasks (e.g. pick-and-place) still use their own generator (make_pick_trajectory.py).

  python record_trajectory.py [experiment] [seconds]
"""
import sys
import json
import mujoco
from harness import get_experiment

exp = get_experiment(sys.argv[1] if len(sys.argv) > 1 else None)
seconds = float(sys.argv[2]) if len(sys.argv) > 2 else 3.0

model = mujoco.MjModel.from_xml_path(str(exp["scene_path"]))
data = mujoco.MjData(model)
if model.nkey > 0:
    mujoco.mj_resetDataKeyframe(model, data, 0)
mujoco.mj_forward(model, data)

FPS = 30
steps_per_frame = max(1, round((1.0 / FPS) / model.opt.timestep))
nframes = int(seconds * FPS)
print(f"== recording '{exp['name']}': {nframes} frames @ {FPS}fps "
      f"({steps_per_frame} steps/frame, dt={model.opt.timestep})")

qpos = []
for _ in range(nframes):
    for _ in range(steps_per_frame):
        mujoco.mj_step(model, data)
    qpos.append(data.qpos[:model.nq].tolist())

out = exp["trajectory_path"]
out.write_text(json.dumps({"fps": FPS, "qpos": qpos}))
print(f"== wrote {out}: {len(qpos)} frames, nq={model.nq}")
