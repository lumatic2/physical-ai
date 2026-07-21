# Changeset: GEN4 failure coverage gate

- Status: completed
- Target: ROADMAP `GEN4` step-5 — `failure-coverage-gate`

## Scope

- `coverage_gate.py`: 27개 non-success의 policy/suite/pattern 분모와 evidence coverage를 재계산한다.
- `failure-coverage-report.json`: specific pattern과 unknown을 함께 공개하는 GEN4 정본이다.
- `test_coverage_gate.py`: 분모 누락, unknown 은폐, root-cause·독립 인간·실물 로봇 과장 claim을 거부한다.

## Verification

- [x] 27/27이 evidence-backed pattern 또는 unknown이다.
- [x] policy·suite별 breakdown의 합이 원 분모와 같다.
- [x] unknown 21/27을 coverage metric으로 보존한다.
- [x] root cause와 hidden reasoning 진단으로 relabel할 수 없다.
- [x] reviewer calibration의 비독립성 disclosure를 보존한다.

## Result

27개 timeout을 누락 없이 집계했다. 관측 가능한 `no_progress`는 6개(22.2%), 활성 규칙으로 더 구체화할 수 없는 `unknown`은 21개(77.8%)다. OpenVLA는 5/20, π0.5는 1/1이며 goal 5/7, object 0/8, spatial 1/6으로 각각 no_progress/unknown이다.

분모 누락, unknown 은폐, root cause·planning/perception failure·독립 인간·실물 로봇 주장 failure probe를 모두 거부했다.
