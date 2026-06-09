# 0001 — VLA 동작 표현(action representation)의 분류 정의

- Status: Accepted (2026-06-09)
- 근거 reference: openvla/openvla(#1), Physical-Intelligence/openpi(#2), tonyzhaozh/act(#3), OXE(#4), VLA 서베이(#5)

## Context

M2에서 VLA 4개를 코드 수준으로 정독한 결과, "VLA = 이미지+지시 → 동작"이라는 평면적 정의로는 모델 간 핵심 차이를 못 잡는다는 걸 확인했다. 같은 VLA라도 **동작을 어떻게 표현·생성하는가**에서 셋으로 갈렸고, 손실 함수까지 모두 달랐다:

| 모델 | 동작 표현 | 생성 방식 | 손실 | 추론 비용 | 근거 |
|------|----------|----------|------|----------|------|
| OpenVLA | **이산 토큰** (256-bin → 어휘 끝) | autoregressive 단일 패스 | cross-entropy | 1 forward | `action_tokenizer.py:36,45` |
| π0 | **연속 벡터** | flow matching ODE 적분 | MSE(velocity) | N=10 forward | `pi0.py:195-279` |
| ACT | **연속 청크** | CVAE 직접 회귀 단일 패스 | L1 + KL | 1 forward | `policy.py:27-37` |

공통 모티프: ACT·π0 모두 단일 step이 아닌 **action chunking**(동작 시퀀스 예측)으로 compounding error를 완화. 백본은 수렴(VLM: Prismatic/PaliGemma) 하나 "동작을 만드는 위치"가 분기 — OpenVLA는 LLM 헤드 재사용, π0는 별도 action expert, ACT는 전용 CVAE 디코더.

서베이(#5)는 이와 직교하는 1차축으로 **monolithic vs hierarchical**을 제시 — 본 4개는 전부 monolithic.

## Decision

이 레포에서 VLA를 **2D 좌표**로 정의·분류한다:

1. **구조축 (서베이)**: monolithic(single/dual-system) ↔ hierarchical(계획·실행 분리)
2. **동작표현축 (직접 정독)**: 이산 토큰화 ↔ flow/diffusion ↔ 직접 회귀(CVAE 등)

신규 VLA reference는 정독 전 이 2D 좌표에 먼저 위치시킨다(routing 기준). landscape §2의 "VLA" 정의는 이 좌표계를 포함하도록 갱신한다.

## Consequences

- **(+)** 모델 비교가 구조화됨. "왜 이 모델은 추론이 느린가" 같은 질문이 동작표현축으로 즉답된다(π0=N-step ODE).
- **(+)** M3 프로젝트 설계 시 동작표현 선택의 트레이드오프가 명시적: 실시간 고주파 제어면 단일 패스(OpenVLA/ACT), 멀티모달 동작 분포 표현력이면 flow matching(π0).
- **(−)** 본 정의는 monolithic 계열 4개에 기반 — **hierarchical·world-model 통합 VLA는 미검증**. 해당 영역 정독 시 좌표계 보강/재정의 필요(이 ADR supersede 가능).
- **다음**: hierarchical VLA 1편 + world-model 통합 VLA 1편 정독을 M2 확장 또는 M3 사전조사 후보로 둔다.
