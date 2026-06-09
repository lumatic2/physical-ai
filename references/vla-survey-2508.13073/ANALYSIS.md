# VLA 서베이 (arXiv 2508.13073) 분석

> ⚠ 코드 레포가 아닌 **서베이 논문** — §2·§3을 "논문 구조"·"제시 taxonomy"로 적응. 클론 없음.
> 출처: [arXiv 2508.13073](https://arxiv.org/abs/2508.13073) (2026-06-09 WebFetch 접근).
> "Large VLM-based Vision-Language-Action Models for Robotic Manipulation: A Survey" — Rui Shao, Wei Li, Lingsen Zhang, Renshan Zhang, Zhiyang Liu, Ran Chen, Liqiang Nie.

## 1. 한 줄 요약 / 무엇을 하는 하네스인가

**대형 VLM 기반 VLA 모델을 조작(manipulation) 관점에서 체계화한 서베이**. 개별 모델(OpenVLA·π0 등) 정독으로 얻은 점들을 하나의 분류 지도로 묶어주는 *메타 레퍼런스* — M2의 #1~#4를 어디에 놓을지 좌표를 제공.

## 2. 논문 구조 (장 구성 — 코드 디렉터리 대체)

- 서론: VLM → VLA 전환 배경
- **아키텍처 paradigm 분류** (핵심): monolithic vs hierarchical
- 통합 영역: RL 통합 / training-free 최적화 / human video 학습 / world model 통합
- 향후 방향 5+종
- 정기 갱신 project page (GitHub)

## 3. 이 서베이가 제시하는 taxonomy (아키텍처 레이어 대체)

| 분류축 | 범주 | 본 레포의 #1~#4 매핑 |
|--------|------|---------------------|
| **Monolithic** | single-system | OpenVLA(#1) — VLM 헤드 재사용 단일 모델 |
| | dual-system | (landscape의 GR00T N1 System1/System2) |
| **Hierarchical** | 계획·실행을 해석가능한 중간표현으로 분리 | (고수준 계획 + 저수준 정책 분리형) |
| 동작 생성(서베이 외 본 분석 보강) | 토큰화 / flow matching / CVAE 회귀 | OpenVLA / π0(#2) / ACT(#3) |
| 데이터 토대 | cross-embodiment 통합 | OXE(#4) |

> 주의: 서베이 abstract 수준에서 monolithic/hierarchical 2축은 확인됐으나, "동작 표현(토큰화 vs diffusion vs flow)" 세부 분류는 본문 미확인 — 그 축은 본 레포 #1~#3 직접 정독으로 보강함(ADR 0001).

## 4. 인상 깊은 점 / 분류 통찰

- **monolithic ↔ hierarchical** 이 1차 분류축. 본 레포가 본 모델들(OpenVLA·π0·ACT)은 전부 monolithic 계열 — hierarchical(LLM 계획 + 별도 저수준 정책)은 아직 미정독. M2 이후 보강 후보.
- 서베이가 꼽는 **향후 방향 5종**: memory mechanism, 4D perception, efficient adaptation, multi-agent cooperation, 그리고 emerging capabilities. + 통합축: RL·training-free·human video·world model.
- "정기 갱신 project page" 존재 → 분야 속도가 빨라 정적 서베이의 한계를 저자도 인정.

## 5. 내 정의에 어떻게 반영할 것인가

- **분류 좌표계 획득**: 지금까지 "VLA = 이미지+지시→동작"이라는 평면적 정의에, **monolithic/hierarchical** 1차축 + **동작표현(토큰/flow/회귀)** 2차축을 더해 2D 지도로 승격. landscape §2 갱신 후보.
- **빈칸 발견 = 다음 학습 방향**: 본 레포는 monolithic만 봤다. hierarchical(계획-실행 분리) + world model 통합 VLA가 미정독 영역 — M2 확장 또는 M3 아이디어의 씨앗.
- **서베이를 입구로**: 향후 신규 모델은 이 2축 위에 먼저 위치시킨 뒤 정독하면 빠르다 — reference 분석의 routing 기준.
- 관련 ADR: `docs/adr/0001-vla-action-representation.md` (동작표현 2차축을 박제)

---

## 메타
- 수집일: 2026-06-09
- 링크: [arXiv 2508.13073](https://arxiv.org/abs/2508.13073)
- 소요 시간: ~25분 (abstract/구조 수준 — 전문 정독 아님)
- 한계: WebFetch가 abstract+구조까지만 추출. 동작표현 세부 taxonomy는 본문 PDF 정독 필요(미수행).
- 다음에 볼 후보: 서베이 project page의 hierarchical VLA 대표 1편, world-model 통합 VLA 1편
