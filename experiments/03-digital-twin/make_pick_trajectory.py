"""Generate a scripted SO-100 pick-and-place trajectory -> pick_trajectory.json.

Replay-first (ADR 0004 Decision §2): NOT a learned policy. The arm is driven by
Cartesian waypoints solved with a tiny damped-least-squares Jacobian IK, blocks are
carried by a weld constraint whose relpose is written at the grasp instant, and the
full qpos (arm 6 + 3 free-joint blocks * 7 = 27) is recorded each frame. render_twin.py
and the web both replay these frames kinematically (set qpos + mj_forward), so desktop
mp4 == web exactly and no contact/friction tuning leaks into playback.

Scenario: stack red -> green -> blue blocks onto the target pad (0.10, 0.0).
Run after setup.sh + smoke:  python make_pick_trajectory.py
"""
import json
from pathlib import Path
import numpy as np
import mujoco

HERE = Path(__file__).resolve().parent
XML = HERE / "vendor" / "mujoco_menagerie" / "trs_so_arm100" / "scene_twin.xml"
OUT = HERE / "pick_trajectory.json"
FPS = 30

model = mujoco.MjModel.from_xml_path(str(XML))
data = mujoco.MjData(model)

# --- ids -------------------------------------------------------------------
FJ = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "Fixed_Jaw")
JAW = 5                              # actuator/qpos index of the gripper joint
POS_DOFS = [0, 1, 2, 3, 4]          # arm dofs used for positioning (not the jaw)
GRASP_LOCAL = np.array([0.005, -0.085, 0.0])   # grasp point in Fixed_Jaw frame (between pads)
JAW_OPEN, JAW_CLOSE = 1.2, -0.1     # gripper ctrl targets (rad)

home_arm = model.key_qpos[0][:6].copy()        # 0 -1.57 1.57 1.57 -1.57 0

# block qpos addresses (3 pos + 4 quat each)
BLOCK_QADR = {
    "a": model.jnt_qposadr[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, "block_a_free")],
    "b": model.jnt_qposadr[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, "block_b_free")],
    "c": model.jnt_qposadr[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, "block_c_free")],
}
EQ = {k: mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_EQUALITY, f"grasp_{k}") for k in "abc"}

# pick order: red(a) bottom, green(b) middle, blue(c) top
PAD = np.array([0.14, -0.26])
STACK_Z = {"a": 0.018, "b": 0.054, "c": 0.090}     # block-center heights on the floor stack


def grasp_point(d):
    """World position of the grasp point rigidly attached to Fixed_Jaw."""
    return d.xpos[FJ] + d.xmat[FJ].reshape(3, 3) @ GRASP_LOCAL


def ik_arm(target, seed_qpos, iters=200, tol=1e-4, damp=0.03):
    """Damped least-squares IK: arm angles so grasp_point reaches target (3-DOF pos)."""
    dik = mujoco.MjData(model)
    dik.qpos[:] = seed_qpos
    q = dik.qpos[POS_DOFS].copy()
    jacp = np.zeros((3, model.nv))
    for _ in range(iters):
        dik.qpos[POS_DOFS] = q
        mujoco.mj_kinematics(model, dik)
        mujoco.mj_comPos(model, dik)
        gp = grasp_point(dik)
        err = target - gp
        if np.linalg.norm(err) < tol:
            break
        mujoco.mj_jac(model, dik, jacp, None, gp, FJ)
        J = jacp[:, POS_DOFS]
        dq = J.T @ np.linalg.solve(J @ J.T + (damp ** 2) * np.eye(3), err)
        q = np.clip(q + dq, model.jnt_range[POS_DOFS, 0], model.jnt_range[POS_DOFS, 1])
    return q, np.linalg.norm(err)


# --- build the waypoint plan ----------------------------------------------
# Each segment: (target xyz for grasp_point, jaw ctrl, weld key or None, seconds, hold s)
HOVER = 0.07
plan = []                                                   # (target, jaw, weld, secs, hold)
plan.append(("home", JAW_OPEN, None, 0.01, 0.5))           # start hold
for k in "abc":
    qa = BLOCK_QADR[k]
    bx, by = data.qpos[qa], data.qpos[qa + 1]               # block rest xy (fresh data)
    bc = np.array([bx, by, 0.018])                          # block center at rest
    above = bc + [0, 0, HOVER]
    sx, sy = PAD
    sc = np.array([sx, sy, STACK_Z[k]])                     # stack center target
    sabove = sc + [0, 0, HOVER]
    plan += [
        (above, JAW_OPEN, None, 0.5, 0.0),                 # 1 approach above block
        (bc,    JAW_OPEN, None, 0.4, 0.1),                 # 2 descend onto block
        (bc,    JAW_CLOSE, ("grasp", k), 0.25, 0.1),       # 3 close + weld on
        (above, JAW_CLOSE, None, 0.4, 0.0),                # 4 lift
        (sabove, JAW_CLOSE, None, 0.6, 0.0),               # 5 transport over pad
        (sc,    JAW_CLOSE, None, 0.4, 0.1),                # 6 lower onto stack
        (sc,    JAW_OPEN, ("release", k), 0.25, 0.15),     # 7 open + weld off (settle)
        (sabove, JAW_OPEN, None, 0.4, 0.0),                # 8 retract up
    ]
