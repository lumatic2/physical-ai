# 02-action-repr-bench — 동작표현 2축 실측 비교 (OpenVLA 이산토큰 vs π0.5 flow-matching)

> `experiments/02-action-repr-bench/README.md` — 실험은 *가설·방법·결과·통찰* 4섹션.
> 통찰이 비었으면 실험이 *안 끝난* 것.
> 거버넌스: [ADR 0003](../../docs/adr/0003-second-policy-separate-harness.md) — "별도 하네스·동일 벤치마크·비교표".
> 짝: [experiment 01](../01-vla-local-eval/README.md) (OpenVLA 측 실측, 73%/n=15).

## 1. 가설 (Hypothesis)

**동일 LIBERO `libero_spatial` suite 위에서, 연속 flow-matching action-chunk 정책(π0.5)이 이산 토큰 autoregressive 정책(OpenVLA)과 비교 가능한 success rate를 달성한다.**

반증 가능 형태:
- **H-main**: π0.5의 `libero_spatial` success rate (n=500) 가 산출된다 (0 < SR < 1, 평가 하네스가 실제로 동작).
- **H-cmp**: π0.5 SR 의 95% CI 가 OpenVLA 측정치(73%, 11/15, n=15)의 95% Wilson CI(약 48~89%)와 **겹치거나 그 위**다. → 겹치면 "두 동작표현이 이 벤치마크에서 구분 불가/대등", CI 하단(~48%)보다 **아래**면 "이 셋업에서 flow-matching이 열위"로 가설 약화·수정.

> ⚠ 이 실험은 *우열 판정*이 1차 목표가 아니다. ADR 0001의 "동작표현 축(이산 토큰 vs flow-matching chunk)"을 **같은 벤치마크 위 2점 실측**으로 채우는 게 목표. 우열은 측정조건(표본 비대칭)을 병기한 *부차적* 관찰.

## 2. 방법 (Method)

### 셋업
- **정책 A (기존 실측, 재측정 안 함)**: OpenVLA-7B finetuned-libero-spatial. experiment 01 하네스(REST `/act`, 단일 step). **73% (11/15), n=15** (task 3 × trial 5).
- **정책 B (이번 측정)**: π0.5 (`pi05_libero`), openpi 자체 하네스. flow-matching, action-chunk(horizon) 단위 추론.
- **공통 벤치마크**: LIBERO `libero_spatial`. 두 정책 모두 *같은 suite*. 코드는 다름(ADR 0003 — 공정성은 "같은 코드"가 아니라 "같은 벤치마크 + 명시된 프로토콜 차이").

### 정책 B 실행 경로 (openpi 별도 하네스)
- **환경**: WSL2 Ubuntu-24.04 + RTX 5090. `~/openpi` 별도 클론·별도 venv (transformers 4.53.2 수동패치). 비-Docker + EGL.
  - ⚠ Blackwell: openpi 핀 `torch 2.7.1+cu126` 는 sm_120 `no kernel image` 실패 → `+cu128` 휠 강제교체 적용됨.
- **체크포인트**: openpi JAX `gs://openpi-assets/checkpoints/pi05_libero` → `convert_jax_model_to_pytorch.py` 로 PyTorch 변환. (sm_120 변환 이슈 시 `JAX_PLATFORMS=cpu`, 그래도 막히면 HF 포트 `pepijn223/pi05_libero_fp32` fallback)
- **2-프로세스**: 터미널1 `MUJOCO_GL=egl uv run examples/libero/main.py` (LIBERO 클라) + 터미널2 `uv run scripts/serve_policy.py policy:checkpoint --policy.config pi05_libero --policy.dir <ckpt>` (정책 서버).

### 측정 metric
- **success rate** = 성공 episode / 전체 episode. 정책 B: `libero_spatial` 10 task × **50 trial = 500 ep** (LIBERO 표준 프로토콜 — openpi 논문 수치와 직접 대조 가능, 95% CI ≈ ±4pp).
- raw 출력(eval 로그·per-task 성공수)은 `verify/` 에 박제 (재현성).

### 측정조건 병기 (ADR 0003 §Consequences — 필수)
| 항목 | OpenVLA (A) | π0.5 (B) |
|---|---|---|
| 표본 n | 15 (task 3×trial 5) | 500 (task 10×trial 50) |
| 95% CI 폭 | ≈ ±22pp (넓음) | ≈ ±4pp (좁음) |
| 하네스 | experiment 01 REST `/act` | openpi serve_policy + main.py |
| 추론 단위 | 단일 step autoregressive | action-chunk flow-matching |
| seed/전처리 | experiment 01 기준 | openpi LIBERO 기본 |

→ 비대칭이 크므로 결과표는 **head-to-head 우열이 아니라 "각 수치의 신뢰도가 다름"** 으로 읽어야 한다.

## 3. 결과 (Results)

측정일 2026-06-10. raw: [`verify/eval_result.txt`](verify/eval_result.txt) · 셋업: [`verify/SETUP_NOTES.md`](verify/SETUP_NOTES.md).

### (A) 정식 비교 — **matched 3 task** (동일 task 집합, apples-to-apples)
experiment 01 OpenVLA는 libero_spatial **첫 3개 task**만 측정(`--tasks 3`). 그 동일 3 task로 π0.5를 매칭한 게 *통제된* 비교다:

| task (동일) | OpenVLA (n=5) | π0.5 (n=50) |
|---|---|---|
| between plate and ramekin | 4/5 | 49/50 |
| next to ramekin | 3/5 | 49/50 |
| from table center | 4/5 | 50/50 |
| **합** | **11/15 = 73.3%** | **148/150 = 98.7%** |

