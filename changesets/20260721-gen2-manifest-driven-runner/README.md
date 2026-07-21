# Changeset: GEN2 manifest-driven runner

- Status: completed
- Target: ROADMAP `GEN2` step-1 — `manifest-driven-runner`

## Scope

- `runner-config.json`: GEN1 네 정본과 기존 OpenVLA orchestrator의 content hash, suite 순서와 max step 고정.
- `run_baseline.py`: 60 cell 검증, deterministic dry-run, exact single-cell invocation.
- `test_run_baseline.py`: 분모·순서·selector·revision drift 회귀 검사.
- `verify/dry-run-report.json`: 60개 실행 spec의 canonical dry-run.

## Contract

- Source of truth: GEN1의 OpenVLA denominator 60개만 선택한다.
- Ordering: `Spatial → Object → Goal`, 각 suite 안에서 task id → state index 순서다.
- Execution: 한 command는 정확히 task 1개, initial state 1개와 suite별 exact checkpoint revision만 실행한다.
- Claim boundary: dry-run은 identity/command 검증이며 rollout 또는 성능 결과가 아니다.

## Verification

- [x] dry-run 60개, unique run key 60개, suite별 20개 PASS.
- [x] 첫 cell Spatial task-00/state-00, 마지막 cell Goal task-09/state-04.
- [x] ordered run-key hash `63080ad832cfd84c27fd485b324081b0babaa789e8cb0b2c4ec734b56005abf3`.
- [x] manifest 밖 task/state selector가 subprocess 전에 exit 2.
- [x] denominator source hash와 checkpoint/environment revision drift가 FAIL.

## Result

GEN1의 60개 OpenVLA cell이 기존 server/client orchestrator의 단일-cell 명령으로 lossless 변환된다. canonical report는 로컬 절대경로·cache·secret을 포함하지 않으며 실제 rollout은 아직 실행하지 않았다.

## Sources

- [LIBERO frozen revision](https://github.com/Lifelong-Robot-Learning/LIBERO/tree/8f1084e3132a39270c3a13ebe37270a43ece2a01) (접근일: 2026-07-21)
- [OpenVLA LIBERO evaluation](https://github.com/openvla/openvla/blob/main/experiments/robot/libero/README.md) (접근일: 2026-07-21)
