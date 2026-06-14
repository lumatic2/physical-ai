"""Decimate every mesh in a bundled scene's assets dir to fit the web transfer budget.
Loads each .obj/.stl, welds vertices, simplifies to a target face count, and writes back to
the SAME filename + extension (so the scene XML mesh refs need no edits). Meshes already
under the target pass through untouched. OBJ stays ASCII, STL stays binary.

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

before_t = after_t = 0
for fn in sorted(os.listdir(DIR)):
    ext = os.path.splitext(fn)[1].lower()
    if ext not in (".obj", ".stl"):
        continue
    p = os.path.join(DIR, fn)
    before = os.path.getsize(p)
    before_t += before
    m = trimesh.load(p, process=True, force="mesh")
    nf = len(m.faces)
    if nf > TARGET:
        vo, fo = fast_simplification.simplify(m.vertices, m.faces, target_count=max(MINF, TARGET))
        m = trimesh.Trimesh(vertices=vo, faces=fo, process=False)
    # Always re-export through trimesh: mujoco-js (wasm 0.0.7) fails to load some original
    # Meshlab-authored .obj files; trimesh's normalized output loads cleanly. So every mesh is
    # rewritten even when not decimated.
    m.export(p, file_type=ext[1:])
    after = os.path.getsize(p)
    after_t += after
    print(f"{fn:34s} {nf:>7d}f -> {len(m.faces):>6d}f   {before/1e6:5.2f} -> {after/1e6:5.2f} MB")
print(f"TOTAL {before_t/1e6:.1f} -> {after_t/1e6:.1f} MB")
