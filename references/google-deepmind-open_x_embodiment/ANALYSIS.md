# google-deepmind/open_x_embodiment (OXE) 분석

> 시간 박스 90분. 클론: https://github.com/google-deepmind/open_x_embodiment (2026-06-09 접근). 논문: [arXiv 2310.08864](https://arxiv.org/abs/2310.08864).

## 1. 한 줄 요약 / 무엇을 하는 하네스인가

**모든 오픈 로봇 데이터를 단일 포맷(RLDS)으로 통합한 데이터셋 + cross-embodiment 정책(RT-X)**. 34개 랩·60개 데이터셋·22종 로봇·100만+ 궤적을 표준 RLDS episode 포맷으로 묶어, 여러 로봇에서 학습한 단일 정책이 양전이(positive transfer)함을 입증. 모델 레포라기보다 **L2 데이터 파이프라인의 사실상 표준** — OpenVLA·π0의 학습 데이터가 여기서 나온다.

## 2. 디렉터리 지도 (핵심 폴더만)

```
open_x_embodiment/
├── models/
│   ├── rt1.py                  # ★ RT-1/RT-1-X Jax/Flax 구현
│   ├── efficientnet.py         # 비전 백본
│   ├── film_conditioning.py    # ★ 언어→비전 FiLM 조건화
│   ├── token_learner.py        # 토큰 수 축소 (TokenLearner)
│   └── rt1_inference_example.py
└── colabs/
    ├── Open_X_Embodiment_Datasets.ipynb   # 데이터 시각화·배치 생성
    ├── Minimal_Training_Example.ipynb
    └── Minimal_example_..._RT_1_X_...ipynb # RT-1-X 추론 예제
```

## 3. 아키텍처 레이어 매핑 (로보틱스 — landscape §2 4레이어와 정렬)

| 레이어 | 위치 (파일:줄) | 내용 |
|--------|---------------|------|
| 입력·센서 (관측) | `README.md:27-31` | 작업공간 RGB 1장 + 태스크 문자열. 3Hz(333ms마다). 손목/depth 카메라 미사용 |
| 인지·추론 | `models/rt1.py:16-18,28-45`, `film_conditioning.py` | EfficientNet 비전 + FiLM 언어조건화 + TokenLearner + 트랜스포머 |
| 정책·액션 생성 | `README.md:33-35`, `rt1.py` | 7-DoF(x,y,z,roll,pitch,yaw,gripper) 이산화 동작. absolute/delta/velocity |
| 학습·데이터 | `README.md:11-21` | **RLDS episode 포맷**으로 60 데이터셋 통합. `tfds.load`로 소비 |
| 하드웨어·배포 | `colabs/*.ipynb`, gs:// 체크포인트 | TF/Jax 체크포인트 + colab 추론. cross-embodiment(22 로봇) |

## 4. 인상 깊은 코드/패턴 (파일 경로 + 줄 번호 필수)

- `README.md:5,11-13` — 핵심 기여는 모델이 아니라 **포맷 통일**: 이질적 랩 데이터를 전부 RLDS episode 포맷으로. "데이터 표준이 곧 생태계 레버리지"라는 명제의 실물. OpenVLA의 `oxe-magic-soup` 믹스가 이 위에 선다.
- `models/rt1.py:1-6` — RT-1(arxiv 2212.06817)의 Jax 재구현 + RT-X 개선. TF→Jax 포팅으로 가속기 학습 용이화.
- `models/film_conditioning.py` + `rt1.py:17` — **FiLM**으로 언어 지시를 비전 특징에 주입. VLA가 등장하기 전, 언어조건화의 고전적 방식 — OpenVLA/π0의 "언어를 토큰으로 LLM에 넣기"와 대비되는 이전 세대 설계.
- `models/token_learner.py` — 비전 토큰 수를 학습적으로 축소해 트랜스포머 비용↓. 실시간 제어(3Hz) 제약 하 효율화 패턴.

## 5. 내 정의에 어떻게 반영할 것인가

- **데이터 레이어가 모델만큼 중요**: landscape에서 "데이터 병목 → 시뮬·합성"이라 적었는데, OXE는 *실물 데이터의 통합·표준화*라는 다른 해법축. RLDS가 사실상 표준 포맷임을 정의에 추가.
- **cross-embodiment = 일반화의 토대**: 22 로봇 pooled 학습이 단일 로봇보다 낫다는 결과가 OpenVLA·π0의 "generalist" 전제를 떠받친다. landscape 용어 "cross-embodiment"의 실증 출처.
- **세대 구분선 발견**: OXE/RT-1(FiLM 언어조건화 + 이산 동작)은 VLA 직전 세대. RT-2→OpenVLA→π0로 "LLM 백본 흡수"가 일어난 변곡점을 데이터로 짚을 수 있음.
- **M3 관점**: 직접 만들 로봇의 데이터를 RLDS로 맞추면 기존 모델·툴체인(LeRobot 등)에 바로 붙는다. 데이터 포맷 선택이 곧 생태계 호환성.

---

## 메타
- 수집일: 2026-06-09
- 논문/링크: [arXiv 2310.08864](https://arxiv.org/abs/2310.08864) · [robotics-transformer-x.github.io](https://robotics-transformer-x.github.io/) · [RT-1 arXiv 2212.06817](https://arxiv.org/abs/2212.06817)
- 소요 시간: ~40분
- 다음에 볼 레포 후보: google-research/rlds(포맷 원류), LeRobot(데이터셋 허브 통합)
