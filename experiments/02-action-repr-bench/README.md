# 02-action-repr-bench — 동작표현 2축 실측 비교 (OpenVLA 이산토큰 vs π0.5 flow-matching)

> `experiments/02-action-repr-bench/README.md` — 실험은 *가설·방법·결과·통찰* 4섹션.
> 통찰이 비었으면 실험이 *안 끝난* 것.
> 거버넌스: [ADR 0003](../../docs/adr/0003-second-policy-separate-harness.md) — "별도 하네스·동일 벤치마크·비교표".
> 짝: [experiment 01](../01-vla-local-eval/README.md) (OpenVLA 측 실측, 73%/n=15).

## 1. 가설 (Hypothesis)

**동일 LIBERO `libero_spatial` suite 위에서, 연속 flow-matching action-chunk 정책(π0.5)이 이산 토큰 autoregressive 정책(OpenVLA)과 비교 가능한 success rate를 달성한다.**

반증 가능 형태:
- **H-main**: π0.5의 `libero_spatial` success rate (n=500) 가 산출된다 (0 < SR < 1, 평가 하네스가 실제로 동작).
- **H-cmp**: 동일 task·동일 표본(n=500)에서 두 정책의 success rate를 비교한다. 95% CI가 겹치면 "두 동작표현 대등", 비겹침이면 우열 식별. (초안은 OpenVLA n=15 = 73%에 맞춰 세웠으나, 2026-06-11 OpenVLA를 n=500으로 재측정해 *대칭 비교*로 격상.)

> ⚠ 이 실험의 1차 목표는 ADR 0001의 "동작표현 축(이산 토큰 vs flow-matching chunk)"을 **같은 벤치마크 위 2점 실측**으로 채우는 것. 재측정으로 표본·task 모집단이 대칭이 되어 우열 식별도 *유효*해졌다(잔여 혼재는 하네스 차이뿐, 프로토콜 병기).

## 2. 방법 (Method)

### 셋업
- **정책 A**: OpenVLA-7B finetuned-libero-spatial. experiment 01 하네스(REST `/act`, 단일 step). **77.4% (387/500), n=500** (task 10 × trial 50, 2026-06-11 재측정 — 비대칭 caveat 해소).
- **정책 B**: π0.5 (`pi05_libero`), openpi 자체 하네스. flow-matching, action-chunk(horizon) 단위 추론. **98.4% (492/500), n=500** (공식 JAX 변환본).
- **공통 벤치마크**: LIBERO `libero_spatial`. 두 정책 모두 *같은 suite*. 코드는 다름(ADR 0003 — 공정성은 "같은 코드"가 아니라 "같은 벤치마크 + 명시된 프로토콜 차이").

### 정책 B 실행 경로 (openpi 별도 하네스)
- **환경**: WSL2 Ubuntu-24.04 + RTX 5090. `~/openpi` 별도 클론·별도 venv (transformers 4.53.2 수동패치). 비-Docker + EGL.
  - ⚠ Blackwell: openpi 핀 `torch 2.7.1+cu126` 는 sm_120 `no kernel image` 실패 → `+cu128` 휠 강제교체 적용됨.
- **체크포인트**: openpi JAX `gs://openpi-assets/checkpoints/pi05_libero` → **WSL 내 순수-python GCS(gcsfs anon)로 다운(9p 우회)** → `convert_jax_model_to_pytorch.py`(`JAX_PLATFORMS=cpu`)로 PyTorch 변환(공식, fp32). 상세 [`SETUP_NOTES.md` §1b]. (초기 HF 포트 fallback은 §1 — 공식본으로 대체됨)
- **2-프로세스**: 터미널1 `MUJOCO_GL=egl uv run examples/libero/main.py` (LIBERO 클라) + 터미널2 `uv run scripts/serve_policy.py policy:checkpoint --policy.config pi05_libero --policy.dir <ckpt>` (정책 서버).

### 측정 metric
- **success rate** = 성공 episode / 전체 episode. 정책 B: `libero_spatial` 10 task × **50 trial = 500 ep** (LIBERO 표준 프로토콜 — openpi 논문 수치와 직접 대조 가능, 95% CI ≈ ±4pp).
- raw 출력(eval 로그·per-task 성공수)은 `verify/` 에 박제 (재현성).

