#!/usr/bin/env bash
# setup.sh — vla-eval 로컬 환경 부트스트랩.
# 대상: WSL2 Ubuntu-24.04 + NVIDIA Blackwell(RTX 5090, sm_120). 다른 GPU 면 cu128 인덱스만 조정.
# 단계: venv → torch(cu128) → requirements → LIBERO(--no-deps) → config 시드 → 스모크 안내.
set -euo pipefail

VENV="${VENV:-$HOME/.venvs/vla-eval}"
LIBERO_DIR="${LIBERO_DIR:-$HOME/LIBERO}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "[setup] venv → $VENV"
python3 -m venv "$VENV"
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

# config 시드 — libero 패키지는 첫 import 시 ~/.libero/config.yaml 을 자동 생성한다.
echo "[setup] seeding LIBERO config (~/.libero/config.yaml)"
PYTHONPATH="$LIBERO_DIR" python -c "from libero.libero import benchmark; benchmark.get_benchmark_dict(); print('  config ok')"

cat <<EOF

[setup] 완료. venv = $VENV, LIBERO = $LIBERO_DIR

스모크 (1 task × 1 trial, 모델 로드 ~3분):
  PYTHONPATH=$LIBERO_DIR MUJOCO_GL=egl "$VENV/bin/python" "$HERE/run.py" --suite libero_spatial --tasks 1 --trials 1

전체 예 (3 task × 5 trial):
  PYTHONPATH=$LIBERO_DIR MUJOCO_GL=egl "$VENV/bin/python" "$HERE/run.py" --suite libero_spatial --tasks 3 --trials 5
EOF
