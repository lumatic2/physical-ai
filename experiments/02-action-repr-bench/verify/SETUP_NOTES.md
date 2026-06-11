# π0.5 LIBERO eval — 재현 셋업 노트 (실측 경로 박제)

> 2026-06-10 실행. 환경: WSL2 Ubuntu-24.04 + RTX 5090(sm_120) + openpi `~/openpi`.
> 이 노트는 *실제로 작동한* 경로. 핸드오프 계획에서 벗어난 지점은 "⚠ 편차"로 표시.

## 0. 구조
- **서버**(π0.5 정책): openpi 메인 venv `~/openpi/.venv` (python 3.11). GPU 추론.
- **클라**(LIBERO 시뮬): 별도 venv `~/openpi/examples/libero/.venv` (python 3.8). CPU 시뮬 + websocket.
- 두 프로세스가 ws://0.0.0.0:8000 으로 통신 (ADR 0003 "별도 하네스" 그대로).

## 1b. 체크포인트 — ✅ 공식 변환 경로 (2026-06-11, provenance caveat 해소)
> 아래 1번의 9p 막힘은 **Windows gsutil 바이너리** 탓이었다. WSL 안의 **순수-python GCS(`gcsfs` anon)** 로 받으면 9p 우회 → 공식 변환 성공.
- **다운로드**: `gcsfs.GCSFileSystem(token="anon").get("openpi-assets/checkpoints/pi05_libero", dest, recursive=True)` → `~/.cache/openpi/openpi-assets/checkpoints/pi05_libero/pi05_libero/` (12.4GB, `params/` + `assets/`). openpi `.venv` 에 jax 0.5.3·orbax·flax 존재.
- **변환**: `JAX_PLATFORMS=cpu .venv/bin/python examples/convert_jax_model_to_pytorch.py --checkpoint_dir <…/pi05_libero/pi05_libero> --config_name pi05_libero --output_path <…/pi05_libero_pytorch_official> --precision float32`. CPU 변환이라 sm_120 무관. 결과: `model.safetensors` 14.5GB(HF 포트와 **바이트 크기 동일**) + `config.json`.
- **⚠ assets graft**: convert 스크립트의 assets 복사는 `checkpoint_dir.parent/assets` 를 봐서 중첩 경로선 빗나감 → 공식 `assets/`(같은 norm_stats 1914B, 이번엔 공식 출처)를 `<output>/assets/` 로 직접 복사.
- **서버**: `.venv/bin/python scripts/serve_policy.py policy:checkpoint --policy.config pi05_libero --policy.dir <…/pi05_libero_pytorch_official>` → "Loaded norm stats from …/pi05_libero_pytorch_official/assets/physical-intelligence/libero" 확인.
- 결과: 공식 500ep = 492/500 = 98.4% (HF 포트 97.6%와 0.8pp 차, CI 내 일치 — HF 포트 충실성 재확인 + provenance 공식화).

## 1. 체크포인트 — ⚠ 편차: JAX 변환 대신 HF 포트 (초기 경로, 1b 로 대체됨)
- **계획**: `gs://openpi-assets/checkpoints/pi05_libero`(JAX) 다운 → `convert_jax_model_to_pytorch.py` 변환.
- **막힘**: gsutil 이 Windows SDK 바이너리(`/mnt/c/...`)라, WSL 9p 파일시스템에 **1.5GB+ 대용량 shard 쓰기가 실패**(빈 `CommandException` ×6, 작은 파일만 성공). `-m` sliced 비활성화·rsync 재시도 모두 동일 실패. → **Windows gsutil → WSL 9p 대용량 쓰기 한계**로 결론.
- **해결(결정된 fallback)**: HF 포트 `pepijn223/pi05_libero_fp32` 를 `huggingface_hub.snapshot_download` 로 직접 WSL fs 에 받음(순수 python, 9p 우회). 14GB fp32 `model.safetensors`.
- **⚠ norm_stats graft 필수**: HF 포트엔 `assets/` 가 없고 `policy_preprocessor.json` 만 있음. 그러나 `create_trained_policy` 는 `<ckpt>/assets/<asset_id>/norm_stats.json` 을 찾음(`policy_config.py:60`, asset_id = repo_id = `physical-intelligence/libero`). → JAX 체크포인트의 작은 `norm_stats.json`(1.9KB, gsutil 로 정상 다운)만 떼어 그 경로에 배치:
  ```
  <ckpt>/assets/physical-intelligence/libero/norm_stats.json
  ```
  배치 후 서버 로그 "Loaded norm stats from .../pi05_libero_pytorch/assets/physical-intelligence/libero" 확인.
