# PLAN — REAL3 실물 dataset과 sim 대응 과제

Status: approval-ready — 3-Horizon 연쇄 실행 승인 대기

## Objective → Horizon → Milestone
- Objective: simulation과 real claim을 같은 증거 계약으로 구분한다.
- Horizon: `plans/horizons/sim-real-so101-evidence-loop.md`
- Milestone: 50 teleop episode의 real dataset과 schema-compatible sim analogue를 만든다.

## Scope Boundary
- 포함: black-cube-to-zone task, object/target protocol, 50 real demonstrations, quality audit, sim analogue, schema comparison.
- 제외: physics 동일성, policy training, performance ranking, public UI.
- Start gate: REAL2 final report PASS.
- Execution mode: continuous
- Stop only: completed, blocked, decision_required, risk_gate, secret_required, user_stopped.
- Rollback/cleanup: raw dataset은 immutable version으로 보존하고 rejected episode도 audit index에 남긴다.

## planning_gate
```yaml
planning_gate:
  team_validation_mode: manual-pass
  scope_posture: reduction
  delegation_decision: {remote_background_agents: skip, reason: "한 physical setup의 순차 dataset capture와 audit이다."}
  skeptic: "sim과 real의 schema 공유를 physics fidelity로 과장하지 않는다."
```

## 스캐폴딩 결정
- source-of-truth: LeRobot real dataset revision, task protocol과 separate sim dataset revision이다.
- 검증: episode quality audit, task/reset checklist, schema/claim negative fixtures를 사용한다.
- 배포/운영: local/Hugging Face private-or-local storage; public release는 REAL5 gate 후다.
- task: black cube를 사전 표시한 target zone으로 이동하며 initial positions를 stratify한다.
- data: front/wrist camera, joint state, leader/executed action, timing, outcome와 rejection reason.
- 검토 후 제외: failed/rejected demo 삭제, sim frame을 real처럼 표기, data augmentation.

## 결정 로그
- status: resolved
- 50 accepted training episode를 목표로 하고 rejected attempts도 denominator audit에 남긴다.

## Step 트리
- [ ] **step-1 — real-task-reset-protocol**
  - Artifact: object/target/workspace, initial position strata, reset/outcome/safety checklist.
  - Files: `experiments/162-real-dataset-sim-analogue/task-contract/`, fixtures, changeset.
  - Dependencies: 없음
  - Verify: independent operator가 task/reset/success를 반복 판정한다.
  - Failure probe: ambiguous target, inconsistent reset, hidden assistance가 FAIL한다.
  - Commit: changeset 1 — real manipulation task contract.
- [ ] **step-2 — fifty-episode-capture**
  - Artifact: 50 accepted teleop LeRobot episodes와 complete attempt ledger.
  - Files: dataset manifest, capture logs/evidence, changeset.
  - Dependencies: step-1
  - Verify: 50 accepted unique episodes plus all rejected/retried attempts accounted.
  - Failure probe: duplicate episode, missing camera/action, discarded failure가 FAIL한다.
  - Commit: changeset 2 — real SO-101 training dataset.
- [ ] **step-3 — dataset-quality-audit**
  - Artifact: blur/drop/sync/action/reset/outcome coverage와 train split quality report.
  - Files: audit tool/report/negative fixtures, changeset.
  - Dependencies: step-2
  - Verify: every accepted episode passes thresholds or is replaced with traceable reason.
  - Failure probe: hidden replacement, success-only filtering, calibration revision mix가 FAIL한다.
  - Commit: changeset 3 — real dataset quality gate.
- [ ] **step-4 — simulation-analogue-task**
  - Artifact: same task semantics/result schema를 가진 MuJoCo/LIBERO analogue와 canonical episodes.
  - Files: sim task/runner/verify evidence, changeset.
  - Dependencies: step-3
  - Verify: task fields and episode schema map while claim level remains simulation.
  - Failure probe: real label, physics equivalence, unmatched action/state semantics가 FAIL한다.
  - Commit: changeset 4 — schema-compatible sim analogue.
- [ ] **step-5 — sim-real-schema-gate**
  - Artifact: shared/different fields, provenance and claim boundary를 대조한 REAL3 report.
  - Files: comparison schema/verifier/report, changeset, final report.
  - Dependencies: step-1, step-2, step-3, step-4
  - Verify: both datasets load through common top-level index without losing source-specific fields.
  - Failure probe: success rate direct ranking, sensor fabrication, source removal가 FAIL한다.
  - Commit: changeset 5 — sim-real evidence schema gate.

## Verification / DoD
- 50 quality-gated real episodes와 sim analogue가 공통 schema·다른 claim level로 검증된다.
