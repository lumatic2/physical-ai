"""Deploy this web/ app to Vercel via REST API (direct upload, no GitHub needed).
Token read from VERCEL_TOKEN env (never printed). Prints the deployment URL + state.
Pure static (deps via CDN) — Vercel just serves files + applies vercel.json headers.

Files are uploaded individually by SHA1 (POST /v2/files) first, then the deployment
references them by {file, sha, size}. This lifts the ~10MB single-POST body limit of the
old inline-base64 approach, so the asset gallery (multiple robot mesh sets) can grow.
Run:  python deploy_vercel.py"""
import hashlib, json, os, subprocess, sys, time, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.abspath(__file__))
NAME = "physical-ai-so100-twin"
TOKEN = os.environ["VERCEL_TOKEN"]
API = "https://api.vercel.com"

# Single-source guard: mirror canonical data JSONs from 03/ root into web/ before upload,
# so a forgotten sync can never ship a stale copy to production. See ../sync_web.py.
subprocess.run([sys.executable, os.path.join(os.path.dirname(ROOT), "sync_web.py")], check=True)

# Only the files the hosted site needs (deps come from CDN, so no node_modules).
INCLUDE_EXT = {".html", ".js", ".json", ".xml", ".stl", ".obj", ".png", ".onnx"}
EXCLUDE_DIRS = {"node_modules", "media", ".vercel", "qa"}
EXCLUDE_NAMES = {"serve_coi.py", "deploy_vercel.py", "README.md", "mujoco_wasm.patch", ".gitignore"}


def req(url, data=None, headers=None, method="GET", timeout=120):
    r = urllib.request.Request(url, data=data, method=method,
                               headers={"Authorization": f"Bearer {TOKEN}", **(headers or {})})
    return urllib.request.urlopen(r, timeout=timeout)


# Collect files, compute SHA1, upload each (Vercel dedupes by digest — re-upload is harmless).
files, total = [], 0
for dirpath, dirnames, filenames in os.walk(ROOT):
    dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
    for fn in filenames:
        if fn in EXCLUDE_NAMES or os.path.splitext(fn)[1].lower() not in INCLUDE_EXT:
            continue
        full = os.path.join(dirpath, fn)
        rel = os.path.relpath(full, ROOT).replace("\\", "/")
        with open(full, "rb") as f:
            data = f.read()
        sha = hashlib.sha1(data).hexdigest()
        files.append({"file": rel, "sha": sha, "size": len(data)})
        total += len(data)
        for attempt in range(3):
            try:
                req(f"{API}/v2/files", data=data, method="POST",
                    headers={"Content-Type": "application/octet-stream",
                             "x-vercel-digest": sha, "Content-Length": str(len(data))})
                break
            except urllib.error.HTTPError as e:
                if attempt == 2:
                    print("upload HTTP", e.code, rel, e.read().decode()[:500]); sys.exit(1)
                time.sleep(2)

print(f"uploaded {len(files)} files ({total/1e6:.2f} MB raw)")

body = {"name": NAME, "files": files, "target": "production",
        "projectSettings": {"framework": None, "buildCommand": None, "outputDirectory": "."}}
try:
    out = json.load(req(f"{API}/v13/deployments?forceNew=1", data=json.dumps(body).encode(),
                        headers={"Content-Type": "application/json"}, method="POST"))
except urllib.error.HTTPError as e:
    print("HTTP", e.code, e.read().decode()[:2000]); sys.exit(1)

dep_id, url = out.get("id"), out.get("url")
print(f"created: id={dep_id}  url=https://{url}  state={out.get('readyState')}")
for _ in range(60):
    time.sleep(5)
    st = json.load(req(f"{API}/v13/deployments/{dep_id}", timeout=60))
    rs = st.get("readyState") or st.get("status")
    print(f"  state={rs}")
    if rs in ("READY", "ERROR", "CANCELED"):
        print(f"\nFINAL state={rs}\ndeployment: https://{url}")
        for a in st.get("alias") or []:
            print(f"alias: https://{a}")
        sys.exit(0 if rs == "READY" else 2)
print("timed out"); sys.exit(3)
