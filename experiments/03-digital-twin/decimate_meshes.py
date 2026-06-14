"""Decimate every mesh in a bundled scene's assets dir to fit the web transfer budget.
Loads each .obj/.stl, welds vertices, simplifies to a target face count, and writes back to
the SAME filename + extension (so the scene XML mesh refs need no edits). Meshes already
under the target pass through untouched. OBJ stays ASCII, STL stays binary.

WATERTIGHT GUARD (trap #1): fast_simplification collapses NON-watertight meshes — open shells
(e.g. the Franka panda visual meshes) shred into scattered fragments instead of decimating.
So we simplify ONLY watertight meshes. A non-watertight mesh over the target is KEPT at full
resolution (just re-exported for wasm-loader compat); if it is also over HARDCAP it can't be
shrunk safely and gets a WARN so the scene's web budget can be fixed by hand.

  python decimate_meshes.py <assets_dir> [target_faces=4000] [min_faces=400]

Run in the WSL venv with trimesh + fast_simplification.
"""
import sys
import os
import trimesh
import fast_simplification

DIR = sys.argv[1]
TARGET = int(sys.argv[2]) if len(sys.argv) > 2 else 4000
MINF = int(sys.argv[3]) if len(sys.argv) > 3 else 400
HARDCAP = 150_000  # non-watertight meshes above this are too big for the web bundle to ship as-is

before_t = after_t = warns = 0
for fn in sorted(os.listdir(DIR)):
    ext = os.path.splitext(fn)[1].lower()
    if ext not in (".obj", ".stl"):
        continue
    p = os.path.join(DIR, fn)
    before = os.path.getsize(p)
    before_t += before
    m = trimesh.load(p, process=True, force="mesh")
    nf = len(m.faces)
    watertight = m.is_watertight
    if nf > TARGET and watertight:
        vo, fo = fast_simplification.simplify(m.vertices, m.faces, target_count=max(MINF, TARGET))
        m = trimesh.Trimesh(vertices=vo, faces=fo, process=False)
        tag = "decimated"
    elif nf > TARGET and not watertight:
        # Guard: simplifying this would collapse it. Keep full geometry (re-exported below).
        tag = "KEPT non-watertight"
        if nf > HARDCAP:
            tag = f"WARN non-watertight {nf}f > {HARDCAP} cap — shrink by hand"
            warns += 1
    else:
        tag = "passthrough"
    # Always re-export through trimesh: mujoco-js (wasm 0.0.7) fails to load some original
    # Meshlab-authored .obj files; trimesh's normalized output loads cleanly. So every mesh is
    # rewritten even when not decimated.
    m.export(p, file_type=ext[1:])
    after = os.path.getsize(p)
    after_t += after
    print(f"{fn:34s} {nf:>7d}f -> {len(m.faces):>6d}f   {before/1e6:5.2f} -> {after/1e6:5.2f} MB   {tag}")
print(f"TOTAL {before_t/1e6:.1f} -> {after_t/1e6:.1f} MB" + (f"   ({warns} WARN)" if warns else ""))
