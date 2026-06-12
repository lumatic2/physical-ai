"""Generate a scripted SO-100 pick-and-place trajectory -> pick_trajectory.json.

Replay-first (ADR 0004 Decision §2): NOT a learned policy. The arm is driven by Cartesian
waypoints solved with a tiny damped-least-squares Jacobian IK (real mj_step servo motion).
The cube being picked is carried KINEMATICALLY — pinned upright to the midpoint of the
finger TIPS — while the gripper actually CLOSES its fingers onto it (the jaw servo drives
shut until the finger geoms contact the pinned cube, so the fingers visibly grip the cube
faces: no gap, no pass-through, and the cube moves coupled with the hand). On release the
cube is frozen at its exact tower pose. NOTE: this is visual coupling, not causal physics —
this 5-DOF SO-100 cannot hold a top-down grasp orientation through a lift (verified: top-down
is unreachable above table height), so a fully physical pick-lift-stack isn't achievable with
this arm; the kinematic carry reproduces the look robustly. Full qpos (arm 6 + 3 free-joint
blocks * 7 = 27) is recorded each frame and replayed kinematically (qpos + mj_forward) on
desktop and web, so mp4 == web. (Interactive mode in the web app runs full physics — drag the
blocks and they collide/fall for real.)

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
GRASP_LOCAL = np.array([-0.009, -0.102, 0.0])  # grasp point = midpoint of the finger TIPS (distal pads)
# The cube is carried at the fingertips; JAW_CLOSE shuts them to ~the cube width (36mm) so the tips
# visually pinch the cube faces (carry is kinematic, but the fingers really close onto it — no gap,
# no penetration), JAW_OPEN clears the cube on approach/release.
JAW_OPEN, JAW_CLOSE = 0.6, 0.15

home_arm = model.key_qpos[0][:6].copy()        # 0 -1.57 1.57 1.57 -1.57 0

# block qpos addresses (3 pos + 4 quat each)
BLOCK_QADR = {
    "a": model.jnt_qposadr[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, "block_a_free")],
    "b": model.jnt_qposadr[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, "block_b_free")],
    "c": model.jnt_qposadr[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, "block_c_free")],
}
BLOCK_DADR = {k: model.jnt_dofadr[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, f"block_{k}_free")] for k in "abc"}

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
        (bc,    JAW_CLOSE, ("grasp", k), 0.5, 0.5),        # 3 close the fingers onto the cube (settle)
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

# Kinematic block control: every block is in exactly one state each frame —
#   rest    -> its upright start pose
#   carried -> pinned upright to the grasp point (centred between the fingers)
#   placed  -> frozen at its exact tower pose
# This is what makes playback clean (no tilt, no snap, no inter-penetration).
REST = {k: data.qpos[BLOCK_QADR[k]:BLOCK_QADR[k] + 7].copy() for k in "abc"}
placed = {}                                                # k -> frozen 7-vec tower pose
carrying = [None]                                          # block id currently held (or None)


def apply_block_kinematics():
    gp = grasp_point(data)
    for k in "abc":
        qa, da = BLOCK_QADR[k], BLOCK_DADR[k]
        if carrying[0] == k:
            pose = np.array([gp[0], gp[1], gp[2], 1.0, 0.0, 0.0, 0.0])   # upright in gripper
        elif k in placed:
            pose = placed[k]
        else:
            pose = REST[k]
        data.qpos[qa:qa + 7] = pose
        data.qvel[da:da + 6] = 0.0


def step_once():
    mujoco.mj_step(model, data)
    apply_block_kinematics()


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
    # state transition AFTER reaching the pose (grasp = start carrying; release = freeze on stack)
    if weld is not None:
        kind, k = weld
        if kind == "grasp":
            carrying[0] = k
        else:
            carrying[0] = None
            placed[k] = np.array([PAD[0], PAD[1], STACK_Z[k], 1.0, 0.0, 0.0, 0.0])
        apply_block_kinematics()
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
