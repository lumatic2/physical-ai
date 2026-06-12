"""SO-100 (trs_so_arm100) MuJoCo load smoke — fast headless gate, no GL/render.
Verifies the model loads, FK resolves, and actuation moves the arm.
Run after setup.sh. Exit 0 = PASS."""
import sys
from pathlib import Path
import numpy as np
import mujoco

HERE = Path(__file__).resolve().parent
XML = HERE / "vendor" / "mujoco_menagerie" / "trs_so_arm100" / "scene_twin.xml"

print(f"== loading {XML}")
model = mujoco.MjModel.from_xml_path(str(XML))
data = mujoco.MjData(model)
print(f"   OK  nq={model.nq} nv={model.nv} njnt={model.njnt} nu={model.nu} nbody={model.nbody}")

jnt = [mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, i) for i in range(model.njnt)]
print(f"   joints({model.njnt}): {jnt}")

ee = "Moving_Jaw"
eid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, ee)
mujoco.mj_forward(model, data)
home = data.xpos[eid].copy()
print(f"== FK home: '{ee}' xpos = {np.round(home, 4)}")

if model.nu > 0:
    data.ctrl[0] = 0.4
for _ in range(200):
    mujoco.mj_step(model, data)
moved = data.xpos[eid].copy()
delta = np.linalg.norm(moved - home)
print(f"== after 200 steps (ctrl[0]=0.4): xpos = {np.round(moved, 4)}  |delta|={delta:.4f}")

ok = model.nq == 6 and model.nu == 6 and delta > 1e-4
print("\nSMOKE", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
