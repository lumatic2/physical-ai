"""Deploy this web/ app to Vercel via REST API (direct upload, no GitHub needed).
Token read from VERCEL_TOKEN env (never printed). Prints the deployment URL + state.
Vite app — build dist/ first, then upload dist plus runtime assets/JSON and headers.

Files are uploaded individually by SHA1 (POST /v2/files) first, then the deployment
references them by {file, sha, size}. This lifts the ~10MB single-POST body limit of the
old inline-base64 approach, so the asset gallery (multiple robot mesh sets) can grow.
Run:  python deploy_vercel.py"""
import hashlib, json, os, shutil, subprocess, sys, tempfile, time, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.abspath(__file__))
NAME = "physical-ai-so100-twin"
CUSTOM_DOMAIN = "robotics.askewly.com"
TOKEN = os.environ["VERCEL_TOKEN"]
API = "https://api.vercel.com"

# Single-source guard: mirror canonical data JSONs from 03/ root into web/ before build,
# so a forgotten sync can never ship a stale copy to production. See ../sync_web.py.
subprocess.run([sys.executable, os.path.join(os.path.dirname(ROOT), "sync_web.py")], check=True)
npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
subprocess.run([npm_cmd, "run", "build"], cwd=ROOT, check=True)

# Upload the Vite build output plus runtime files fetched by src/main.js at runtime.
# Do not upload source modules; production must serve dist/index.html and hashed bundles.
INCLUDE_EXT = {".html", ".js", ".css", ".json", ".xml", ".stl", ".obj", ".gltf", ".bin", ".png", ".onnx", ".woff2", ".ico"}
RUNTIME_DIRS = {"assets"}
RUNTIME_ROOT_FILES = {
    "experiments.json",
    "vercel.json",
    "barkour_walk_trajectory.json",
    "dummy_arm_trajectory.json",
    "g1_controlled_squat_trajectory.json",
    "g1_decoupled_wbc_squat_trajectory.json",
    "g1_rough_walk_trajectory.json",
    "g1_settle.json",
    "g1_squat_reference_trajectory.json",
    "g1_walk_trajectory.json",
    "go1_walk_trajectory.json",
    "humanoid_settle.json",
    "panda_sweep.json",
    "pick_trajectory.json",
    "shadow_hand_sweep.json",
    "spot_settle.json",
    "spot_walk_trajectory.json",
    "unitree_g1_elastic_stand_telemetry.json",
    "unitree_g1_elastic_stand_trajectory.json",
    "unitree_g1_headless_telemetry.json",
    "unitree_g1_headless_trajectory.json",
}


def req(url, data=None, headers=None, method="GET", timeout=120):
    r = urllib.request.Request(url, data=data, method=method,
                               headers={"Authorization": f"Bearer {TOKEN}", **(headers or {})})
    return urllib.request.urlopen(r, timeout=timeout)


with tempfile.TemporaryDirectory(prefix="physical-ai-vercel-") as deploy_root:
    shutil.copytree(os.path.join(ROOT, "dist"), deploy_root, dirs_exist_ok=True)
    with open(os.path.join(deploy_root, "package.json"), "w", encoding="utf-8") as f:
        json.dump({"private": True, "description": "prebuilt static Robotics Lab deploy"}, f)
    for name in RUNTIME_ROOT_FILES:
        src = os.path.join(ROOT, name)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(deploy_root, name))
    for name in RUNTIME_DIRS:
        src = os.path.join(ROOT, name)
        if os.path.isdir(src):
            shutil.copytree(src, os.path.join(deploy_root, name), dirs_exist_ok=True)

    # Collect files, compute SHA1, upload each (Vercel dedupes by digest — re-upload is harmless).
    files, total = [], 0
    for dirpath, dirnames, filenames in os.walk(deploy_root):
        for fn in filenames:
            if os.path.splitext(fn)[1].lower() not in INCLUDE_EXT:
                continue
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, deploy_root).replace("\\", "/")
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
        if rs == "READY":
            try:
                alias_body = json.dumps({"alias": CUSTOM_DOMAIN}).encode()
                alias_out = json.load(req(
                    f"{API}/v2/deployments/{dep_id}/aliases",
                    data=alias_body,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                    timeout=60,
                ))
                alias = alias_out.get("alias") or CUSTOM_DOMAIN
                print(f"custom alias: https://{alias}")
            except urllib.error.HTTPError as e:
                msg = e.read().decode()[:1000]
                if e.code == 409 and "not_modified" in msg:
                    print(f"custom alias: https://{CUSTOM_DOMAIN} (already associated)")
                else:
                    print(f"custom alias failed for {CUSTOM_DOMAIN}: HTTP {e.code} {msg}")
                    print("If this is a first-time domain, add it to the Vercel project Domains settings and set the subdomain CNAME as required.")
        for a in st.get("alias") or []:
            print(f"alias: https://{a}")
        sys.exit(0 if rs == "READY" else 2)
print("timed out"); sys.exit(3)
