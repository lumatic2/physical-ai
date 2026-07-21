# PLAN — LIVE1 통합 inference server 계약

Status: pending current approval — 2026-07-21 계획 보강

## Objective → Horizon → Milestone
- Objective: 정책을 직접 실행하고 전 과정을 관찰한다. (`OBJECTIVE.md`)
- Horizon: 지시를 바꿔 실행하는 로컬 피지컬 AI 실험실. (`plans/horizons/live-instruction-execution-lab.md`)
- Milestone: OpenVLA·π₀.₅ direct VLA와 Qwen3-VL bounded skill을 동일 localhost request/result/stop 계약으로 제공한다.

## Scope Boundary
- 포함: WebSocket envelope, exact model adapter, exclusive GPU lease, health/heartbeat, latency, fail-closed stop, contract gate.
- 제외: browser UI, session orchestration, recording, public backend.
- Start gate: GEN Horizon final report PASS + Ubuntu-24.04 `nvidia-smi`와 OpenVLA/openpi/Qwen3-VL env readiness PASS. 현재 WSL probe timeout은 구현 전 recovery 대상으로 기록한다.
- Execution mode: continuous
- Stop only: completed, blocked, decision_required, risk_gate, secret_required, user_stopped.
- Rollback/cleanup: 세 inference env/cache는 repo 밖에 두고 schema·adapter·verify evidence만 revert 가능하게 추적한다.

## planning_gate
```yaml
planning_gate:
  team_validation_mode: manual-pass
  scope_posture: reduction
  delegation_decision: {remote_background_agents: skip, reason: "세 adapter와 GPU lease를 한 localhost envelope에 순차 통합하며 기존 실측 환경을 재사용한다."}
  qa: "malformed request, stale heartbeat, model crash와 wrong revision을 fail-closed로 검사한다."
```

## 스캐폴딩 결정
- source-of-truth: `physical-ai-inference-server-v1` envelope와 exact execution-lane registry다.
- 검증: schema/semantic tests, 세 real checkpoint smoke, exclusive lease 전환, heartbeat/kill fault injection을 사용한다.
- 배포/운영: localhost-only WSL processes; 외부 listen·Vercel backend 없음.
- runtime: OpenVLA, openpi, Qwen3-VL은 격리 env에서 한 번에 하나만 GPU lease를 소유하고 thin client만 공유한다.
- 관측: request id, policy revision, preprocess revision, latency와 action chunk shape를 기록한다.
- 검토 후 제외: training, auth, multi-user queue, public network exposure, free-form chain-of-thought.

## 결정 로그
- status: resolved
- server는 inference만 소유하고 action execution/stop은 session controller가 소유한다.
- Qwen3-VL은 구조화된 scene/allowlisted skill만 반환하며 저수준 action을 생성한 것으로 표시하지 않는다.

## Step 트리
- [ ] **step-1 — inference-server-envelope**
  - Artifact: execution lane, observation/prompt/proposal/action/error/health WebSocket schema와 reference client.
  - Files: `experiments/155-unified-policy-server/schema/`, client/tests, changeset.
  - Dependencies: 없음
  - Verify: valid round-trip과 version negotiation이 PASS한다.
  - Failure probe: unknown version, missing camera/state, oversized payload가 FAIL한다.
  - Commit: changeset 1 — inference server envelope.
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
- [ ] **step-4 — qwen3-vl-bounded-adapter**
  - Artifact: Qwen3-VL exact revision이 image+instruction에서 schema-validated scene/allowlisted skill을 반환하는 bounded adapter.
  - Files: VLM adapter/config/fixtures/verify evidence, changeset.
  - Dependencies: step-1
  - Verify: LAB2 frame과 live sample에서 structured observation/skill/source/latency를 반환한다.
  - Failure probe: unknown object, non-allowlisted skill, hidden reasoning field와 VLA-thought relabel이 FAIL한다.
  - Commit: changeset 4 — bounded Qwen3-VL inference adapter.
- [ ] **step-5 — gpu-lease-heartbeat-and-stop-gate**
  - Artifact: exclusive GPU lease, health, heartbeat expiry, cancel과 model crash를 fail-closed로 다루는 supervisor.
  - Files: supervisor/fault fixtures/verify report, changeset.
  - Dependencies: step-2, step-3, step-4
  - Verify: lane 전환 때 이전 process·port·VRAM이 정리되고 stale server와 kill injection에서 새 action/proposal을 반환하지 않는다.
  - Failure probe: concurrent GPU owners, cached action replay, cancel 후 response, silent reconnect가 FAIL한다.
  - Commit: changeset 5 — exclusive GPU lease and fail-closed supervision.
- [ ] **step-6 — cross-lane-contract-gate**
  - Artifact: 세 inference lane의 envelope/provenance/latency/error/source parity를 검증한 LIVE1 report.
  - Files: integration verifier, canonical fixtures, changeset, final report.
  - Dependencies: step-1, step-2, step-3, step-4, step-5
  - Verify: 세 real checkpoint smoke와 all negative fixtures PASS.
  - Failure probe: lane/source swap, action shape drift, VLM action claim과 external bind가 FAIL한다.
  - Commit: changeset 6 — unified inference server contract.

## Verification / DoD
- 세 실행 레인이 localhost-only 동일 envelope, exclusive GPU lease와 fail-closed lifecycle로 실제 inference를 제공한다.
