# openvla/openvla 분석

> `references/openvla-openvla/ANALYSIS.md` — 클론 옆에 둠. 시간 박스: 레포당 90분.
> 클론: https://github.com/openvla/openvla (2026-06-09 접근). 논문: [arXiv 2406.09246](https://arxiv.org/abs/2406.09246).

## 1. 한 줄 요약 / 무엇을 하는 하네스인가

**오픈소스 7B VLA** — 사전학습된 멀티모달 VLM(Prismatic) 위에 *동작 토큰화* 로직만 얹어, 카메라 이미지 + 텍스트 지시를 받아 로봇의 end-effector 동작(연속값)을 출력하는 generalist 정책. RT-2의 "동작을 언어처럼" 패러다임을 완전 오픈소스·상용가능하게 재현. 분류 어휘로는 **L1 정책 모델(policy)** + **L2 데이터 파이프라인(RLDS/OXE)** + **L3 배포 서버(REST)** 의 결합.

## 2. 디렉터리 지도 (핵심 폴더만)

```
openvla/
├── prismatic/
│   ├── models/
│   │   ├── vlms/prismatic.py        # 베이스 VLM (비전+LLM 결합)
│   │   ├── vlas/openvla.py          # ★ VLA = PrismaticVLM 얇은 래퍼 + predict_action
│   │   └── backbones/
│   │       ├── vision/dinosiglip_vit.py  # ★ DINOv2 + SigLIP 융합 비전 백본
│   │       └── llm/llama2.py        # Llama-2 LLM 백본
│   └── vla/
│       ├── action_tokenizer.py      # ★ 연속 동작 → 256 bin → 어휘 끝 토큰
│       └── datasets/rlds/oxe/       # Open X-Embodiment(OXE) 데이터 믹스 ("magic soup")
├── vla-scripts/
│   ├── train.py / finetune.py       # 사전학습 / LoRA·full 파인튜닝
│   └── deploy.py                    # ★ FastAPI REST `/act` 추론 서버
└── experiments/robot/              # 실물/벤치(BridgeData·LIBERO 등) 평가 코드
```

## 3. 아키텍처 레이어 매핑 (로보틱스 — landscape §2 4레이어와 정렬)

| 레이어 | 위치 (파일:줄) | 내용 |
|--------|---------------|------|
| 입력·센서 (관측) | `dinosiglip_vit.py:39-40`, `vlas/openvla.py:69` | 단일 RGB 이미지를 DINOv2·SigLIP 두 transform으로 동시 전처리 |
| 인지·추론 (VLM 백본) | `vlms/prismatic.py`, `dinosiglip_vit.py:43-58` | DINOv2(공간) + SigLIP(의미) 특징 concat → Llama-2 7B에 투영 |
| 정책·액션 생성 | `action_tokenizer.py:31-47`, `vlas/openvla.py:81-91` | 256-bin 이산화 → 어휘 *끝* 토큰; autoregressive `generate(max_new_tokens=action_dim)` |
| 학습·데이터 | `vla/datasets/rlds/oxe/`, `vla-scripts/finetune.py` | RLDS 포맷 OXE 믹스로 사전학습; 다운스트림은 LoRA 파인튜닝 |
| 하드웨어·배포 | `vla-scripts/deploy.py:65-89` | HF `AutoModelForVision2Seq`(bf16, flash-attn2)를 FastAPI `/act`로 서빙 |

핵심: 새로운 "action head"를 만들지 않는다 — **LLM의 기존 토큰 예측 헤드를 그대로 동작 출력에 재사용**. 그래서 모델은 사실상 PrismaticVLM의 얇은 서브클래스(`openvla.py:23`).

## 4. 인상 깊은 코드/패턴 (파일 경로 + 줄 번호 필수)

- `prismatic/vla/action_tokenizer.py:36,45` — 어휘의 *최하위 사용* 256개 토큰을 동작 bin으로 덮어쓴다(`vocab_size - discretized_action`). LLM 구조를 1바이트도 안 바꾸고 연속 제어를 언어 모델링 문제로 환원하는 핵심 트릭. RT-2의 아이디어를 가장 간결하게 구현.
- `prismatic/models/vlas/openvla.py:84` — `max_new_tokens = self.get_action_dim()`. 동작 차원(예: 7-DoF = xyz·rpy·gripper)만큼만 토큰 생성 → 출력 길이가 결정론적. 텍스트 생성과 달리 EOS를 기다릴 필요 없음.
- `prismatic/models/vlas/openvla.py:61-64` — Llama 토크나이저의 빈 토큰(`29871`)을 프롬프트 끝에 강제 삽입해 *학습 시 분포와 일치*시킨다. VLA 추론이 토크나이저 사소한 차이에 얼마나 취약한지 보여주는 실전 교훈.
- `prismatic/models/backbones/vision/dinosiglip_vit.py:43-58` — DINOv2(self-supervised 공간 특징) + SigLIP(언어-정렬 의미 특징)을 **융합**. OpenVLA 논문의 발견: 조작 태스크엔 단일 인코더보다 융합 백본이 유리.
- `vla-scripts/deploy.py:21-24,65-89` — 실물 로봇 인터페이스가 `POST /act {image, instruction} → {action}` 한 줄. 모델을 로봇에 얹는 최소 계약을 REST로 노출 — M3 프로젝트의 배포 패턴으로 바로 차용 가능.

## 5. 내 정의에 어떻게 반영할 것인가

- **정책 레이어 정의 구체화**: landscape §2에서 "VLA = 이미지+지시 → 동작"이라 적었는데, OpenVLA를 보면 그 실체는 **"사전학습 VLM + 동작 토큰화"** 라는 *얇은 어댑터* 구조다. 새 아키텍처가 아니라 LLM 재사용. 이 점을 정의에 추가.
- **대비축 발견**: OpenVLA(이산 토큰화·autoregressive) ↔ π0(연속 flow matching). 같은 "VLA"라도 동작 생성 방식이 갈린다 — M2 #2(π0) 정독 후 이 대비를 **ADR로 박제** 예정 ("왜 토큰화 vs flow matching").
- **M3 직결**: `deploy.py`의 REST `/act` 최소 계약 + LoRA 파인튜닝 = 개인이 사전학습 모델에 자기 데이터만 얹어 실험하는 진입로. 실물 제작 프로젝트의 SW 골격 후보.
- 관련 ADR: `docs/adr/0001-vla-action-representation.md` (M2 #2 이후 작성 — 현재 미작성)

---

## 메타
- 수집일: 2026-06-09
- 논문/링크: [arXiv 2406.09246](https://arxiv.org/abs/2406.09246) · [HF: openvla/openvla-7b](https://huggingface.co/openvla/openvla-7b) · repo README (클론 동봉)
- 소요 시간: ~60분 (코드 정독 위주)
- 다음에 볼 레포 후보: Physical-Intelligence/openpi (π0 — flow matching 대비), Open X-Embodiment (OXE 데이터 포맷 RLDS 심화)
