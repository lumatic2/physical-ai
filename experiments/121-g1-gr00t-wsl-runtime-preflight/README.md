# 121-g1-gr00t-wsl-runtime-preflight — GR00T WSL runtime preflight

> `experiments/121-g1-gr00t-wsl-runtime-preflight/README.md` — M19 real controller trace capture before exp120 visible/browser gate.

## 1. 가설 (Hypothesis)

Unitree G1은 공개 관절 범위와 squat posture mode 기준으로 squat 자세 자체는 가능하지만, M19가 요구하는 것은 "no-balance squat posture"가 아니라 균형 제어된 measured 29-DOF trace다. WSL에서 GR00T/SONIC MuJoCo runtime이 뜨면 다음 실험은 환경 복구가 아니라 실제 controller trace capture로 넘어갈 수 있다.

## 2. 방법 (Method)

### 셋업
- 로봇: Unitree G1 / G1 EDU public spec.
- 후보 controller stack: NVIDIA GR00T-WholeBodyControl / GEAR-SONIC / Decoupled WBC.
- 로컬 runtime: WSL `Ubuntu-24.04`, native checkout `/home/yusun/gr00t-wbc-native`, RTX 5090 CUDA visible.

### 웹 근거
- Unitree G1 공식 페이지는 G1이 23-43 joint motors, leg 6 DoF, knee 0-165 deg, hip pitch +/-154 deg 범위를 가진다고 설명한다. 출처: https://www.unitree.com/g1/ (accessed 2026-06-18).
- G1 operation docs는 `Squat Mode`가 squat posture로 천천히 전환한다고 설명하지만, balance control은 없다고 명시한다. 출처: https://docs.quadruped.de/projects/g1/html/operation_1.2.html (accessed 2026-06-18).
- GR00T-WholeBodyControl은 humanoid WBC codebase이고 GEAR-SONIC은 G1 whole-body motion/controller 경로를 제공한다. 출처: https://github.com/NVlabs/GR00T-WholeBodyControl, https://nvlabs.github.io/GR00T-WholeBodyControl/ (accessed 2026-06-18).
- Decoupled WBC docs는 Unitree G1을 primary support 대상으로 하는 whole-body control policies, teleoperation stack, data exporter를 설명한다. 출처: https://nvlabs.github.io/GR00T-WholeBodyControl/references/decoupled_wbc.html (accessed 2026-06-18).

### 로컬 검증
- WSL Git LFS 설치 상태를 확인했다.
- HF sample download를 `huggingface_hub` isolated venv로 수행했다.
- GR00T source를 `/mnt/c` checkout이 아니라 WSL-native `/home/yusun/gr00t-wbc-native`로 복사하고 `install_mujoco_sim.sh`를 실행했다.
- `run_sim_loop.py --help`, MuJoCo/Torch/ZMQ import smoke, short headless `run_sim_loop.py` timeout smoke를 실행했다.
- `/mnt/c` checkout에서 `.venv_sim` 생성이 permission denied로 막히는 것을 별도 probe로 박제했다.

### 측정 metric
- `git_lfs_healthy`
- `hf_sample_download_present`
- `run_sim_help_pass`
- `venv_import_smoke_pass`
- `torch_cuda_visible`
- `g1_balance_walk_onnx_present`
- `run_sim_loop_timeout_smoke_no_traceback`
- `windows_mount_install_permission_block_confirmed`

## 3. 결과 (Results)

### 데이터
| Run | Verdict | 핵심 결과 | M19 |
|-----|---------|-----------|-----|
| WSL runtime preflight | `WSL_SIM_RUNTIME_PREFLIGHT_PASS__DEPLOYMENT_PARTIAL` | Git LFS/HF sample/sim venv/import/CUDA/run_sim_loop startup smoke PASS | open |

### 체크 결과
- Git LFS: PASS, `git-lfs/3.4.1`.
- HF sample data: PASS, 6 sample PKL files present under `/home/yusun/gr00t_sample_download_probe`.
- GR00T MuJoCo sim venv: PASS on WSL-native checkout.
- `run_sim_loop.py --help`: PASS.
- Import smoke: PASS, MuJoCo 3.9.0, Torch 2.12.1+cu130, CUDA visible, ZMQ import OK.
- G1 Balance/Walk ONNX assets: PASS.
- Short headless sim-loop startup: PASS as timeout smoke, `RUN_SIM_RC:124`, no traceback.
- `/mnt/c` install path: confirmed unsuitable, `.venv_sim` creation failed with permission denied.
- Deployment partial blocker: `TensorRT_ROOT` is not set, so C++ deployment/controller trace capture is not closed.

### 박제 위치
- Raw result: [`verify/result.json`](verify/result.json)
- Summary: [`verify/summary.md`](verify/summary.md)
- Reproducer: [`run_gr00t_wsl_runtime_preflight.py`](run_gr00t_wsl_runtime_preflight.py)

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- "해당 로봇으로 squat 자세가 가능한가?"에 대한 답은 yes에 가깝다. 공식 관절 범위와 Squat Mode가 posture 가능성을 뒷받침한다.
- 그러나 M19의 목표는 posture 가능성이 아니라 balance-controlled visible squat이다. G1 docs의 Squat Mode는 no balance control이므로 M19 evidence로는 부족하다.
- 환경 blocker는 대부분 제거됐다. 다음 병목은 Windows/WSL 설치가 아니라 GR00T deployment 또는 동등 WBC에서 measured `g1_debug`/CSV trace를 얻는 것이다.
- GR00T sim stack은 `/mnt/c`가 아니라 WSL-native filesystem에서 실행해야 한다.

### 가설은 통과했나?
- [x] PASS — WSL-native GR00T MuJoCo sim runtime은 trace capture 전 단계까지 준비됐다.
- [ ] FAIL — M19는 아직 닫히지 않았다. 실제 controller trace가 exp120 adapter와 exp29 visible/browser gate를 통과해야 한다.

### 정의에 반영
- ROADMAP M19를 exp121 기준으로 갱신한다. M19 완료 조건은 계속 native visible gate + browser replay 동시 PASS다.

### 다음 실험 후보
- exp122: GR00T/SONIC deployment or Decoupled WBC trace capture. `run_sim_loop.py`와 controller/deployment process를 함께 띄우고 measured `g1_debug`/CSV를 exp120 adapter로 흘린다.
