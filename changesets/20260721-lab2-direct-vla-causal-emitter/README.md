# 20260721-lab2-direct-vla-causal-emitter

## Target

- ROADMAP milestone: LAB2 — 출처가 보이는 VLM/VLA 판단·행동 기록.
- Plan leaf: `plans/2026-07-21-lab2-observable-causal-trace.md` step-2.
- Goal: LAB1 episode의 실제 main-camera 입력, raw OpenVLA output, executed action과 outcome을 역추적 가능한 event chain으로 파생한다.

## Planning Gate

```yaml
planning_gate:
  team_validation_mode: manual-pass
  scope_posture: selective
  delegation_decision:
    remote_background_agents: skip
    reason: "LAB1 sidecar와 Parquet의 결정적 변환이며 독립 병렬 작업보다 동일 hash 검증이 중요하다."
    target_roles: []
    execution_path: local_manual
  perspectives:
    product: "direct VLA에는 실제 input/action/latency만 보여주고 언어적 생각을 발명하지 않는다."
    architecture: "event stream은 LAB1 dataset과 sidecar를 payload_ref로 가리키는 파생물이다."
    security: "로컬 경로나 모델 응답 원문 대신 공개 가능한 revision과 수치만 기록한다."
    qa: "wrist model-input relabel, raw/action drift와 실행되지 않은 proposal을 거부한다."
    skeptic: "controller action 하나가 정확히 하나의 VLA proposal과 연결되는지 프레임별로 확인한다."
  dod:
    - "canonical PASS/FAIL 모두 direct VLA event contract를 통과한다."
    - "모든 executed action hash가 LAB1 sidecar와 일치한다."
    - "observer-only wrist camera를 model input으로 바꾸면 실패한다."
```

## Verification

- [x] Direct emitter unit/integration tests: LAB2 전체 15/15 PASS.
- [x] Canonical PASS: 78 frames, 235 events, executed action 78/78 linked.
- [x] Canonical FAIL: 220 frames, 661 events, executed action 220/220 linked.
- [x] Wrist relabel/action drift/unexecuted proposal negative gates FAIL 확인.
- [x] Python compile, run CLI flag surface와 `git diff --check` PASS.

## Result

- Status: completed 2026-07-21
- Evidence: `experiments/148-observable-decision-action-trace/verify/direct-vla/`.
- Reviewer verdict: 두 canonical stream 모두 wrist를 observer-only로 유지하고 모든 controller action을 단일 raw OpenVLA proposal과 LAB1 hash로 역추적한다.
