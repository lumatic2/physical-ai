#!/usr/bin/env bash
# setup.sh — vla-eval 로컬 환경 부트스트랩.
# 대상: WSL2 Ubuntu-24.04 + Python 3.12 + NVIDIA Blackwell(RTX 5090, sm_120). 다른 GPU 면 cu128 인덱스만 조정.
# 단계: venv → torch(cu128) → requirements → LIBERO(--no-deps) → config 시드 → 스모크 안내.
set -euo pipefail

VENV="${VENV:-$HOME/.venvs/vla-eval}"
LIBERO_DIR="${LIBERO_DIR:-$HOME/LIBERO}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
LEROBOT_DIR="${LEROBOT_DIR:-$HERE/../../references/huggingface-lerobot}"

"$PYTHON_BIN" - <<'PY'
import sys

if sys.version_info < (3, 12):
    raise SystemExit(
        f"[setup] Python 3.12+ required by the reviewed LeRobot source; got {sys.version.split()[0]}"
    )
PY

echo "[setup] venv → $VENV ($PYTHON_BIN)"
"$PYTHON_BIN" -m venv "$VENV"
# shellcheck disable=SC1091
source "$VENV/bin/activate"
pip install --upgrade pip

# torch/torchvision — Blackwell(sm_120)은 cu128 휠 필요 (기본 PyPI 휠은 sm_120 미포함 → 런타임 실패).
echo "[setup] torch + torchvision (cu128)"
pip install torch==2.11.* torchvision --index-url https://download.pytorch.org/whl/cu128

echo "[setup] requirements.txt"
pip install -r "$HERE/requirements.txt"

# LIBERO — 상류 stale 핀 회피 위해 소스 클론 후 --no-deps 설치.
if [ ! -d "$LIBERO_DIR" ]; then
  echo "[setup] cloning LIBERO → $LIBERO_DIR"
  git clone https://github.com/Lifelong-Robot-Learning/LIBERO.git "$LIBERO_DIR"
fi
echo "[setup] LIBERO (--no-deps)"
pip install --no-deps -e "$LIBERO_DIR"

# LAB1 canonical recorder — use the reviewed repository source and install only
# dataset/runtime dependencies from requirements.txt to avoid changing OpenVLA's
# intentionally pinned transformers stack.
if [ ! -f "$LEROBOT_DIR/pyproject.toml" ]; then
  echo "[setup] missing LeRobot source: $LEROBOT_DIR" >&2
  exit 1
fi
echo "[setup] LeRobot dataset runtime (--no-deps) → $LEROBOT_DIR"
pip install --no-deps -e "$LEROBOT_DIR"

# config 시드 — LIBERO upstream은 첫 import에서 input()을 호출하므로
# non-interactive setup에서는 동일한 기본 경로를 먼저 기록한다.
echo "[setup] seeding LIBERO config (~/.libero/config.yaml)"
LIBERO_DIR="$LIBERO_DIR" python - <<'PY'
import os
from pathlib import Path

import yaml

package_root = (Path(os.environ["LIBERO_DIR"]) / "libero" / "libero").resolve()
config_dir = Path(os.environ.get("LIBERO_CONFIG_PATH", "~/.libero")).expanduser()
config_dir.mkdir(parents=True, exist_ok=True)
config_file = config_dir / "config.yaml"
if not config_file.exists():
    config = {
        "benchmark_root": str(package_root),
        "bddl_files": str(package_root / "bddl_files"),
        "init_states": str(package_root / "init_files"),
        "datasets": str(package_root.parent / "datasets"),
        "assets": str(package_root / "assets"),
    }
    config_file.write_text(yaml.safe_dump(config), encoding="utf-8")
PY
PYTHONPATH="$LIBERO_DIR" python -c "from libero.libero import benchmark; benchmark.get_benchmark_dict(); print('  config ok')"

cat <<EOF

[setup] 완료. venv = $VENV, LIBERO = $LIBERO_DIR

스모크 (1 task × 1 trial, 모델 로드 ~3분):
  PYTHONPATH=$LIBERO_DIR MUJOCO_GL=egl "$VENV/bin/python" "$HERE/run.py" --suite libero_spatial --tasks 1 --trials 1

전체 예 (3 task × 5 trial):
  PYTHONPATH=$LIBERO_DIR MUJOCO_GL=egl "$VENV/bin/python" "$HERE/run.py" --suite libero_spatial --tasks 3 --trials 5
EOF
