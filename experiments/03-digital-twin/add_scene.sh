#!/usr/bin/env bash
# Unified "add a scene / refresh an embodiment" pipeline for the digital twin.
#
# One command runs the deterministic chain so adding an embodiment needs ZERO bespoke code:
# only a scene bundle (web/assets/scenes/<model>/), one experiments.json entry, and a
# trajectory (this script can record a generic one). Every step is the same generic tool
# driven by experiments.json (harness.py) — nothing here is hardcoded per embodiment.
#
# Usage:
#   bash add_scene.sh <exp> [--record] [--decimate <model-subdir>] [--skip-render] [--skip-qa]
#     <exp>              experiment key in experiments.json
#     --record           generate the trajectory with the generic physics recorder
#                        (record_trajectory.py). Omit if the entry's trajectory already
#                        exists (scripted IK like make_pick_trajectory.py, or a policy rollout).
#     --decimate <dir>   shrink web/assets/scenes/<dir> meshes to the web transfer budget
#                        (runs in the WSL venv — trimesh/fast_simplification live there).
#     --skip-render      skip the desktop mp4 (render_twin.py).
#     --skip-qa          skip node QA (loadtest wasm preflight + visual_check screenshot).
#
# Runtimes: python = Windows (mujoco 3.9), node = web/node_modules, decimate = WSL venv.
# Fail-fast: any step's non-zero exit aborts the pipeline.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"

EXP="${1:-}"
[ -n "$EXP" ] || { echo "usage: bash add_scene.sh <exp> [--record] [--decimate <dir>] [--skip-render] [--skip-qa]"; exit 2; }
shift
RECORD=0; DECIMATE_DIR=""; SKIP_RENDER=0; SKIP_QA=0
while [ $# -gt 0 ]; do
  case "$1" in
    --record)      RECORD=1 ;;
    --decimate)    DECIMATE_DIR="${2:?--decimate needs a model subdir}"; shift ;;
    --skip-render) SKIP_RENDER=1 ;;
    --skip-qa)     SKIP_QA=1 ;;
    *) echo "unknown arg: $1"; exit 2 ;;
  esac
  shift
done

# Resolve scene + trajectory for this experiment from the single registry (no hardcoding).
read -r SCENE TRAJ < <(python -c "from harness import get_experiment as g; e=g('$EXP'); print(e['scene'], e['trajectory'])")
echo "== experiment '$EXP'  scene=$SCENE  trajectory=$TRAJ"
step() { echo ""; echo "==> $*"; }

# 1. Mesh budget (WSL venv) — opt-in: only when a scene's meshes are over the web budget.
#    Convert the Git Bash path (/c/...) to a WSL path (/mnt/c/...) HERE, so the wsl command
#    string is all-literal — no $VAR/$(...) inside `wsl bash -lc` (that combo breaks; literal
#    paths work). sed (not wslpath, which isn't on the Git Bash PATH); a path already /mnt/* is
#    left unchanged. Paths under this repo have no spaces.
to_wsl() { echo "$1" | sed -E 's#^/([a-zA-Z])/#/mnt/\1/#'; }
if [ -n "$DECIMATE_DIR" ]; then
  step "decimate meshes (WSL venv): web/assets/scenes/$DECIMATE_DIR"
  DEC_WSL="$(to_wsl "$HERE/decimate_meshes.py")"
  ASSETS_WSL="$(to_wsl "$HERE/web/assets/scenes/$DECIMATE_DIR")"
  wsl bash -lc "~/playground-go1/.venv/bin/python $DEC_WSL $ASSETS_WSL"
fi

# 2. Scene manifest — the file list the web loader writes into the wasm FS (replaces a
#    hand-maintained array). Regenerate after any scene asset add/decimate.
step "regenerate scene manifest"
python web/gen_scene_manifest.py

# 3. Trajectory (opt-in) — generic physics recorder, robot-agnostic, zero bespoke code.
if [ "$RECORD" = 1 ]; then
  step "record generic trajectory: record_trajectory.py $EXP"
  python record_trajectory.py "$EXP"
fi

# 4. Smoke — headless load gate (scene loads, end-effector FK resolves, model moves). PASS/FAIL.
step "smoke (headless load gate): smoke_twin.py $EXP"
python smoke_twin.py "$EXP"

# 5. wasm preflight — the bundled scene must compile in mujoco-js@0.0.7 (the web wasm), which
#    is stricter than desktop mujoco. Catches web-only load failures before deploy.
if [ "$SKIP_QA" = 0 ]; then
  step "wasm preflight: qa/loadtest.mjs $SCENE"
  ( cd web && node qa/loadtest.mjs "$SCENE" )
fi

# 6. Desktop render — offscreen mp4 of the trajectory replay (matches the web replay).
if [ "$SKIP_RENDER" = 0 ]; then
  step "render desktop mp4: render_twin.py $EXP"
  python render_twin.py "$EXP"
fi

# 7. Single-source sync — mirror experiments.json + trajectory into web/ (step 1's guard).
step "sync data to web/ (single source)"
python sync_web.py

# 8. Visual QA — spawns serve_coi.py, drives the live scene in a headless browser, screenshots.
if [ "$SKIP_QA" = 0 ]; then
  step "visual QA: qa/visual_check.mjs --exp=$EXP"
  ( cd web && node qa/visual_check.mjs --exp="$EXP" )
fi

echo ""
echo "== DONE: '$EXP' pipeline complete."