plan.append(("home", JAW_OPEN, None, 0.7, 0.6))            # return home + end hold

# --- execute & record ------------------------------------------------------
mujoco.mj_resetData(model, data)                           # blocks at body rest, arm at 0
data.qpos[:6] = home_arm
data.ctrl[:6] = home_arm
mujoco.mj_forward(model, data)

frames = []
steps_per_frame = max(1, int(round((1.0 / FPS) / model.opt.timestep)))
cur_ctrl = data.ctrl.copy()
home_pt = grasp_point(data).copy()
ik_residuals = []

# Blocks released onto the stack are frozen at their exact tower pose so the next
# pick's gripper/contact cannot knock them — playback is kinematic, so a clean
# scripted stack is the source of truth (weld only drives the carry).
placed = {}                                                # k -> 7-vec target qpos
BLOCK_DADR = {k: model.jnt_dofadr[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, f"block_{k}_free")] for k in "abc"}


def step_once():
    mujoco.mj_step(model, data)
    for k, pose in placed.items():
        qa = BLOCK_QADR[k]
        data.qpos[qa:qa + 7] = pose
        data.qvel[BLOCK_DADR[k]:BLOCK_DADR[k] + 6] = 0.0


def record():
    frames.append([round(float(x), 6) for x in data.qpos[:model.nq]])


def run_segment(target_pt, jaw, weld, secs, hold):
    global cur_ctrl
    nframes = max(1, int(round(secs * FPS)))
    start = cur_ctrl[POS_DOFS].copy()
    # solve IK once for the segment endpoint, then interpolate joint targets
    if target_pt is not None:
        qend, res = ik_arm(target_pt, data.qpos, )
        ik_residuals.append(res)
    else:
        qend = cur_ctrl[POS_DOFS].copy()
    for i in range(nframes):
        a = (i + 1) / nframes
        data.ctrl[POS_DOFS] = (1 - a) * start + a * qend
        if jaw is not None:
            data.ctrl[JAW] = jaw
        for _ in range(steps_per_frame):
            step_once()
        record()
    cur_ctrl = data.ctrl.copy()
    # weld toggle happens AFTER reaching the pose (grasp/release instant)
    if weld is not None:
        kind, k = weld
        eqid = EQ[k]
        if kind == "grasp":
            # capture current block pose relative to Fixed_Jaw -> weld relpose
            qa = BLOCK_QADR[k]
            bpos = data.qpos[qa:qa + 3].copy()
            bquat = data.qpos[qa + 3:qa + 7].copy()
            R = data.xmat[FJ].reshape(3, 3)
            rel_pos = R.T @ (bpos - data.xpos[FJ])
            fjq = np.zeros(4); mujoco.mju_mat2Quat(fjq, data.xmat[FJ])
            negfjq = np.zeros(4); mujoco.mju_negQuat(negfjq, fjq)
            rel_quat = np.zeros(4); mujoco.mju_mulQuat(rel_quat, negfjq, bquat)
            model.eq_data[eqid][0:3] = 0.0
            model.eq_data[eqid][3:6] = rel_pos
            model.eq_data[eqid][6:10] = rel_quat
            data.eq_active[eqid] = 1
        else:
            data.eq_active[eqid] = 0
            # freeze the just-released block at its exact tower pose (clean stack)
            placed[k] = np.array([PAD[0], PAD[1], STACK_Z[k], 1.0, 0.0, 0.0, 0.0])
            data.qpos[BLOCK_QADR[k]:BLOCK_QADR[k] + 7] = placed[k]
            data.qvel[BLOCK_DADR[k]:BLOCK_DADR[k] + 6] = 0.0
    # hold
    for _ in range(max(0, int(round(hold * FPS)))):
        for _ in range(steps_per_frame):
            step_once()
        record()


for target_pt, jaw, weld, secs, hold in plan:
    if isinstance(target_pt, str) and target_pt == "home":
        run_segment(home_pt, jaw, None, secs, hold)
    else:
        run_segment(np.asarray(target_pt, float), jaw, weld, secs, hold)

# --- report & write --------------------------------------------------------
print(f"== frames: {len(frames)}  ({len(frames)/FPS:.1f}s @ {FPS}fps)")
print(f"== IK residual max: {max(ik_residuals)*1000:.1f} mm  mean: {np.mean(ik_residuals)*1000:.1f} mm")
for k in "abc":
    qa = BLOCK_QADR[k]
    print(f"   block_{k} final center z = {data.qpos[qa+2]:.3f}  xy=({data.qpos[qa]:.3f},{data.qpos[qa+1]:.3f})  target z={STACK_Z[k]}")

OUT.write_text(json.dumps({
    "fps": FPS,
    "nq": int(model.nq),
    "arm_dofs": 6,
    "blocks": {k: int(BLOCK_QADR[k]) for k in "abc"},
    "scene": "trs_so_arm100/scene_twin.xml",
    "note": "scripted pick-and-place (replay-first, ADR 0004); qpos per frame",
    "qpos": frames,
}))
print(f"== wrote {OUT} ({OUT.stat().st_size//1024} KB)")
