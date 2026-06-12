"""Digital-twin MuJoCo load smoke — fast headless gate, no GL/render.
Verifies the experiment's scene loads, FK resolves on its end-effector body, and
actuation moves the model. Generic across embodiments (nq/nu derived from the model,
not hardcoded) — proves the harness, not just SO-100. Run after setup.sh. Exit 0 = PASS.

  python smoke_twin.py [experiment]
"""
import sys
from pathlib import Path
import numpy as np
import mujoco
from harness import get_experiment

exp = get_experiment(sys.argv[1] if len(sys.argv) > 1 else None)
XML = exp["scene_path"]

print(f"== experiment '{exp['name']}' — loading {XML}")
model = mujoco.MjModel.from_xml_path(str(XML))
data = mujoco.MjData(model)
print(f"   OK  nq={model.nq} nv={model.nv} njnt={model.njnt} nu={model.nu} nbody={model.nbody}")

jnt = [mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, i) for i in range(model.njnt)]
print(f"   joints({model.njnt}): {jnt}")

ee = exp["ee_body"]
eid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, ee)
mujoco.mj_forward(model, data)
home = data.xpos[eid].copy() if eid >= 0 else None
print(f"== FK home: '{ee}' (id={eid}) xpos = {np.round(home, 4) if eid >= 0 else 'NOT FOUND'}")

if model.nu > 0:
    data.ctrl[0] = 0.4
for _ in range(200):
    mujoco.mj_step(model, data)
moved = data.xpos[eid].copy() if eid >= 0 else None
delta = float(np.linalg.norm(moved - home)) if eid >= 0 else 0.0
print(f"== after 200 steps (ctrl[0]=0.4): xpos = {np.round(moved, 4) if eid >= 0 else 'n/a'}  |delta|={delta:.4f}")

# Generic gate: scene loaded, end-effector body resolved, and the model moved under
# actuation/dynamics. nq/nu are reported (derived from the model), not asserted to a
# fixed embodiment-specific value.
ok = eid >= 0 and model.nq > 0 and delta > 1e-4
print("\nSMOKE", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
