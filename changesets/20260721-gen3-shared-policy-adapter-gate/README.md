# Changeset: GEN3 shared policy adapter gate

- Status: completed
- Target: ROADMAP `GEN3` step-2 — `shared-policy-adapter-gate`

## Scope

- `shared-adapter-contract.json`: 공통 captured observation/result와 정책별 model input·transform·chunk·replan 차이 고정.
- `verify_adapter_parity.py`: GEN1 60 paired keys/120 runs와 registry의 adapter revision을 lossless 대조.
- `test_verify_adapter_parity.py`: hidden transform, sign/scale drift, wrist relabel, timing omission, unpaired cell 변이 검사.
- `verify/adapter-parity-report.json`: held-constant와 policy-specific surface를 함께 노출.

## Contract

| 항목 | OpenVLA | π₀.₅-LIBERO |
|---|---|---|
| model input | instruction + main camera | instruction + main + wrist + 8D state |
| raw/executed output | 7 → 1×7 | 10×32 → 10×7 |
| gripper | 0..1→sign 뒤 LIBERO 반전 | dataset absolute gripper, 추가 변환 없음 |
| cadence | 매 step 요청 | 10개 예측 중 5 step 실행 후 재계획 |

공통으로 고정되는 것은 task, initial state, LIBERO revision, seed, max steps, terminal/result schema다. 입력과 action interface가 동일하다는 주장은 하지 않는다.

## Verification

- [x] 60 paired task-state keys와 120 policy runs 전수 대응.
- [x] OpenVLA adapter revision `eb1ae763…`와 π₀.₅ revision `13bafd5d…` 고정.
- [x] main/wrist camera source key와 model-input/observer-only 역할 대조.
- [x] 7D environment action semantics와 request latency 누적 필드 고정.
- [x] hidden crop과 OpenVLA gripper normalization 누락이 FAIL.
- [x] wrist relabel, timing omission, unpaired cell이 FAIL.

## Result

두 정책이 동일한 60 task-state 분모와 terminal evidence 외피를 공유하면서도 서로 다른 관측 입력과 행동 생성 cadence를 숨기지 않는 비교 경계를 만들었다. 이 gate는 adapter fairness를 입증하며 π₀.₅ 60개 rollout 결과는 아직 포함하지 않는다.

## Sources

- [OpenVLA LIBERO evaluation](https://github.com/openvla/openvla/blob/main/experiments/robot/libero/README.md) (접근일: 2026-07-21)
- [OpenPI LIBERO policy adapter](https://github.com/Physical-Intelligence/openpi/blob/15a9616a00943ada6c20a0f158e3adb39df2ccac/src/openpi/policies/libero_policy.py) (접근일: 2026-07-21)
- [OpenPI LIBERO evaluation client](https://github.com/Physical-Intelligence/openpi/blob/15a9616a00943ada6c20a0f158e3adb39df2ccac/examples/libero/main.py) (접근일: 2026-07-21)
