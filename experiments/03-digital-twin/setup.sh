#!/usr/bin/env bash
# Fetch the SO-100 (trs_so_arm100) MuJoCo model from MuJoCo Menagerie (DeepMind),
# sparse-checkout only that folder, and drop our scene_twin.xml next to it so the
# `<include file="so_arm100.xml"/>` and asset paths resolve. Model is NOT tracked
# (large meshes) — this script reconstructs vendor/ on any machine.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
VENDOR="$HERE/vendor"
MENAGERIE="$VENDOR/mujoco_menagerie"

mkdir -p "$VENDOR"
if [ ! -d "$MENAGERIE/trs_so_arm100" ]; then
  echo "== sparse-checkout trs_so_arm100 from mujoco_menagerie"
  git clone --depth 1 --filter=blob:none --sparse \
    https://github.com/google-deepmind/mujoco_menagerie.git "$MENAGERIE"
  ( cd "$MENAGERIE" && git sparse-checkout set trs_so_arm100 )
fi

cp "$HERE/scene_twin.xml" "$MENAGERIE/trs_so_arm100/scene_twin.xml"
echo "== model ready: $MENAGERIE/trs_so_arm100/"
echo "   next:  pip install -r requirements.txt  &&  python smoke_twin.py  &&  python render_twin.py"
