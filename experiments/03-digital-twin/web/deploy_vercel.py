"""Deploy this web/ app to Vercel via REST API (direct upload, no GitHub needed).
Token read from VERCEL_TOKEN env (never printed). Prints the deployment URL + state.
Pure static (deps via CDN) — Vercel just serves files + applies vercel.json headers.
Run:  python deploy_vercel.py"""
import base64, json, os, sys, time, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.abspath(__file__))
NAME = "physical-ai-so100-twin"
TOKEN = os.environ["VERCEL_TOKEN"]

# Only the files the hosted site needs (deps come from CDN, so no node_modules).
INCLUDE_EXT = {".html", ".js", ".json", ".xml", ".stl", ".png", ".onnx"}
EXCLUDE_DIRS = {"node_modules", "media", ".vercel"}
EXCLUDE_NAMES = {"serve_coi.py", "deploy_vercel.py", "README.md", "mujoco_wasm.patch", ".gitignore"}

files = []
for dirpath, dirnames, filenames in os.walk(ROOT):
    dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
    for fn in filenames:
        if fn in EXCLUDE_NAMES:
            continue
        if os.path.splitext(fn)[1].lower() not in INCLUDE_EXT:
            continue
        full = os.path.join(dirpath, fn)
        rel = os.path.relpath(full, ROOT).replace("\\", "/")
        with open(full, "rb") as f:
            files.append({"file": rel, "data": base64.b64encode(f.read()).decode(), "encoding": "base64"})

print(f"packaging {len(files)} files")
body = {"name": NAME, "files": files, "target": "production",
        "projectSettings": {"framework": None, "buildCommand": None, "outputDirectory": "."}}

req = urllib.request.Request(
    "https://api.vercel.com/v13/deployments?forceNew=1",
    data=json.dumps(body).encode(),
    headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
    method="POST")
try:
    out = json.load(urllib.request.urlopen(req, timeout=120))
except urllib.error.HTTPError as e:
    print("HTTP", e.code, e.read().decode()[:2000]); sys.exit(1)

dep_id, url = out.get("id"), out.get("url")
print(f"created: id={dep_id}  url=https://{url}  state={out.get('readyState')}")
for _ in range(60):
    time.sleep(5)
    r = urllib.request.Request(f"https://api.vercel.com/v13/deployments/{dep_id}",
                               headers={"Authorization": f"Bearer {TOKEN}"})
    st = json.load(urllib.request.urlopen(r, timeout=60))
    rs = st.get("readyState") or st.get("status")
    print(f"  state={rs}")
    if rs in ("READY", "ERROR", "CANCELED"):
        print(f"\nFINAL state={rs}\ndeployment: https://{url}")
        for a in st.get("alias") or []:
            print(f"alias: https://{a}")
        sys.exit(0 if rs == "READY" else 2)
print("timed out"); sys.exit(3)
