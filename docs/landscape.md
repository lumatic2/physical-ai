# 피지컬 AI 지형도 (Landscape)

> M1 산출물. 이 분야의 용어·기술 스택·주요 플레이어·핵심 논문을 한 장에 정리한다.
> **인용 규약**: 모든 외부 주장에 출처 URL. 본 문서의 모든 링크는 **2026-06-09** 접근 기준.
> 1차 출처(arXiv·공식 발표)를 우선하고, 시장 수치 등 2차 출처(블로그·뉴스 roundup)는 〔2차〕로 표기.

---

## 1. 정의

**피지컬 AI(Physical AI) = embodied AI**. 기계에 체화되어 주변을 *감지*하고 물리 세계에 *행동*하는 AI. 텍스트·이미지·코드를 순수 계산 환경에서 처리하는 디지털 AI와 달리, 실제 물체·표면·힘의 연속적이고 노이즈가 많은 물리를 다뤄야 한다. NVIDIA는 "Physical AI"를 generative AI 다음의 플랫폼 전환 카테고리로 위치시킨다 ([NVIDIA Glossary: Generative Physical AI](https://www.nvidia.com/en-us/glossary/generative-physical-ai/), [NVIDIA Glossary: Embodied AI](https://www.nvidia.com/en-us/glossary/embodied-ai/)).

핵심 한 줄: **파운데이션 모델 × 로보틱스의 수렴** — 실세계를 인지·추론·행동하는 AI 시스템.

---

## 2. 핵심 용어 · taxonomy

| 용어 | 뜻 |
|------|----|
| **Embodied AI** | 물리적 몸을 가진 에이전트의 지능 (= Physical AI) |
| **VLA (Vision-Language-Action)** | 카메라 이미지 + 텍스트 지시 → 로봇 동작을 직접 출력하는 모델. 인지·계획·제어 모듈 분리 없이 단일 forward pass ([Wikipedia: VLA](https://en.wikipedia.org/wiki/Vision-language-action_model)) |
| **Foundation/Generalist Policy** | 여러 로봇·태스크에 걸쳐 일반화하는 정책 모델 (예: π0, GR00T N1) |
| **World Model** | 환경의 동역학을 학습해 미래를 "상상"하는 모델. 데이터 효율·계획에 사용 (Dreamer, Genie) |
| **Cross-embodiment** | 서로 다른 로봇 하드웨어 간 학습 전이 (RT-X, Open X-Embodiment) |
| **Sim-to-Real** | 시뮬레이터에서 학습한 정책을 실물 로봇으로 옮길 때의 격차(reality gap)와 그 극복 |
| **Diffusion / Flow-matching policy** | 동작 시퀀스를 확산·flow matching으로 생성하는 정책 (Diffusion Policy, π0) |
| **Action chunking** | 단일 step이 아닌 동작 *시퀀스*를 한 번에 예측 (ACT) |
| **Manipulation / Locomotion** | 조작(팔·손) / 이동(보행·주행) — 로봇 태스크의 두 축 |
| **Teleoperation** | 사람이 원격 조종해 시연 데이터를 수집 (ALOHA) |
| **Synthetic data** | 시뮬레이터·world model로 생성한 학습 데이터 (Cosmos, Isaac GR00T Blueprint) |

### 기술 스택 (4 레이어 — SW부터 HW까지)

```
[인지·추론]  VLM 기반 멀티모달 이해 (System 2)  ─┐
[정책·제어]  VLA / diffusion·flow policy (System 1) ─┤  소프트웨어
[시뮬·데이터] Isaac Sim·MuJoCo·Genesis, world model ─┘
[하드웨어]   휴머노이드·매니퓰레이터·센서·온보드 컴퓨트(Jetson Thor)  ← 실물
```

대표적 분업 구조: NVIDIA GR00T N1의 **dual-system** — System 1(빠른 반사적 동작 모델) + System 2(느린 VLM 기반 숙고·계획) ([NVIDIA Research: GR00T N1](https://research.nvidia.com/publication/2025-03_nvidia-isaac-gr00t-n1-open-foundation-model-humanoid-robots)).

---

## 3. 주요 플레이어 · 랩 맵

### 소프트웨어 / 파운데이션 모델 랩

| 주체 | 대표 산출물 | 메모 |
|------|-----------|------|
| **Physical Intelligence** | π0, π0.5, π*0.6 | 2024 설립(DeepMind·Stanford·Berkeley 출신). 2025-11 $600M 투자 유치, 밸류 $5.6B (CapitalG·Bezos·Thrive·Lux) 〔2차: [TheRobotReport](https://www.therobotreport.com/physical-intelligence-open-sources-pi0-robotics-foundation-model/)〕 |
| **Google DeepMind** | RT-2, RT-X / Open X-Embodiment, Gemini Robotics | Gemini 2.0 멀티모달 기반 로보틱스 ([DeepMind blog](https://deepmind.google/blog/scaling-up-learning-across-many-different-robot-types/)) |
| **NVIDIA** | Isaac GR00T N1(휴머노이드 FM), Cosmos(world FM), Isaac Sim/Lab, Jetson Thor | 3축: 시뮬(Omniverse)·모델(GR00T)·컴퓨트(Thor) ([NVIDIA Newsroom](https://nvidianews.nvidia.com/news/nvidia-isaac-gr00t-n1-open-humanoid-robot-foundation-model-simulation-frameworks)) |

### 하드웨어 / 휴머노이드 기업 〔주로 2차 출처〕

| 기업 | 제품 | 상태 (2026 기준) |
|------|------|----------------|
| **Figure AI** | Figure 02 | BMW Spartanburg 라인 11개월 가동, 3만+ 차량 기여 〔[EVST](https://www.evsint.com/top-8-humanoid-robot-companies-2026/)〕 |
| **Tesla** | Optimus Gen 2 | 5'8"·약 57kg, 목표가 $20–30k. 자사 공장 내부 배치 〔[LumiChats](https://lumichats.com/blog/humanoid-robots-2026-tesla-optimus-figure-ai-unitree-complete-guide)〕 |
| **Unitree** | G1 | ~$16k부터 상용 판매, 2025년 5,500+ 대 출하 〔EVST〕 |
| **1X** | NEO | 가정용 이족보행. OpenAI·Tiger·Samsung $125M 투자. ~$20k 또는 $499/월, 2026 미국 early-access 〔EVST〕 |
| **Agility Robotics** | Digit | Amazon 창고 테스트, 양산 시설 확보 〔EVST〕 |
| 기타 | Apptronik, Boston Dynamics(Atlas), AgiBot | 2026 watchlist 〔EVST〕 |

### 시뮬레이터 / 툴링

| 도구 | 특징 |
|------|------|
| **Isaac Sim / Isaac Lab** | NVIDIA GPU 위 대규모 병렬, 휴머노이드·4족 보행 학습. RTX 포토리얼 렌더 + 센서 시뮬 ([SVRC 비교](https://www.roboticscenter.ai/learn/robot-simulation-software-comparison)) |
| **MuJoCo (MJX)** | 접촉 물리의 gold standard. v3.0+ JAX 백엔드로 GPU/TPU 가속 |
| **Genesis** | 신예. rigid·soft·fluid 멀티피직스 + 미분가능(differentiable) |
| 기타 | Robosuite, Brax, PyBullet, Gazebo, Drake |

---

## 4. 핵심 논문 Reading List

> 태그: 🧠 정책/모델 · 🌍 world model · 📦 데이터셋 · 🔧 하드웨어/시스템 · 📋 서베이

| # | 논문 | 연도 | 태그 | 한 줄 |
|---|------|------|------|------|
| 1 | [RT-2: VLA transfer web knowledge to robotic control](https://en.wikipedia.org/wiki/Vision-language-action_model) (DeepMind) | 2023 | 🧠 | 최초의 인터넷 스케일 일반화 VLA — 동작을 "언어 토큰"으로 취급 |
| 2 | [Open X-Embodiment / RT-X](https://arxiv.org/abs/2310.08864) | 2023 | 📦🧠 | 34개 랩·22종 로봇·100만+ 시연 통합, cross-embodiment 양전이 |
| 3 | [Diffusion Policy](https://arxiv.org/abs/2303.04137) | 2023 | 🧠 | 동작 생성을 확산 과정으로 — visuomotor 정책의 표준 베이스라인 |
| 4 | [ALOHA + ACT](https://arxiv.org/abs/2304.13705) | 2023 | 🔧🧠 | $20k 저가 양팔 원격조종 + action chunking, 10분 시연으로 정밀 조작 |
| 5 | [Mobile ALOHA](https://arxiv.org/abs/2401.02117) | 2024 | 🔧🧠 | 전신 이동 조작으로 ALOHA 확장 (요리·세탁) |
| 6 | [OpenVLA](https://arxiv.org/abs/2406.09246) | 2024 | 🧠 | 최초의 완전 오픈소스·상용가능 VLA(7B), RT-2-X(55B) 대비 +16.5% |
| 7 | [π0: VLA Flow Model for General Robot Control](https://arxiv.org/abs/2410.24164) (Physical Intelligence) | 2024 | 🧠 | VLM + flow matching, 빨래 개기·테이블 정리 등 범용 generalist policy |
| 8 | [π*0.6: a VLA That Learns From Experience](https://arxiv.org/abs/2511.14759) | 2025 | 🧠 | 경험으로 학습하는 후속 모델 |
| 9 | [Gemini Robotics](https://arxiv.org/abs/2503.20020) (DeepMind) | 2025 | 🧠 | Gemini 2.0 멀티모달 기반 로보틱스 |
| 10 | [NVIDIA Isaac GR00T N1](https://research.nvidia.com/publication/2025-03_nvidia-isaac-gr00t-n1-open-foundation-model-humanoid-robots) | 2025 | 🧠🔧 | 최초의 오픈 휴머노이드 FM, System1/System2 dual-system |
| 11 | [Genie: Generative Interactive Environments](https://arxiv.org/abs/2402.15391) (DeepMind) | 2024 | 🌍 | 비디오에서 플레이 가능한 환경 생성 — world model 계열 |
| 12 | DreamerV3 (Nature 2025) | 2025 | 🌍 | latent imagination으로 행동 학습, 범용 RL 〔[Awesome-World-Models](https://github.com/leofan90/Awesome-World-Models)〕 |
| 13 | [Survey: Large VLM-based VLA Models for Manipulation](https://arxiv.org/abs/2508.13073) | 2025 | 📋 | VLA 분야 전체 서베이 — 입문 지도용 |
| 14 | [Survey: Navigation & Manipulation with Physics Simulators](https://arxiv.org/abs/2505.01458) | 2025 | 📋 | 시뮬레이터·sim-to-real 서베이 |
| 15 | [Cosmos World Foundation Models](https://huggingface.co/blog/nvidia-physical-ai) (NVIDIA) | 2025 | 🌍📦 | 합성 데이터 생성용 world FM (Cosmos Transfer 7B) |

다음 단계(M2): 위 1~15 중 핵심 5개를 골라 `references/<handle>-<repo>/`에 ANALYSIS_TEMPLATE 5섹션으로 정독.

---

## 5. 관찰 · 다음 액션

- **수렴 지점**: VLA가 2024~2026 로봇 혁명의 공통 아키텍처. 오픈 생태계(OpenVLA·π0·Octo·RT-X)가 빠르게 형성 중.
- **SW↔HW 다리**: ALOHA류 저가 하드웨어 + 모방학습이 진입장벽을 낮춤 — 개인/소규모도 데이터 수집·실험 가능. M3 프로젝트 후보의 유력 출발점.
- **데이터 병목**: 실물 데이터가 비싸 → 시뮬·world model 합성 데이터(Cosmos, Isaac Blueprint)가 핵심 전장.
- **미해결**: sim-to-real 격차, 안전성, 온디바이스 추론 비용(Jetson Thor) — 서베이 논문(#13·14)에서 보강.

> 시장 수치(투자·출하·배치)는 대부분 2차 블로그/뉴스 roundup 기반 — M2 정독 시 1차 출처(IR·공식 발표)로 교차검증 필요.