- 최종 ckpt dir: `~/.cache/openpi/checkpoints/pi05_libero_pytorch/` (model.safetensors + config.json + assets/.../norm_stats.json).

## 2. Blackwell torch — ⚠ uv run 이 cu128 을 revert
- openpi 핀 `torch 2.7.1+cu126` 는 sm_120 미지원 (`arch=[...sm_90]`, 추론 시 no kernel image).
- cu128 휠 교체:
  ```bash
  cd ~/openpi && UV_LINK_MODE=copy uv pip install --reinstall-package torch --reinstall-package torchvision \
    "torch==2.7.1+cu128" "torchvision==0.22.1+cu128" --index-url https://download.pytorch.org/whl/cu128
  ```
- **⚠ 핵심 함정**: `uv run <script>` 는 매 실행마다 lockfile 로 env 를 재동기화 → **cu128 을 cu126 으로 revert**("Uninstalled 14 / Installed 14"). 첫 서버 기동 때 sm_120 경고가 이래서 떴음.
  → **해결: 서버는 `uv run` 말고 `.venv/bin/python` 직접 호출**. 적용 후 `arch=[...sm_120, compute_120]`, CUDA matmul 통과.

## 3. 서버 기동
```bash
cd ~/openpi
.venv/bin/python scripts/serve_policy.py policy:checkpoint \
  --policy.config pi05_libero \
  --policy.dir ~/.cache/openpi/checkpoints/pi05_libero_pytorch
# → "server listening on 0.0.0.0:8000"
```
- `create_trained_policy` 가 `model.safetensors` 존재로 PyTorch 자동감지(`policy_config.py:48`).

## 4. 클라(LIBERO) venv — openpi 비-Docker 레시피 (examples/libero/README "Without Docker")
```bash
cd ~/openpi && export UV_LINK_MODE=copy
uv venv --python 3.8 examples/libero/.venv
source examples/libero/.venv/bin/activate
uv pip sync examples/libero/requirements.txt third_party/libero/requirements.txt \
  --extra-index-url https://download.pytorch.org/whl/cu113 --index-strategy=unsafe-best-match
uv pip install -e packages/openpi-client
uv pip install -e third_party/libero
# 검증: libero_spatial 10 tasks, robosuite 1.4.1, mujoco 3.2.3, numpy 1.22.4
```

## 5. eval 실행
```bash
cd ~/openpi
export PYTHONPATH=$PWD/third_party/libero
export MUJOCO_GL=egl
examples/libero/.venv/bin/python examples/libero/main.py
# 기본값: task_suite_name=libero_spatial, num_trials_per_task=50, seed=7, replan_steps=5, resize=224
# → 10 task × 50 trial = 500 ep
```
- **측정조건(병기용)**: seed=7, replan_steps=5, resize 224, fp32 ckpt(선택 params bf16 캐스팅), suite=libero_spatial.
- **타이밍**: 첫 에피소드 ~213s(torch max-autotune compile warmup) → 정상상태 ~12s/ep. 500ep ≈ ~100분.
- 결과 로그: `~/pi05_eval_logs/client.log` 의 "Total success rate" + per-task. (eval.json/videos 는 gitignored, 핵심 수치만 verify/ 박제)
