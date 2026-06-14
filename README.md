# physical-ai

> 컨슈머 GPU에서 VLA(Vision-Language-Action) 정책을 직접 돌리고, 서로 다른 **동작 표현(action representation)** 두 가지를 같은 벤치마크로 실측 비교한 피지컬 AI 학습·리서치 레포.

피지컬 AI(embodied AI·로보틱스)를 논문·코드 수준으로 정독해 쌓고, 그 위에서 *실제로 돌아가는 도구와 실측 결과*로 검증한다. 정의만 외우지 않고 — **컨슈머 GPU(RTX 5090/WSL2)에서 모델을 직접 띄워 숫자를 낸다.**

---

## 5분 요약

**무엇을 알아냈나** — VLA 모델은 백본이 VLM으로 수렴하지만 *로봇 동작을 어떻게 표현하느냐*에서 갈린다: **이산 토큰화**(OpenVLA) · **flow-matching chunk**(π0) · **CVAE 직접 회귀**(ACT). 이 차이를 `구조축 × 동작표현축` 2D 좌표로 정의 → [ADR 0001](docs/adr/0001-vla-action-representation.md).

**무엇을 만들었나** —
1. **[vla-eval](experiments/01-vla-local-eval/README.md)** — 컨슈머 GPU에서 **1커맨드로 VLA 정책을 평가**하는 도구 (Windows/WSL2·Blackwell sm_120·세그폴트/의존성 해법 내장).
2. **[action-repr-bench](experiments/02-action-repr-bench/README.md)** — 두 동작표현을 같은 LIBERO 벤치마크로 **head-to-head 실측**.
3. **[digital-twin](experiments/03-digital-twin/web/README.md)** — 하드웨어 없이 브라우저에서 도는 **인터랙티브 3D 임베디먼트 갤러리(8종)**. 그중 둘은 **내가 직접 RL로 학습한 보행 정책이 onnxruntime-web으로 실시간 closed-loop** 구동(4족 Go1 · 휴머노이드 G1). → **라이브: [physical-ai-arm.askewly.com](https://physical-ai-arm.askewly.com)**

---

## 🎯 핵심 결과 — 동작표현 head-to-head (실측)

동일 LIBERO `libero_spatial`, **양쪽 n=500**(10 task × 50 trial), π0.5는 공식 JAX 변환본:

| 정책 | 동작 표현 | 성공률 | 95% CI |
|------|----------|--------|--------|
| **π0.5** | flow-matching chunk | **98.4%** (492/500) | 96.9 – 99.2% |
| **OpenVLA** | 이산 토큰 autoregressive | **77.4%** (387/500) | 73.5 – 80.8% |

→ **flow-matching +21.0pp 우위** (Fisher exact p=1.4e-27, 95% CI 비겹침). 격차는 난이도에 의존 — 평면 픽업은 두 모델 모두 ~90%+이지만, occlusion·height task(예: "on the ramekin")에서 OpenVLA는 36%까지 붕괴하고 π0.5는 94%를 유지한다. *동작표현의 차이가 어려운 공간추론에서 가장 크게 드러난다.*

> 방법론 메모: 두 모델은 하네스가 다르므로(REST 단일-step vs openpi action-chunk) "같은 코드"가 아니라 **"같은 벤치마크 + 명시된 프로토콜 차이"**로 공정성을 확보했다. 표본·task 모집단은 대칭(n=500). 전체 셋업·통계·caveat: [experiment 02](experiments/02-action-repr-bench/README.md).

---

## 만든 것 ① vla-eval — 1커맨드 로컬 VLA 평가

컨슈머 GPU에서 OpenVLA 같은 7B VLA를 LIBERO 시뮬로 평가한다. tf↔robosuite-EGL in-process 세그폴트를 **REST 서버/클라 프로세스 분리**로 회피하고, Blackwell(sm_120)용 torch cu128·LIBERO 의존성 해법을 `setup.sh`에 박았다.

```bash
# WSL2 Ubuntu + NVIDIA GPU 기준
bash experiments/01-vla-local-eval/setup.sh
PYTHONPATH=~/LIBERO MUJOCO_GL=egl \
  python experiments/01-vla-local-eval/run.py --suite libero_spatial --tasks 3 --trials 5
```

빈 venv에서 `setup.sh`만으로 재현되는지 클린룸 검증 완료 → [verify/cleanroom](experiments/01-vla-local-eval/verify/cleanroom-2026-06-11.txt).

## 만든 것 ② action-repr-bench — 동작표현 실측 비교

위 핵심 결과의 실험. 가설·방법·결과·통찰 4섹션 + raw 박제 + 재현 셋업노트. → [README](experiments/02-action-repr-bench/README.md)

---

## 만든 것 ③ digital-twin — 브라우저 임베디먼트 갤러리 + 직접 학습한 보행 정책

**[physical-ai-arm.askewly.com](https://physical-ai-arm.askewly.com)** — 하드웨어 없이 sim→real 직전까지. MuJoCo를 WASM으로 브라우저에 띄워 8종 로봇을 인터랙티브 3D로 돌린다(`?exp=` 로 전환).

| `?exp=` | 임베디먼트 | 구동 방식 |
|---|---|---|
| `go1-walk` | Unitree Go1 (4족) | ⭐ **직접 학습한 RL 정책** — onnxruntime-web live closed-loop + 조이스틱 조향 |
| `g1-walk` | Unitree G1 (휴머노이드) | ⭐ **직접 학습한 RL 정책** — 103-d obs + gait phase clock, live closed-loop |
| `so100-stack` | SO-ARM100 팔 | scripted pick-and-place 3단 스택 replay |
| `panda-sweep` | Franka Panda 팔 | scripted 관절 sweep replay |
| `shadow-hand` | Shadow Hand | scripted 손가락 굴곡 replay |
| `spot-stand` · `g1-stand` · `humanoid-settle` | Spot·G1·휴머노이드 | 물리 settle |

**직접 학습한 정책이 브라우저에서 몸을 제어한다** — MuJoCo Playground에서 PPO로 보행 정책을 학습(RTX5090, ~9~47분)하고 ONNX로 뽑은 뒤, 브라우저에서 `obs→onnx→ctrl→mj_step@50Hz` closed-loop로 돌린다. 학습 sim과 **obs 바이트 단위 parity**(golden fixture 단언)로 sim2sim 충실도를 보장 → [exp 04 (Go1)](experiments/04-go1-rl-walk/README.md) · [exp 05 (G1 휴머노이드)](experiments/05-g1-rl-walk/). config-driven 하네스(`experiments.json`)라 새 임베디먼트는 JS 0줄로 추가 → [exp 03](experiments/03-digital-twin/web/README.md).

---

## 공부한 것 — 레퍼런스 정독 (M2)

각 레퍼런스를 5섹션(`references/ANALYSIS_TEMPLATE.md`)으로 분석. 클론 소스는 gitignored, 분석 노트만 추적.

| 레퍼런스 | 동작 표현 | 분석 |
|---------|----------|------|
| openvla/openvla | 이산 토큰 | [ANALYSIS](references/openvla-openvla/ANALYSIS.md) |
| Physical-Intelligence/openpi (π0) | flow-matching | [ANALYSIS](references/Physical-Intelligence-openpi/ANALYSIS.md) |
| tonyzhaozh/act | CVAE 직접 회귀 | [ANALYSIS](references/tonyzhaozh-act/ANALYSIS.md) |
| google-deepmind/open_x_embodiment | (데이터셋) | [ANALYSIS](references/google-deepmind-open_x_embodiment/ANALYSIS.md) |
| VLA survey (2508.13073) | (서베이) | [ANALYSIS](references/vla-survey-2508.13073/ANALYSIS.md) |

→ 종합 정의: [ADR 0001 — 동작표현 2축](docs/adr/0001-vla-action-representation.md). 지형도(정의·스택·플레이어 맵): [docs/landscape.md](docs/landscape.md).

---

## 진행 상태

| 마일스톤 | | 산출물 |
|---------|---|-------|
| **M1** 지형 파악 | ✅ | [docs/landscape.md](docs/landscape.md) |
| **M2** 레퍼런스 정독 | ✅ | [references/](references/) 5편 + [ADR 0001](docs/adr/0001-vla-action-representation.md) |
| **M3** 로컬 추론·평가 | ✅ | [experiment 01](experiments/01-vla-local-eval/README.md) — VLA 로컬 실행 + LIBERO 평가 |
| **M4** 도구화·비교 | ✅ | 01 productize + [experiment 02](experiments/02-action-repr-bench/README.md) 동작표현 실측 |
| **M5** 포트폴리오 패키징 | ✅ | 이 README + [블로그 글](https://askewly.com) + vault 정리 |
| **M6** 디지털 트윈 (sim) | ✅ | [exp 03](experiments/03-digital-twin/web/README.md) — 브라우저 인터랙티브 3D + 정책 replay |
| **M8** 학습 정책 sandbox | ✅ | [exp 04·05](experiments/04-go1-rl-walk/README.md) — 직접 학습한 Go1·G1 보행 정책 live closed-loop + 임베디먼트 갤러리 8종 |
| **M7** 실물 도달 (하드웨어) | ⬜ | 저가팔 + ACT (구매 게이트, 보류) |

상세 이력·의사결정: [ROADMAP.md](ROADMAP.md) · [docs/adr/](docs/adr/) (0001~0005)

## 구조

```
physical-ai/
├── experiments/          # 실측 (가설·방법·결과·통찰 4섹션 + verify/ raw 박제)
│   ├── 01-vla-local-eval/    #   vla-eval 도구
│   ├── 02-action-repr-bench/ #   동작표현 head-to-head
│   ├── 03-digital-twin/      #   브라우저 임베디먼트 갤러리 (MuJoCo WASM) + config 하네스
│   ├── 04-go1-rl-walk/       #   Go1 보행 정책 학습 → ONNX → live closed-loop
│   └── 05-g1-rl-walk/        #   G1 휴머노이드 보행 정책 (동 파이프라인)
├── references/           # 외부 레포·논문 정독 노트 (ANALYSIS.md 5섹션)
├── docs/
│   ├── landscape.md      #   피지컬 AI 지형도
│   └── adr/              #   의사결정 기록 (Nygard 포맷)
└── ROADMAP.md            # 마일스톤·이력
```
