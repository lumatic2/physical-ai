# PLAN — LIVE2 안전한 실험 session 제어

Status: approved — 2026-07-21 사용자 승인; Horizon 전체 연쇄 실행

## Objective → Horizon → Milestone
- Objective: 언어 지시를 이해하고 행동을 생성·실행하는 과정을 관찰한다.
- Horizon: `plans/horizons/live-instruction-execution-lab.md`
- Milestone: supported instruction과 실행 레인을 선택해 pause/stop/timeout/action limit가 보장되는 session을 실행한다.

## Scope Boundary
- 포함: task catalog, session state machine, environment lifecycle, action safety, operator controls, fault gate.
- 제외: arbitrary BDDL generation, browser rendering, canonical recording.
- Start gate: LIVE1 final report PASS.
- Execution mode: continuous
- Stop only: completed, blocked, decision_required, risk_gate, secret_required, user_stopped.
- Rollback/cleanup: session 종료 시 env/server client를 닫고 ports·GPU lease를 해제한다.

## planning_gate
```yaml
planning_gate:
  team_validation_mode: manual-pass
  scope_posture: reduction
  delegation_decision: {remote_background_agents: skip, reason: "하나의 state machine과 safety owner를 검증한다."}
  skeptic: "지원하지 않는 자유 지시를 실행 가능한 task처럼 보이지 않는다."
```

## 스캐폴딩 결정
- source-of-truth: GEN task catalog, LAB2 VLM skill allowlist와 `physical-ai-experiment-session-v1` state machine이다.
- 검증: transition property tests, real LIBERO session smoke와 fault injection을 사용한다.
- 배포/운영: local controller process; browser나 public network가 action 권한을 직접 갖지 않는다.
- safety: max steps, action bounds, heartbeat, timeout과 operator abort가 policy보다 우선한다.
- 관측: instruction source, task id, execution lane, model/component revision, transition, stop reason과 proposed/executed action count를 기록한다.
- 검토 후 제외: unsupported free-form task mapping, background unattended session, retry 숨김.

## 결정 로그
- status: resolved
- canonical instruction과 사전 승인 paraphrase만 실행하고 나머지는 거부한다.
- 검증 행렬은 두 task×canonical/paraphrase×OpenVLA/π₀.₅/Qwen3-VL→skill의 12 session으로 고정한다.

## Step 트리
- [ ] **step-1 — supported-instruction-catalog**
  - Artifact: task id, canonical instruction, allowed paraphrase와 environment binding catalog.
  - Files: `experiments/156-safe-experiment-session/instructions.json`, validator/tests, changeset.
  - Dependencies: 없음
  - Verify: 모든 instruction이 GEN task와 BDDL hash로 resolve된다.
  - Failure probe: ambiguous/unknown prompt와 task drift가 `unsupported_instruction`이다.
  - Commit: changeset 1 — supported instruction catalog.
- [ ] **step-2 — session-state-machine**
  - Artifact: created→ready→running↔paused→completed/aborted/error transition contract.
  - Files: session schema/controller/tests, changeset.
  - Dependencies: step-1
  - Verify: allowed transition과 cleanup invariant가 property tests를 통과한다.
  - Failure probe: double start, resume after abort, completion without outcome이 FAIL한다.
  - Commit: changeset 2 — experiment session state machine.
- [ ] **step-3 — action-safety-envelope**
  - Artifact: action clamp/reject, max steps, rate, timeout와 heartbeat enforcement.
  - Files: safety controller/fixtures/report, changeset.
  - Dependencies: step-2
  - Verify: valid action은 lossless, invalid action은 실행 전 reject되고 source가 남는다.
  - Failure probe: NaN, bound/rate violation, stale action chunk가 FAIL한다.
  - Commit: changeset 3 — session action safety.
- [ ] **step-4 — operator-control-fault-smoke**
  - Artifact: pause/resume/abort/policy crash/network loss를 실제 session에서 검증한 evidence.
  - Files: fault runner, canonical logs, changeset.
  - Dependencies: step-3
  - Verify: 모든 fault에서 env action이 제한 시간 안에 정지하고 stop reason이 일치한다.
  - Failure probe: abort 후 action, lost heartbeat 자동 resume, hidden retry가 FAIL한다.
  - Commit: changeset 4 — operator and fault controls.
- [ ] **step-5 — twelve-session-safety-gate**
  - Artifact: 두 task×두 instruction form×세 실행 레인의 12 operator-controlled session 통합 report.
  - Files: run manifest, verify report, changeset, final report.
  - Dependencies: step-1, step-2, step-3, step-4
  - Verify: 12/12 terminal/cleanup, supported instruction, lane/source/action/stop provenance PASS.
  - Failure probe: missing session, wrong task binding, unrecorded stop이 FAIL한다.
  - Commit: changeset 5 — twelve-session safety gate.

## Verification / DoD
- operator가 선택한 지원 지시와 policy session이 fail-closed safety controls 아래 실제 실행된다.
