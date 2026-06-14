"""Generic scripted-motion recorder: sweep every actuator sinusoidally across its ctrlrange
and record qpos per frame. Gives visible articulation for any actuated fixed-base model
(dexterous hands, arms) with zero bespoke IK — the universal qpos replay format the web reads.

Floating-base robots (quadruped/humanoid) will just flail without a balance controller — use
record_trajectory.py (physics settle) or a static keyframe pose for those instead.

  python record_ctrl_sweep.py <experiment> [seconds] [cycles]
"""
import sys
import json
import math
import mujoco
from harness import get_experiment

exp = get_experiment(sys.argv[1])
seconds = float(sys.argv[2]) if len(sys.argv) > 2 else 4.0
cycles = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0

model = mujoco.MjModel.from_xml_path(str(exp["scene_path"]))
data = mujoco.MjData(model)
if model.nkey > 0:
    mujoco.mj_resetDataKeyframe(model, data, 0)
mujoco.mj_forward(model, data)

# Target range per actuator; fall back to a small range for unlimited actuators.
lo = model.actuator_ctrlrange[:, 0].copy()
hi = model.actuator_ctrlrange[:, 1].copy()
unlimited = ~model.actuator_ctrllimited.astype(bool)
lo[unlimited] = -0.5
hi[unlimited] = 0.5

FPS = 30
spf = max(1, round((1.0 / FPS) / model.opt.timestep))
nframes = int(seconds * FPS)
qpos = []
for fr in range(nframes):
    phase = cycles * fr / nframes
    s = 0.5 - 0.5 * math.cos(2 * math.pi * phase)   # 0 -> 1 -> 0 each cycle
    data.ctrl[:] = lo + (hi - lo) * s
    for _ in range(spf):
        mujoco.mj_step(model, data)
    qpos.append(data.qpos[:model.nq].tolist())

out = exp["trajectory_path"]
out.write_text(json.dumps({"fps": FPS, "qpos": qpos}))
print(f"wrote {out}: {len(qpos)} frames nq={model.nq} nu={model.nu}")
