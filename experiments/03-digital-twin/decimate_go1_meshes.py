"""Re-decimate the Go1 visual meshes for the web bundle (browser deploy size limit).

Why: the first pass (commit bd7824a) crushed all 5 meshes to a flat 6000 faces, which
shredded the trunk (112k->6k = 95% loss) into scattered fragments. The fix here:
  1) load each ORIGINAL mesh through trimesh, which WELDS duplicated STL vertices into a
     shared-vertex mesh — decimation needs shared edges to collapse cleanly (unwelded STL
     is why the first pass scattered into points),
  2) decimate to a PER-MESH face budget (trunk keeps the most detail), staying within the
     Vercel single-POST deploy budget (go1 meshes ~2.5MB, total bundle base64 < ~10MB).

Output overwrites web/assets/scenes/go1/assets/*.stl (shared by desktop rollout + web).

Run in the WSL venv that has trimesh + fast_simplification:
    cd ~/playground-go1 && .venv/bin/python /mnt/c/.../03-digital-twin/decimate_go1_meshes.py
"""
import os
import mujoco_playground
import trimesh
import fast_simplification

SRC = os.path.join(os.path.dirname(mujoco_playground.__file__),
                   "external_deps/mujoco_menagerie/unitree_go1/assets")
DST = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "web/assets/scenes/go1/assets")

# Per-mesh target face counts. trunk is the big detailed shell -> most budget; small leg
# parts need far less. Sum ~49k faces -> ~2.5MB total binary STL (84 + 50*faces each).
TARGETS = {
    "trunk.stl":        20000,
    "hip.stl":          10000,
    "calf.stl":          9000,
    "thigh.stl":         5000,
    "thigh_mirror.stl":  5000,
}

total = 0
for name, target in TARGETS.items():
    src = os.path.join(SRC, name)
    m = trimesh.load(src, process=True)  # process=True welds duplicate vertices
    v, f = m.vertices, m.faces
    target = min(target, len(f))         # never "decimate" upward
    vo, fo = fast_simplification.simplify(v, f, target_count=target)
    out = trimesh.Trimesh(vertices=vo, faces=fo, process=False)
    dst = os.path.join(DST, name)
    out.export(dst, file_type="stl")     # binary STL
    sz = os.path.getsize(dst)
    total += sz
    print(f"{name:18s} {len(f):>7d} -> {len(fo):>6d} faces   {sz/1e6:5.2f} MB")

print(f"{'TOTAL':18s} {'':>7s}    {'':>6s}        {total/1e6:5.2f} MB")