- 같은 task 집합에서 **flow-matching(π0.5) +25pp 우위**. pooled 2×2 **Fisher exact two-tailed p = 6.1e-4** (< 0.001).
- ⚠ 단서: 표본 작음(OpenVLA task당 5 trial), 단일 seed, 하네스 다름(REST `/act` 단일 step vs openpi action-chunk) — *동작표현 차이*에 *하네스·전처리 차이*가 섞임. Fisher 는 1차 검정(task 구조 무시 pooled).

### (B) 참고 — full-suite (통제 안 됨, task 수 다름)
| 정책 | 동작표현 | suite | n (task×trial) | success rate | 95% CI (Wilson) |
|------|---------|-------|----------------|--------------|-----------------|
| OpenVLA (exp 01) | 이산 토큰 autoregressive | libero_spatial | 15 (3×5) | 73.3% (11/15) | 48.1 – 89.1% |
| π0.5 | flow-matching chunk | libero_spatial | 500 (10×50) | 97.6% (488/500) | 95.9 – 98.6% |

> ⚠ **이건 head-to-head 아님** — OpenVLA는 3 task, π0.5는 10 task로 **task 모집단이 다르다**. 다른 task 집합 간 CI 비교/유의차 주장은 무효. full-suite 수치는 *각 모델의 단독 성적*으로만 읽고, 우열 판단은 위 (A) matched 비교에 근거할 것.

### per-task (π0.5, 실행순서)
| SR | task |
|----|------|
| 0.98 | between plate and ramekin |
| 0.98 | next to ramekin |
| 1.00 | table center |
| 1.00 | on cookie box |
| 0.94 | in top drawer of wooden cabinet |
| 1.00 | on ramekin |
| 1.00 | next to cookie box |
| 0.96 | on stove |
| 1.00 | next to plate |
| 0.90 | on wooden cabinet |

### 박제 위치
- `verify/eval_result.txt` — 총·per-task SR + 통계. `verify/SETUP_NOTES.md` — 재현 경로.
- (eval mp4·서버/클라 raw 로그는 gitignored)

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- **동일 3 task(matched)에서 π0.5(98.7%, 148/150)가 OpenVLA(73.3%, 11/15)를 +25pp 앞선다** (Fisher exact p=6.1e-4). 동작표현 축에서 flow-matching chunk가 이 task들에선 이산 토큰 autoregressive보다 강하다. ⚠ 단, 하네스·전처리 차이가 섞여 *순수 동작표현 효과*로 단정 불가 — 방향·크기의 증거이지 통제된 인과 아님.
- ⚠ **full-suite 비교(97.6% vs 73.3%)는 통제 안 됨** — task 수가 다르다(10 vs 3). 다른 task 모집단 간 우열·CI 비교는 무효. 이전 초안의 "CI 비겹침 → 통계적 식별" 주장은 철회(adversarial-review에서 교정).
- **π0.5 수치는 openpi 논문 pi05 LIBERO 대(~97-98%)와 일관** — 셋업이 크게 어긋나지 않았다는 *시사*. 단 *증명*은 아니다(동일 학습 run·norm_stats 정합성 미검증 — 아래 caveat).
- **π0.5의 실패는 height/occlusion에 몰린다** — 최난도가 "on the wooden cabinet"(0.90)·"in the top drawer"(0.94). 평면 픽업은 거의 1.0. 잔여 난이도는 동작표현이 아니라 3D 공간 추론 쪽.
- **운영 통찰(ADR 0003 실증)**: 스택 격리(transformers 핀 충돌·cu128 revert·9p 대용량 쓰기 한계)가 실제로 별도 하네스를 강제했다 — "통합 /act 어댑터 하나" 가정은 깨졌고, 격리가 옳았다. [`verify/SETUP_NOTES.md`].
- **eval은 GPU-bound가 아니라 sim-bound**(GPU util ~30%) — 추론이 아니라 MuJoCo 물리·EGL 렌더·요청왕복이 병목. 멀티에이전트 workflow로 가속 불가, OS 프로세스 샤딩만 유효(미채택 — 하네스 개조 회피).

### ⚠ caveat (검증 안 된 것 — 결론 강도 제한)
- **체크포인트 provenance**: π0.5 weights는 HF 포트 `pepijn223/pi05_libero_fp32`(공식 openpi 배포 아님). 공식 JAX `pi05_libero`와 동일 학습 run인지 미검증. norm_stats 는 JAX 체크포인트에서 graft — weights↔norm_stats 정합성은 "서버 로드 성공 + 논문대 일치"의 간접 증거뿐, 형식 검증 아님.
- 정식 head-to-head 를 원하면 → OpenVLA 를 10 task×50 으로 재측정(보류, ADR 0003) 또는 공식 JAX 체크포인트로 변환.

### 가설은 통과했나?
- [x] **H-main PASS** — π0.5 libero_spatial SR = 97.6%(488/500) 산출 (0<SR<1, 하네스 정상 동작).
- [x] **H-cmp PASS (matched 기준)** — 동일 3 task에서 π0.5 98.7% > OpenVLA 73.3% (Fisher p<0.001). ※ full-suite CI 비교가 아니라 *matched-subset* 으로 판정(다른 task 집합 CI 비교는 무효).

### 정의에 반영
- [ADR 0001](../../docs/adr/0001-vla-action-representation.md) "동작표현 3축"의 이산토큰·flow-matching 2점을 **동일 벤치마크 실측**으로 갱신.

### 다음 실험 후보
- 다른 suite(libero_object/goal/10)로 일반화 — spatial은 π0.5가 거의 천장. 더 어려운 suite에서 격차가 유지되나?
- OpenVLA를 matched n=500으로 재측정해 비대칭 제거(현재 의도적 미실행, ADR 0003).
- 동작표현 3번째 점 ACT(M6) — 직접 회귀 vs 토큰 vs flow-matching 3자 완성.
