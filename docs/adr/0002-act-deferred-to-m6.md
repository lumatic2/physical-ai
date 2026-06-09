# 0002 — ACT 동작표현 실측은 M4(비교 벤치) 아닌 M6(실물 모방학습)으로

- Status: Accepted (2026-06-10)
- 근거 reference: tonyzhaozh/act(#3), Physical-Intelligence/openpi(#2), openvla/openvla(#1)
- 관련: [[0001-vla-action-representation]] (3축 정의), M4 Track C 조사 게이트

## Context

M4 완료 기준은 "최소 2모델 결과표"이고, ADR 0001은 동작표현 3축(이산 토큰 / flow-matching chunk / CVAE chunk)을 정의했다.
세 번째 축인 **ACT(CVAE 연속 청크)**를 LIBERO에서 OpenVLA와 함께 실측해 3축을 모두 채우는 것이 자연스러운 욕심이었다.

Track C 조사 게이트(2026-06-10)에서 ACT의 LIBERO 실측 가능성을 확인한 결과:

- ACT(tonyzhaozh/act)는 **ALOHA 전용**이다. 동봉 sim 환경은 Transfer Cube·Bimanual Insertion(14-dim 양팔 joint)뿐이며,
  LIBERO 지원·기성 체크포인트가 **전무**하다 (`README.md` "2 simulated environments: Transfer Cube and Bimanual Insertion", 접근 2026-06-10).
- LIBERO에서 ACT를 돌리려면 데이터 변환(`modified_libero_rlds` → ACT hdf5) + **suite당 밑바닥 훈련**(GPU-시간)이 필요하다.
  이는 "기성 체크포인트 드롭인 → 1런 비교"라는 M4의 범위를 벗어나는 별도 훈련 프로젝트다.
- 반면 π0.5는 LIBERO finetuned 체크포인트(`pi05_libero`)가 공개돼 즉시 inference 가능 → M4 2번째 정책으로 적합.

또한 핸드오프 로드맵 M6는 이미 "SO-100류 저가 로봇팔 + ACT 모방학습 sim→real"을 계획하고 있다 — ACT의 강점(실물 모방학습)이 발휘되는 자리다.

## Decision

**ACT의 경험적 LIBERO 실측을 M4에서 하지 않는다.** 대신:

1. **M4**: ACT는 ADR 0001의 *개념적* 3번째 축(CVAE 연속 청크)으로 **인용만** 한다. M4 비교표는
   **이산 토큰(OpenVLA) vs flow-matching chunk(π0.5)** 2점 실측으로 구성한다.
2. **M6**: ACT의 경험적 역할을 실물(SO-100 + 모방학습 sim→real)로 이전한다. LIBERO 위 ACT 훈련은 추진하지 않는다
   (저가 실물 팔에서의 모방학습이 ACT 본래 용도이자 더 가치 있는 실측).

## Consequences

- **(+)** M4 범위가 "기성 체크포인트 2개 비교"로 유지됨 — suite당 ACT 훈련(수 GPU-시간)이라는 범위 폭발을 회피.
- **(+)** ADR 0001의 3축이 실측으로 깨지지 않음: 2축은 M4에서 LIBERO로, 3번째(ACT)는 M6에서 실물로 — 각 동작표현을
  *가장 적합한 무대*에서 실측하게 됨(ACT를 억지로 LIBERO에 올리는 것보다 정직).
- **(−)** M4 결과표는 3축 전부가 아닌 2축 비교 — "동일 벤치 위 3축 동시 비교"라는 이상적 그림은 미달. ADR 0001은 여전히
  ACT 항목이 코드 인용 기반(실측 아님)으로 남는다.
- **되돌림 조건**: LIBERO finetuned ACT 체크포인트가 공개되거나(커뮤니티), M4 일정에 여유가 크면 이 결정을 supersede하고
  M4에서 ACT-LIBERO를 추가할 수 있다.
