# M3 프로젝트 아이디어

> M1·M2 정독에 뿌리내린 프로젝트 후보. 방향: **SW 먼저**(RTX 5090 32GB 로컬 활용, 구매 없이 시작) → 저가 로봇팔(~$200-400)로 점진 확장.
> 각 아이디어는 `references/*/ANALYSIS.md` 의 구체 발견에 연결됨.

## 선정 기준

- 구매 없이 **지금 바로** 시작 가능 (로컬 GPU)
- M2에서 본 코드를 직접 손에 익힘 (추상 이해 → 실행 지식)
- 나중에 저가 HW로 자연스럽게 확장되는 경로

## 후보 5

| # | 아이디어 | 뿌리 | HW | 난이도 | 확장성 |
|---|---------|------|----|-------|-------|
| 1 | **VLA 로컬 추론 서버 + 시뮬 평가** — OpenVLA를 5090에 올려 `deploy.py` REST 띄우고 LIBERO 벤치에서 success rate·latency 측정 | OpenVLA `deploy.py:65-89` | 불필요 | 중 | ★★★ (HW의 SW 골격) |
| 2 | **동작표현 3축 벤치마크** — OpenVLA(토큰)·π0(flow)·ACT(CVAE)를 동일 시뮬 태스크서 latency·정확도 비교, ADR 0001 실측 | #1·#2·#3 손실/추론 | 불필요 | 상 | ★★ (글·논문성) |
| 3 | **나만의 RLDS 미니 파이프라인** — 웹캠+간단 조작 데이터를 RLDS로 만들어 OpenVLA LoRA 파인튜닝 | OXE `RLDS` + OpenVLA finetune | 웹캠 | 상 | ★★★ |
| 4 | **저가 단일팔 + ACT** — LeRobot SO-100류(~$200) 단일 로봇팔로 ACT 모방학습, ALOHA 축소판 | ACT `policy.py` | 구매 | 상 | ★★★ (실물 도달) |
| 5 | **VLA "play" 데모** — 웹캠 이미지+자연어 지시 → OpenVLA 동작벡터 예측을 시각화 (로봇 없이 손맛) | OpenVLA `predict_action` | 웹캠 | 하 | ★ (데모) |

## 권장 시퀀스

```
[1] VLA 로컬 추론 서버 + 시뮬 평가   ← 첫 experiment (SW 골격 + 측정 가능)
      │  (성공 시 deploy.py REST 패턴 손에 익음)
      ├─→ [5] play 데모  (가벼운 곁가지, 빠른 손맛)
      ├─→ [2] 3축 벤치마크  (π0·ACT 추가, ADR 0001 실증)
      └─→ [3] RLDS 파인튜닝 → [4] 저가팔에 deploy  ← 실물 도달
```

**첫 experiment 권장: #1**. 이유:
- 구매 0, 측정 가능한 성공 기준(LIBERO success rate, 추론 latency)
- `deploy.py` REST `/act` 패턴은 이후 #4 실물 로봇 구동의 SW 계약과 동일 — 한 번 익히면 재사용
- 2·3·5가 전부 이 위에 선다

## 리스크 (정직하게)

- OpenVLA 7B 로딩 + flash-attn + LIBERO 시뮬 환경 구성은 Windows에서 CUDA·의존성 마찰 가능 → experiment는 **mock(작은 모델/더미 입력) 먼저, real 다음** (harness 원칙)
- 시뮬(LIBERO)은 Linux 친화적 — WSL2 또는 `ssh m4`(맥) 경로도 검토 대상
