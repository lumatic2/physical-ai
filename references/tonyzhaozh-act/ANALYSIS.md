# tonyzhaozh/act (ALOHA + ACT) 분석

> 시간 박스 90분. 클론: https://github.com/tonyzhaozh/act (2026-06-09 접근). 논문: [arXiv 2304.13705](https://arxiv.org/abs/2304.13705) (ALOHA 하드웨어 + ACT 알고리즘).

## 1. 한 줄 요약 / 무엇을 하는 하네스인가

**저가($20k) 양팔 원격조종 하드웨어(ALOHA) + 모방학습 알고리즘(ACT)**. ACT = Action Chunking with Transformers — 동작을 토큰화·확산 없이 **CVAE + DETR 트랜스포머로 동작 *청크*를 직접 L1 회귀**. 10분 시연으로 정밀 조작 학습. landscape의 🔧하드웨어/시스템 + 🧠정책이 한 레포에 묶인, 개인이 따라 만들 수 있는 가장 가벼운 진입점.

## 2. 디렉터리 지도 (핵심 폴더만)

```
act/
├── policy.py              # ★ ACTPolicy (CVAE 래퍼) / CNNMLPPolicy (베이스라인)
├── detr/
│   └── models/
│       ├── detr_vae.py    # ★ DETRVAE — CVAE 인코더 + 트랜스포머 디코더
│       ├── transformer.py # DETR 트랜스포머
│       └── backbone.py    # ResNet 비전 백본
├── imitate_episodes.py    # 학습/평가 루프
├── sim_env.py / ee_sim_env.py  # MuJoCo 시뮬 환경
├── record_sim_episodes.py # 시연 데이터 수집
└── constants.py           # 태스크·로봇 설정
```

## 3. 아키텍처 레이어 매핑 (로보틱스 — landscape §2 4레이어와 정렬)

| 레이어 | 위치 (파일:줄) | 내용 |
|--------|---------------|------|
| 입력·센서 (관측) | `detr_vae.py:56,81`, `policy.py:20-22` | 다중 카메라 RGB(ImageNet 정규화) + qpos(14-DoF 양팔 관절) |
| 인지·추론 | `detr/models/backbone.py`, `detr_vae.py:49-57` | ResNet 백본 → conv 투영 → DETR 트랜스포머 |
| 정책·액션 생성 | `detr_vae.py:34-76`, `policy.py:9-38` | CVAE: latent z(32-dim) + query embedding `num_queries`개로 동작 청크 회귀 |
| 학습·데이터 | `policy.py:27-34` | **L1 재구성 손실 + KL**(reconstruction + VAE 정규화). MSE 아님 |
| 하드웨어·배포 | `sim_env.py`, ALOHA 하드웨어(논문) | $20k 양팔 원격조종 리그 → 시연 수집 → 실시간 청크 실행 |

## 4. 인상 깊은 코드/패턴 (파일 경로 + 줄 번호 필수)

- `detr/models/detr_vae.py:47,54,72` — `num_queries`개의 query embedding으로 **동작 시퀀스 전체를 한 번에** 예측(action chunking). DETR의 "object query"를 "미래 동작 슬롯"으로 전용한 발상. 단일 step 예측의 compounding error를 청크로 완화.
- `policy.py:27-34` — 학습 손실 = `L1(action, a_hat) + kl_weight·KL`. **L1**(절대오차)을 동작 회귀에 씀 — 논문 발견: 동작엔 L2/MSE보다 L1이 안정적. π0(MSE velocity)·OpenVLA(cross-entropy)와 또 다른 손실 선택.
- `detr_vae.py:34-76`, `policy.py:37` — CVAE 구조: 학습 시 동작 시퀀스를 latent z로 인코딩, 추론 시 z=prior(0) 샘플 → 디코더가 동작 생성. 시연의 멀티모달성을 latent로 흡수.
- `detr_vae.py:58,69` — 로봇 상태 차원이 `14`로 하드코딩 = 양팔 7+7 관절. 이 레포가 **bimanual ALOHA 전용**으로 태어났음을 코드가 드러냄.

## 5. 내 정의에 어떻게 반영할 것인가

- **동작 표현 3번째 패러다임**: ACT(CVAE + 직접 L1 회귀, 단일 forward) — OpenVLA(이산 토큰)·π0(flow matching) 사이의 또 다른 축. 손실 함수(cross-entropy / MSE-velocity / L1)까지 셋이 모두 다름 → ADR의 비교축이 풍부해짐.
- **action chunking은 공통 모티프**: ACT·π0 모두 단일 step이 아닌 동작 *청크*를 예측. compounding error 완화가 로봇 정책의 공통 과제임을 확인 → landscape 용어표에 이미 있는 "action chunking"의 실증.
- **M3 직결 (가장 강함)**: ALOHA는 *하드웨어 BOM + 학습 코드*가 다 공개된 저가 진입점. 실물 제작 프로젝트라면 여기서 출발 가능. 단 14-DoF 양팔 전제라 단일 팔/저자유도로 축소 시 코드 수정 필요.
- 관련 ADR: `docs/adr/0001-vla-action-representation.md` (3자 비교에 ACT 포함)

---

## 메타
- 수집일: 2026-06-09
- 논문/링크: [arXiv 2304.13705](https://arxiv.org/abs/2304.13705) · [Mobile ALOHA arXiv 2401.02117](https://arxiv.org/abs/2401.02117)(후속)
- 소요 시간: ~45분
- 다음에 볼 레포 후보: Mobile ALOHA(전신 이동 조작), LeRobot(ACT/π0 통합 프레임워크)