### 측정조건 병기 (ADR 0003 §Consequences — 필수)
| 항목 | OpenVLA (A) | π0.5 (B) |
|---|---|---|
| 표본 n | 500 (task 10×trial 50) | 500 (task 10×trial 50) |
| 95% CI 폭 | ≈ ±4pp | ≈ ±2pp |
| 하네스 | experiment 01 REST `/act` | openpi serve_policy + main.py |
| 추론 단위 | 단일 step autoregressive | action-chunk(horizon=10) flow-matching |
| seed/전처리 | experiment 01 기준 | openpi LIBERO 기본(seed=7, replan=5, resize=224) |

→ 표본·task 모집단이 대칭이라 head-to-head CI 비교가 *유효*. 남는 비대칭은 **하네스·추론단위**뿐 — 우열 *방향*의 증거이되 순수 동작표현 인과는 아님(프로토콜 병기로 명시).

## 3. 결과 (Results)

측정일 2026-06-11(재측정으로 두 caveat 해소). raw: [`verify/eval_result.txt`](verify/eval_result.txt) · 셋업: [`verify/SETUP_NOTES.md`](verify/SETUP_NOTES.md).

### 정식 비교 — full-suite, **n=500 양쪽 대칭 · 공식 가중치**
같은 10 task, 같은 표본(task당 50 trial), π0.5는 공식 JAX `pi05_libero` 변환본:

| 정책 | 동작표현 | n | success rate | 95% CI (Wilson) |
|------|---------|---|--------------|-----------------|
| **π0.5** | flow-matching chunk | 500 (10×50) | **98.4% (492/500)** | 96.9 – 99.2% |
| **OpenVLA** | 이산 토큰 autoregressive | 500 (10×50) | **77.4% (387/500)** | 73.5 – 80.8% |

- **flow-matching(π0.5) +21.0pp 우위. Fisher exact two-tailed p = 1.4e-27.**
- 이번엔 **task 모집단(10 task)·표본(n=500) 모두 동일** → 95% CI 비겹침(96.9 > 80.8)이 *유효한* head-to-head 식별. (이전 초안의 "다른 task 집합 CI 비교 무효" 문제를 재측정으로 해소.)
- ⚠ 잔여 혼재(불가피): 하네스가 다름(OpenVLA REST `/act` 단일 step vs π0.5 openpi action-chunk). ADR 0003대로 "같은 코드"가 아니라 "같은 벤치마크 + 명시 프로토콜 차이"로 공정성 확보 — *방향·크기*의 강한 증거이나 *순수 동작표현 인과*는 아님.

### per-task (task0~9, 동일 순서)
| task | OpenVLA (n=50) | π0.5 (n=50) |
|------|----------------|-------------|
| between the plate and the ramekin | 92% (46) | 100% (50) |
| next to the ramekin | 90% (45) | 98% (49) |
| from table center | 86% (43) | 100% (50) |
| on the cookie box | 86% (43) | 98% (49) |
| in the top drawer of the wooden cabinet | 70% (35) | 96% (48) |
| **on the ramekin** | **36% (18)** | 94% (47) |
| next to the cookie box | 94% (47) | 100% (50) |
| on the stove | 86% (43) | 100% (50) |
| next to the plate | 72% (36) | 100% (50) |
| on the wooden cabinet | 62% (31) | 98% (49) |
| **합** | **77.4% (387/500)** | **98.4% (492/500)** |

### 참고 — matched first-3-task (정직한 교정)
첫 3 task만 n=150씩: π0.5 **149/150(99.3%)** vs OpenVLA **134/150(89.3%)**, Fisher p=1.9e-4, +10pp.
> ⚠ 이전 초안의 matched-3task OpenVLA `11/15=73.3%`는 **소표본 잡음 과소추정**이었다. n=50/task로 키우니 같은 3 task가 89.3%. 당시 "+25pp" 매칭 우위는 OpenVLA의 15-trial 불운 탓 과장. *전체* 격차(+21pp)가 더 큰 건 task5/8/9 등 첫 3개 밖 난task에서 OpenVLA가 무너지기 때문.

