# Changeset: GEN3 fairness and claim gate

- Status: completed
- Target: ROADMAP `GEN3` step-5 — `fairness-and-claim-gate`

## Scope

- `fairness_gate.py`: exact checkpoint·adapter·denominator·retry/exclusion·paired result를 한 reviewer report로 검증한다.
- `fairness-claim-contract.json`: 필수 disclosure와 허용/금지 claim 경계를 고정한다.
- `fixtures/invalid-fairness-claims.json`: general winner, same checkpoint, hidden exclusion/retry 변이를 정의한다.
- `test_fairness_gate.py`: source/revision drift와 claim 과장을 거부한다.
- `verify/fairness-report.json`: GEN3 spec/quality verdict와 provenance 정본.
- GEN3 최종 보고서: actual execution·paired statistics·한계·재현 명령을 완료 의식으로 묶는다.

## Contract

- 비교의 공통점: LIBERO revision, 12 task×5 state, seed/max step, terminal evidence schema.
- 비교의 차이: checkpoint topology, model input, preprocessing, action horizon, gripper transform, replan cadence.
- retries: infrastructure attempt를 policy result와 합치지 않고 두 정책의 총 attempt를 공개한다.
- claims: 고정 slice의 관측 수치만 허용하며 일반적 winner·동일 checkpoint/input·실물 성능을 금지한다.

## Verification

- [x] 두 policy의 exact checkpoint·adapter provenance를 registry와 대조.
- [x] 60 included pairs, exclusion/unmatched 0과 두 retry history 공개.
- [x] raw count·difference·interval·suite breakdown이 paired report와 일치.
- [x] required disclosure와 allowed claim이 모두 evidence pointer를 가짐.
- [x] general winner·same checkpoint·hidden exclusion/retry·revision drift가 FAIL.
- [x] spec/quality verdict, CLI smoke, tests, Ruff와 diff gate PASS.

## Result

GEN3 fairness report는 60 planned/included pairs, exclusion 0, unmatched 0을 확인했다. OpenVLA는 suite별 checkpoint 3개·instruction+main camera·1×7 action·매 step 재계획이며 총 61 attempts 중 infrastructure 1건이다. π₀.₅는 단일 snapshot `11e0f560…`·instruction+main+wrist+8D state·10×7 chunk·5 step 재계획이며 총 62 attempts 중 infrastructure 2건이다.

두 adapter를 동일하다고 부르지 않고 공통 denominator/result envelope만 같다고 판정했다. allowed claim 3개는 raw count·paired difference·suite breakdown의 evidence pointer를 가지며, general winner·same checkpoint/input·real robot·hidden reasoning 표현은 금지한다. actual report는 spec/quality `pass/pass`다.

## Sources

- [OpenVLA](https://github.com/openvla/openvla) (접근일: 2026-07-21)
- [OpenPI exact revision](https://github.com/Physical-Intelligence/openpi/tree/15a9616a00943ada6c20a0f158e3adb39df2ccac) (접근일: 2026-07-21)
- [LIBERO exact revision](https://github.com/Lifelong-Robot-Learning/LIBERO/tree/8f1084e3132a39270c3a13ebe37270a43ece2a01) (접근일: 2026-07-21)
