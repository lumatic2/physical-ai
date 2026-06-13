# 04-go1-rl-walk — Go1 joystick 보행 정책 직접 학습 → ONNX → native mujoco 검증

> ADR [0005](../../docs/adr/0005-learned-policy-sandbox.md) **단계 1 (학습 spike)**. 트윈을 scripted replay에서
> "직접 학습한 정책의 closed-loop 추론"으로 승격하는 첫 관문 — GPU에서 정책을 학습해 onnx로 뽑고,
> *학습 sim이 아닌* native mujoco에서 그 정책이 실제로 Go1을 걷게 하는지 본다(브라우저 parity의 토대).

## 1. 가설 (Hypothesis)

로컬 RTX5090(WSL)에서 MuJoCo Playground `Go1JoystickFlatTerrain` env를 단시간 RL 학습해 ONNX로 export하면,
그 정책 하나가 **native mujoco-python에서 Go1을 command 방향으로 N초 안 넘어지고 걷게** 만든다.

- 반증(FAIL): ① 학습이 JAX-on-Blackwell(sm_120) 인프라로 끝내 막히고 rsl_rl 폴백도 안 되거나, ② export된
  정책이 native mujoco closed-loop에서 즉시 넘어지거나 command 방향으로 전진하지 못하면 가설 FAIL.

## 2. 방법 (Method)

### 셋업 (S0~S1 완료, 2026-06-13)
- 환경: WSL `Ubuntu-24.04`, RTX5090 32GB (드라이버 596.49), **CUDA passthrough 작동 확인**(WSL 내부 nvidia-smi가 GPU 인식), `uv` 0.11.8, python 3.12.3. nvcc 없음(pip wheel이 CUDA 런타임 번들 → 무관).
- venv: `~/playground-go1/.venv` (WSL 네이티브, py3.12). `uv pip install "playground" "jax[cuda12]"` → mujoco_playground 전체 의존성 + jax/jaxlib **0.10.1** cuda12.
- 학습 lib: `mujoco_playground` (DeepMind MJX). 레포 `github.com/google-deepmind/mujoco_playground`.
  - **주 경로 확정**: `train-jax-ppo`(JAX/MJX). ✅ **sm_120 probe PASS** — jax 0.10.1이 Blackwell에서 실제 커널 실행(matmul block_until_ready, `verify/s0-s1-env-probe.txt`). 폴백 불필요.
  - (폴백 보류: `train-rsl-ppo`(rsl_rl/PyTorch, torch cu128 Blackwell 검증 — [exp 02](../02-action-repr-bench/README.md)). JAX가 돌아 미사용.)
- env: `Go1JoystickFlatTerrain` (flat terrain, command range 제한으로 단순화).
- 검증 sim: native `mujoco`-python(closed-loop, qpos 재생 아님).

### 시나리오 (verify 게이트 단계 — mock=probe 먼저, real=학습 다음)
| 단계 | 내용 | verify (성공 조건) |
|---|---|---|
| **S0** 환경 bring-up | WSL uv venv(py3.12) + `playground` + `jax[cuda12]` 설치 | ✅ jax 0.10.1, `jax.devices()`→`[CudaDevice(id=0)]` |
| **S1** sm_120 probe | jaxlib에서 sm_120 행렬연산 실제 실행 스모크 | ✅ **PASS** — matmul 정확, backend=gpu → **JAX 경로 확정** |
| **S2** 단시간 학습 | `Go1JoystickFlatTerrain` 학습(목표 ~5분, flat, command 제한) | reward 수렴 + ckpt 산출 |
| **S3** ONNX export | ckpt → onnx. **obs_spec 정확히 기록**(관절순서·정규화·body-frame 중력·command·clock) | onnx 파일 + obs_spec 문서(웹 parity 진실원천) |
| **S4** native 검증 ★ | native mujoco-python에서 onnx 정책 closed-loop 롤아웃 | **Go1이 command 방향으로 N초(목표 ≥10s) 안 넘어지고 전진** |

### 측정 metric
- 학습: wall-clock(분), reward curve 수렴, env steps/sec.
- 검증: 넘어지지 않고 보행한 시간(s), command 추종 전진속도(m/s), 정성(발 미끄러짐·자세).
- 경로 결정: JAX vs rsl_rl 중 어느 것으로 끝냈나 + 그 이유.

## 3. 결과 (Results)

> 실행 후 채움 — 현재 스켈레톤. (Judge: 통찰 선보고 금지, S0~S4 돌린 raw를 `verify/`에 박제 후 기록)

### 데이터
| Run | 경로(JAX/rsl) | 학습시간 | 보행 지속(s) | 전진(m/s) | 비고 |
|-----|--------------|---------|-------------|----------|------|
| — | | | | | |

### 박제 위치
- `verify/` — 학습 로그·reward curve·onnx·native 롤아웃 mp4/로그.

## 4. 통찰 (Insights)

> 실행 후 채움.

### 무엇을 알아냈나
- (S4 PASS 후)

### 가설은 통과했나?
- [ ] PASS — 근거:
- [ ] FAIL — 어긋난 지점, 가설 수정:

### 정의에 반영
- ADR 0005 단계 1 verify 게이트 통과 기록. obs_spec → Phase 2 데스크탑 통합의 진실원천.

### 다음 실험 후보
- Phase 2: `experiments.json`에 `policy` 블록 + `rollout_policy.py`(같은 onnx를 mujoco-python closed-loop) → mp4 + obs parity.
