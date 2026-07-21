# PLAN — LIVE4 실행 기록과 replay 승격

Status: pending current approval — 2026-07-21 계획 보강

## Objective → Horizon → Milestone
- Objective: 직접 실행 결과를 재현 가능한 산출물로 확인한다.
- Horizon: `plans/horizons/live-instruction-execution-lab.md`
- Milestone: live session stream을 LAB canonical episode/event로 원자적으로 승격하고 replay와 연결한다.

## Scope Boundary
- 포함: session recorder, partial recovery, canonical writer, live↔replay equivalence, representative sessions.
- 제외: public gallery, new dataset format, failed partial을 canonical로 위장하기.
- Start gate: LIVE3 final report PASS.
- Execution mode: continuous
- Stop only: completed, blocked, decision_required, risk_gate, secret_required, user_stopped.
- Rollback/cleanup: partial spool은 quarantine 후 명시적 cleanup하며 canonical artifact는 content-addressed다.

## planning_gate
```yaml
planning_gate:
  team_validation_mode: manual-pass
  scope_posture: reduction
  delegation_decision: {remote_background_agents: skip, reason: "stream과 canonical episode 사이 원자적 경계를 검증한다."}
  skeptic: "live 화면과 저장 결과의 차이를 숨기지 않는다."
```

## 스캐폴딩 결정
- source-of-truth: completed session ledger가 LAB LeRobot episode와 causal event promotion을 승인한다.
- 검증: crash recovery, byte/hash linkage, live-replay summary equivalence를 사용한다.
- 배포/운영: local recording만 수행하고 GEN/LAB public bundle은 LIVE5가 생성한다.
- storage: bounded spool→validate→atomic promote; canonical frame data 중복 금지.
- 관측: dropped frames, partial/recovered status, promotion id와 artifact hashes를 기록한다.
- 검토 후 제외: stream raw dump를 곧바로 canonical로 취급, silent frame interpolation.

## 결정 로그
- status: resolved
- aborted/error session도 evidence로 보존하되 canonical promotion 조건과 outcome을 명시한다.

## Step 트리
- [ ] **step-1 — bounded-session-recorder**
  - Artifact: stream envelope와 binary camera를 ordered spool에 기록하는 recorder.
  - Files: `experiments/158-session-recording-promotion/recorder/`, tests, changeset.
  - Dependencies: 없음
  - Verify: bounded disk/queue와 session-complete index가 일치한다.
  - Failure probe: unbounded spool, cross-session append, missing close marker가 FAIL한다.
  - Commit: changeset 1 — bounded live session recorder.
- [ ] **step-2 — crash-and-partial-recovery**
  - Artifact: process kill/power-loss fixture에서 partial을 quarantine/recover하는 contract.
  - Files: recovery module/fixtures/report, changeset.
  - Dependencies: step-1
  - Verify: recovered frames keep ordering/hash and incomplete outcome stays explicit.
  - Failure probe: partial→success promotion, silent frame fill, duplicate recovery가 FAIL한다.
  - Commit: changeset 2 — partial recording recovery.
- [ ] **step-3 — canonical-episode-promotion**
  - Artifact: valid session을 LAB episode/provenance와 source-tagged VLM/VLA/controller event stream으로 변환하는 atomic promoter.
  - Files: promoter/schema adapter/tests, changeset.
  - Dependencies: step-2
  - Verify: camera/state/action/instruction/outcome and source links pass LAB validators.
  - Failure probe: missing executed action, wrong policy revision, local path leak가 FAIL한다.
  - Commit: changeset 3 — canonical session promotion.
- [ ] **step-4 — live-replay-equivalence**
  - Artifact: live summary와 promoted replay의 frame/outcome/event/hash linkage report.
  - Files: equivalence verifier/negative fixtures, changeset.
  - Dependencies: step-3
  - Verify: sampled timestep and final outcome resolve identically within declared media tolerance.
  - Failure probe: frame drop 숨김, outcome relabel, event reorder가 FAIL한다.
  - Commit: changeset 4 — live-to-replay equivalence.
- [ ] **step-5 — representative-session-bundle**
  - Artifact: two policy의 complete/abort/error representative sessions와 LIVE4 report.
  - Files: `verify/canonical/`, bundle report, changeset, final report.
  - Dependencies: step-1, step-2, step-3, step-4
  - Verify: all session types promote or quarantine by contract and clean replay PASS.
  - Failure probe: failure omission, invalid canonical promotion, stale artifact ref가 FAIL한다.
  - Commit: changeset 5 — verified session recording promotion.

## Verification / DoD
- valid live session은 canonical replay로 승격되고 partial/failure도 숨김 없이 evidence로 연결된다.