### 박제 위치
- `verify/eval_result.txt` — 공식·대칭 결과 + per-task + 통계 + HF포트 교차검증. `verify/SETUP_NOTES.md` §1b — 공식 변환 경로.
- OpenVLA raw: [`../01-vla-local-eval/verify/openvla-500ep-eval.json`](../01-vla-local-eval/verify/openvla-500ep-eval.json). (π0.5 raw 로그·eval mp4는 WSL 홈, gitignored)

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- **n=500 대칭·공식 가중치에서 π0.5(98.4%, 492/500)가 OpenVLA(77.4%, 387/500)를 +21.0pp 앞선다** (Fisher exact p=1.4e-27, 95% CI 비겹침). 동일 task 모집단·동일 표본이라 이번 우열 식별은 *통계적으로 유효*하다. ⚠ 단 하네스 차이가 섞여 *순수 동작표현 인과*는 아님 — 방향·크기의 강한 증거.
- **격차는 task 난이도에 크게 의존한다** — 평면 픽업(between/next-to-cookie-box)은 OpenVLA도 90~94%로 거의 대등. 그러나 occlusion·height task에서 OpenVLA가 붕괴: **on the ramekin 36%(vs π0.5 94%)**, on wooden cabinet 62%, next to plate 72%. flow-matching의 이점은 *어려운 공간 추론*에서 가장 크게 드러난다.
- **소표본의 위험 — 정직한 교정**: 초안의 matched-3task OpenVLA `73.3%(11/15)`는 잡음 과소추정이었다(n=150에선 89.3%). 같은 task인데 표본만 키워도 +16pp 변동 → 단일 seed·소표본 비교의 위험을 실증. *전체* 격차가 더 큰 건 난task가 첫 3개 밖에 몰려서다.
- **HF 포트 ≈ 공식**: HF 포트 97.6% vs 공식 변환 98.4%(0.8pp, CI 내). safetensors 바이트 크기도 동일 → HF 포트가 충실했고, 이번에 weights·norm_stats를 공식 단일 출처로 교체해 provenance를 박았다.
- **π0.5 수치는 openpi 논문 pi05 LIBERO(~97-98%)와 일관** — 셋업 정합성의 강한 시사.
- **운영 통찰(ADR 0003 실증)**: 스택 격리(transformers 핀 충돌·cu128 revert·9p 대용량 쓰기 한계)가 별도 하네스를 강제했다. + 9p 막힘은 **Windows gsutil** 탓이었고 **WSL 내 순수-python GCS(gcsfs anon)** 로 우회해 공식 변환을 끝냈다 [`verify/SETUP_NOTES.md` §1b].
- **eval은 sim-bound**(GPU util ~30-60%) — MuJoCo·EGL·왕복이 병목. OpenVLA 단일-step autoregressive는 π0.5 action-chunk보다 느려 500ep에 ~5.6h(π0.5 ~2h).

### ✅ caveat 해소 (2026-06-11 재측정)
- **표본 비대칭 해소**: OpenVLA를 10 task×50=500ep로 재측정 → 양쪽 n=500, CI 폭 대칭(±~4pp). 더는 "신뢰도 다른 두 수치"가 아니라 유효한 head-to-head.
- **provenance 해소**: π0.5 weights·norm_stats를 공식 JAX `pi05_libero` 변환본으로 교체(HF 포트 탈피). [`verify/SETUP_NOTES.md` §1b].
- 잔여(설계상 불가피, caveat 아님): 하네스·전처리 차이 — ADR 0003 프로토콜 병기로 처리.

### 가설은 통과했나?
- [x] **H-main PASS** — π0.5 libero_spatial SR = 98.4%(492/500) 산출 (0<SR<1, 하네스 정상 동작).
- [x] **H-cmp PASS** — n=500 대칭·동일 task에서 π0.5 98.4% > OpenVLA 77.4%, 95% CI 비겹침·Fisher p=1.4e-27. (이전 matched-only 판정에서 *유효 full-suite 식별*로 격상.)

### 정의에 반영
- [ADR 0001](../../docs/adr/0001-vla-action-representation.md) "동작표현 3축"의 이산토큰·flow-matching 2점을 **동일 벤치마크·대칭 표본 실측**으로 갱신.

### 다음 실험 후보
- 다른 suite(libero_object/goal/10)로 일반화 — spatial은 π0.5가 거의 천장. 더 어려운 suite에서 +21pp 격차가 유지되나?
- 동작표현 3번째 점 ACT(M6) — 직접 회귀 vs 토큰 vs flow-matching 3자 완성.
