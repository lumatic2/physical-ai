# PLAN — LIVE3 실시간 관찰 stream

Status: approved — 2026-07-21 사용자 승인; Horizon 전체 연쇄 실행

## Objective → Horizon → Milestone
- Objective: 카메라·센서·행동 전 과정을 사람이 관찰한다.
- Horizon: `plans/horizons/live-instruction-execution-lab.md`
- Milestone: running session의 dual-camera/state/action/VLM·VLA·controller event를 source와 timestamp가 보이는 live stream으로 전달한다.

## Scope Boundary
- 포함: stream schema, media transport, synchronized telemetry/event, browser subscriber, live QA.
- 제외: action command from browser, recording promotion, public streaming.
- Start gate: LIVE2 final report PASS.
- Execution mode: continuous
- Stop only: completed, blocked, decision_required, risk_gate, secret_required, user_stopped.
- Rollback/cleanup: localhost sockets와 media buffers를 session 종료 시 제거한다.

## planning_gate
```yaml
planning_gate:
  team_validation_mode: manual-pass
  scope_posture: selective
  delegation_decision: {remote_background_agents: skip, reason: "한 session timeline의 producer/subscriber sync를 통합한다."}
  qa: "drop, reorder, stale frame과 source relabel을 검증한다."
```

## 스캐폴딩 결정
- source-of-truth: session id/timestep/timestamp/source를 가진 `physical-ai-live-stream-v1`이다.
- 검증: producer fixtures, browser Playwright와 real session sync probe를 사용한다.
- 배포/운영: localhost WebSocket/media stream; public domain과 remote bind 없음.
- transport: camera는 bounded binary frames, telemetry/event는 ordered JSON envelope다.
- 관측: drop/reorder count, sync delta, queue depth, subscriber lag와 현재 execution lane/source를 노출한다.
- 검토 후 제외: WebRTC internet relay, remote robot control, hidden thought text.

## 결정 로그
- status: resolved
- browser는 read-only subscriber이며 action/control 권한은 session controller에만 있다.

## Step 트리
- [ ] **step-1 — live-stream-schema**
  - Artifact: camera/state/action/event/health envelope와 ordering contract.
  - Files: `experiments/157-observable-live-stream/schema/`, fixtures/tests, changeset.
  - Dependencies: 없음
  - Verify: multi-rate samples가 common timestep과 source를 lossless round-trip한다.
  - Failure probe: missing source, time reversal, cross-session frame가 FAIL한다.
  - Commit: changeset 1 — observable stream schema.
- [ ] **step-2 — dual-camera-transport**
  - Artifact: main/wrist frames와 camera role/hash/latency를 보내는 bounded producer.
  - Files: media producer/client/tests, changeset.
  - Dependencies: step-1
  - Verify: two camera streams remain within declared sync/drop budget.
  - Failure probe: wrist relabel, stale buffer replay, unbounded queue가 FAIL한다.
  - Commit: changeset 2 — synchronized camera transport.
- [ ] **step-3 — telemetry-event-alignment**
  - Artifact: state, Qwen3-VL structured observation/skill, VLA proposed action, controller executed action과 result의 frame alignment.
  - Files: stream adapter/alignment verifier/evidence, changeset.
  - Dependencies: step-2
  - Verify: selected timestep resolves camera/state/action/event from one session.
  - Failure probe: action without request/source, VLM output의 VLA-thought relabel, future event parent, timestamp skew가 FAIL한다.
  - Commit: changeset 3 — live telemetry and event alignment.
- [ ] **step-4 — read-only-browser-subscriber**
  - Artifact: reconnect/status/drop/sync summary를 가진 browser stream client.
  - Files: web client/hooks/QA, changeset.
  - Dependencies: step-3
  - Verify: desktop/mobile subscriber renders stream and exposes `qaLiveSessionSummary()`.
  - Failure probe: browser-originated action, stale reconnect, cross-session merge가 FAIL한다.
  - Commit: changeset 4 — browser live subscriber.
- [ ] **step-5 — live-observability-gate**
  - Artifact: two policy sessions의 camera/event/sync/fault live report.
  - Files: integration smoke, `verify/live/`, changeset, final report.
  - Dependencies: step-1, step-2, step-3, step-4
  - Verify: sync/drop/lag budgets, source provenance, console/network and cleanup PASS.
  - Failure probe: 0.75s desync, unknown source, hidden reasoning field가 FAIL한다.
  - Commit: changeset 5 — verified observable live stream.

## Verification / DoD
- 실제 session의 dual-camera와 source-tagged VLM/VLA/controller state/action/event가 read-only browser에서 한 시간축으로 관찰된다.
