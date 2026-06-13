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
- venv: `~/playground-go1/.venv` (WSL 네이티브, py3.12). `uv pip install "playground" "jax[cuda12]"` + `onnx onnxruntime`.
  - ⚠ **버전 함정(S2 중 발견)**: `jax[cuda12]`가 0.10.1을 끌어왔으나 **brax 0.14.2가 `jax.device_put_replicated`(jax 0.10에서 제거)를 사용** → 학습 즉시 크래시. brax 최신이 0.14.2라 업핀 불가 → **jax/jaxlib를 0.9.2로 다운핀**(device_put_replicated 존재 + sm_120 재검증 PASS). 재현 시 `jax[cuda12]==0.9.2` 고정 필수.
  - ⚠ **impl 함정**: env 기본 `impl="warp"`는 `mujoco_warp`(미설치) 요구 → `config_overrides={"impl":"jax"}`(클래식 MJX)로 우회.
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

전 단계 PASS (2026-06-13). 경로: **JAX(train-jax-ppo / MJX impl=jax)** — sm_120 probe PASS로 폴백 불필요.

### 데이터
| 단계 | 결과 |
|---|---|
| S0~S1 환경/probe | jax 0.9.2 sm_120 커널 실행 PASS (`verify/s0-s1-env-probe.txt`) |
| S2 학습 | `Go1JoystickFlatTerrain` 200M steps, **8.8분**(RTX5090, impl=jax). reward **0.001 → 29.68** 수렴 (`verify/rewards.txt`) |
| S3 ONNX export | 손작성 onnx 그래프 vs jax `make_inference_fn` **max abs err 4.78e-6** (난수 obs 50개) → PARITY PASS. `verify/go1_policy.onnx`(770KB), `verify/obs_spec.json` |
| **S4 native 검증** ★ | native mujoco-python closed-loop(`env.mj_model`, C 엔진), cmd_vx=1.0: **넘어짐 never · 12.0s 직립 · 전진 11.84m · avg_vx 0.99 m/s** · 최종높이 0.303. `verify/native_rollout.mp4`(300f) |

### 박제 위치
- `verify/` — `s0-s1-env-probe.txt`, `rewards.txt`(학습곡선), `go1_policy.onnx`, `obs_spec.json`, `native_rollout.mp4`.
- WSL `~/playground-go1/runs/go1flat/` — `params.pkl`(1.7MB, brax params), `native_rollout.npy`(qpos 궤적).

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- **로컬 RTX5090서 사족보행 정책을 직접 학습→ONNX→native sim 전이까지 한 바퀴가 닫힌다.** 8.8분 학습으로 command를 0.99/1.0 정확도로 추종하는 보행 정책 확보.
- **sim2sim가 즉시 성립** — MJX(학습)에서 학습한 정책이 native mujoco(C 엔진)에서 *재튜닝 없이* 12s 안 넘어지고 걷는다. 같은 Menagerie Go1 자산 + obs 바이트 parity 덕분(ADR 0005 가설대로).
- **obs parity는 "동일 named 센서 재사용"으로 거의 공짜** — linvel/gravity를 손계산하지 않고 학습과 같은 MJCF 센서를 `data.sensordata`에서 읽으니 어긋날 여지가 없다. gravity만 `site_xmat.T @ [0,0,-1]`로 계산.
- **최대 리스크였던 JAX-on-Blackwell이 무료** — jax 0.9.2 sm_120 PASS. 단 **brax 0.14.2 ↔ jax 0.10 비호환**(`device_put_replicated`)이 숨은 함정이었고 jax 0.9.2 다운핀으로 해결.
- ONNX parity(4.78e-6)는 **손작성 그래프 + jax 대조 assert**로 증명 — Phase 2/3(데스크탑·웹)이 의존할 토대.

### 가설은 통과했나?
- [x] **PASS** — onnx 정책 1개가 native mujoco-python closed-loop에서 Go1을 command 방향으로 11.84m, 12.0s 안 넘어지고 보행(avg_vx 0.99 m/s). 성공 기준 충족.

### 정의에 반영
- ADR 0005 단계 1 verify 게이트 **통과**. `obs_spec.md`/`obs_spec.json`이 Phase 2(데스크탑 closed-loop)·Phase 3(웹 onnxruntime-web) parity의 진실원천.

### 다음 실험 후보
- Phase 2: `experiments.json`에 `policy` 블록 + `rollout_policy.py`(같은 onnx를 mujoco-python closed-loop) → mp4 + obs parity.
- Phase 3: 웹 onnxruntime-web. **obs-builder를 `verify/golden_obs.json`에 슬롯 단위로 단언**(Codex 교차검증 권고 — 난수 parity만으론 builder 버그 못 잡음). `obs_spec.json`의 `default_pose`로 obs/ctrl 재구성.

### Codex 교차검증 (2026-06-13, adversarial-review)
- [high→해결] `obs_spec.json` `default_pose`가 None이라 웹이 obs/ctrl 재구성 불가 → export가 home keyframe에서 채우도록 수정(len 12 단언).
- [medium→가드화] 난수 obs parity는 obs *조립*을 검증 못 함 → `golden_obs.json` 박제로 Phase 3 슬롯 단언 표적 제공. S4 보행 추종이 builder를 경험적으로 검증 중.
