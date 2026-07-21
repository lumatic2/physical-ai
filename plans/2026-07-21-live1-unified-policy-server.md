# PLAN — LIVE1 통합 policy server 계약

Status: approval-ready — 3-Horizon 연쇄 실행 승인 대기

## Objective → Horizon → Milestone
- Objective: 정책을 직접 실행하고 전 과정을 관찰한다. (`OBJECTIVE.md`)
- Horizon: 지시를 바꿔 실행하는 로컬 피지컬 AI 실험실. (`plans/horizons/live-instruction-execution-lab.md`)
- Milestone: OpenVLA와 π₀.₅를 동일 localhost request/result/stop 계약으로 제공한다.

## Scope Boundary
- 포함: WebSocket envelope, exact model adapter, health/heartbeat, latency, fail-closed stop, contract gate.
- 제외: browser UI, session orchestration, recording, public backend.
- Start gate: GEN Horizon final report PASS.
- Execution mode: continuous
- Stop only: completed, blocked, decision_required, risk_gate, secret_required, user_stopped.
- Rollback/cleanup: 두 server env/cache는 repo 밖에 두고 schema·adapter·verify evidence만 revert 가능하게 추적한다.

## planning_gate
```yaml
planning_gate:
  team_validation_mode: manual-pass
  scope_posture: reduction
  delegation_decision: {remote_background_agents: skip, reason: "두 adapter를 한 envelope에 순차 통합한다."}
  qa: "malformed request, stale heartbeat, model crash와 wrong revision을 fail-closed로 검사한다."
```

## 스캐폴딩 결정
- source-of-truth: `physical-ai-policy-server-v1` envelope와 exact policy registry다.
- 검증: schema/semantic tests, real checkpoint smoke, heartbeat/kill fault injection을 사용한다.
- 배포/운영: localhost-only WSL processes; 외부 listen·Vercel backend 없음.
- runtime: OpenVLA와 openpi는 격리 env, thin client만 공유한다.
- 관측: request id, policy revision, preprocess revision, latency와 action chunk shape를 기록한다.
- 검토 후 제외: training, auth, multi-user queue, public network exposure.

## 결정 로그
- status: resolved
- server는 inference만 소유하고 action execution/stop은 session controller가 소유한다.

## Step 트리
- [ ] **step-1 — policy-server-envelope**
  - Artifact: observation/prompt/action/error/health WebSocket schema와 reference client.
  - Files: `experiments/155-unified-policy-server/schema/`, client/tests, changeset.
  - Dependencies: 없음
  - Verify: valid round-trip과 version negotiation이 PASS한다.
  - Failure probe: unknown version, missing camera/state, oversized payload가 FAIL한다.
  - Commit: changeset 1 — policy server envelope.
- [ ] **step-2 — openvla-server-adapter**
  - Artifact: exact OpenVLA checkpoint를 envelope로 serving하는 adapter.
  - Files: server adapter/config/verify evidence, changeset.
  - Dependencies: step-1
  - Verify: GEN sample observation에서 finite action과 provenance/latency를 반환한다.
  - Failure probe: revision drift, camera relabel, invalid action dimension이 FAIL한다.
  - Commit: changeset 2 — OpenVLA serving adapter.
- [ ] **step-3 — pi05-server-adapter**
  - Artifact: exact π₀.₅-LIBERO openpi server adapter.
  - Files: openpi adapter/config/verify evidence, changeset.
  - Dependencies: step-1
  - Verify: 같은 envelope sample에서 finite action chunk와 norm/preprocess provenance를 반환한다.
  - Failure probe: missing norm stats, suite mismatch, hidden transform이 FAIL한다.
  - Commit: changeset 3 — π₀.₅ serving adapter.
- [ ] **step-4 — heartbeat-and-stop-gate**
  - Artifact: health, heartbeat expiry, cancel과 model crash를 fail-closed로 다루는 supervisor.
  - Files: supervisor/fault fixtures/verify report, changeset.
  - Dependencies: step-2, step-3
  - Verify: stale server와 kill injection에서 새 action을 반환하지 않는다.
  - Failure probe: cached action replay, cancel 후 response, silent reconnect가 FAIL한다.
  - Commit: changeset 4 — fail-closed server supervision.
- [ ] **step-5 — cross-policy-contract-gate**
  - Artifact: 두 server의 envelope/provenance/latency/error parity를 검증한 LIVE1 report.
  - Files: integration verifier, canonical fixtures, changeset, final report.
  - Dependencies: step-1, step-2, step-3, step-4
  - Verify: 두 real checkpoint smoke와 all negative fixtures PASS.
  - Failure probe: policy source swap, action shape drift, external bind가 FAIL한다.
  - Commit: changeset 5 — unified policy server contract.

## Verification / DoD
- 두 policy가 localhost-only 동일 envelope와 fail-closed lifecycle로 실제 inference를 제공한다.
