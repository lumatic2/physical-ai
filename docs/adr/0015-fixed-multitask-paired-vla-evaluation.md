# ADR 0015 — 고정 다과제·쌍대 VLA 평가

- 상태: proposed
- 날짜: 2026-07-21

## 맥락

LAB3는 한 LIBERO 과제의 실제 OpenVLA와 VLM→skill 증거를 공개했지만, 단일 과제는 정책의 일반화나 cherry-pick 부재를 입증하지 못한다. 전체 LIBERO-130을 바로 실행하면 compute와 검토 비용이 커지고, suite별 checkpoint 차이를 숨긴 단일 순위표는 공정하지 않다.

## 결정

- LIBERO Spatial/Object/Goal에서 각 4개 task와 task별 initial state 5개를 사전 고정한다.
- 현재 OpenVLA와 π₀.₅-LIBERO를 policy family로 비교하되 suite/checkpoint/revision/action adapter를 compatibility registry에 공개한다.
- 정책별 60 episode를 동일 result contract로 기록하고 paired aggregate에서 canonical episode까지 추적한다.
- 실패는 관측 가능한 양상만 분류하고 증거가 부족하면 `unknown`을 사용한다.
- 공개 화면은 LAB3 replay를 재사용하며 새 backend와 상시 GPU inference를 추가하지 않는다.

## 결과

두 정책을 완전히 같은 모델로 가장하지 않으면서 task·initial state·result denominator를 고정할 수 있다. 비용은 120 canonical rollout과 두 inference stack의 유지이지만, 단일 데모보다 강한 외부 검증 증거가 된다.

## 근거

- https://github.com/Lifelong-Robot-Learning/LIBERO (접근일: 2026-07-21)
- https://github.com/openvla/openvla (접근일: 2026-07-21)
- https://github.com/Physical-Intelligence/openpi (접근일: 2026-07-21)
- `research/2026-07-21-multitask-generalization-lab-policy-evaluation.md`
