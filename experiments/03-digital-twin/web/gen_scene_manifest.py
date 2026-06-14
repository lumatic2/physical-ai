"""Generate assets/scenes/manifest.json — the list of every scene file the web loader must
write into the MuJoCo WASM virtual filesystem before compiling a scene. Replaces the
hand-maintained array in mujocoUtils.js so adding an embodiment is just "drop files + rerun
this". Run after copying/decimating any scene assets:  python gen_scene_manifest.py"""
import json
import os

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "scenes")
EXT = {".xml", ".stl", ".obj", ".png", ".skn"}

files = []
for dirpath, _, filenames in os.walk(ROOT):
    for fn in filenames:
        if os.path.splitext(fn)[1].lower() in EXT:
            rel = os.path.relpath(os.path.join(dirpath, fn), ROOT).replace("\\", "/")
            files.append(rel)
files.sort()

out = os.path.join(ROOT, "manifest.json")
with open(out, "w", encoding="utf-8") as f:
    json.dump(files, f, indent=0)
print(f"wrote {out}: {len(files)} files")
