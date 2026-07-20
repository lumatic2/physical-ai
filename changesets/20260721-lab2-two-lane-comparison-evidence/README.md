# 20260721-lab2-two-lane-comparison-evidence

## Target

- ROADMAP milestone: LAB2 — 출처가 보이는 VLM/VLA 판단·행동 기록.
- Plan leaf: `plans/2026-07-21-lab2-observable-causal-trace.md` step-4.
- Goal: direct VLA와 VLM→scripted skill의 실제 PASS/FAIL trace를 같은 contract로 비교하고 source/assistance/outcome relabel을 거부한다.

## Planning Gate

```yaml
planning_gate:
  team_validation_mode: manual-pass
  scope_posture: selective
  delegation_decision:
    remote_background_agents: skip
    reason: "네 canonical trace의 hash·source·outcome을 한 gate에서 대조하는 단일 통합 changeset이다."
    target_roles: []
    execution_path: local_manual
  perspectives:
    product: "두 lane이 같은 모델 내부 단계가 아니라 서로 다른 제어 구조임을 즉시 읽을 수 있어야 한다."
    architecture: "direct VLA는 raw action, VLM lane은 selected skill과 scripted executor를 각각 정본 source로 유지한다."
    security: "공개 bundle에는 local path나 secret 없이 content hash와 revision만 둔다."
    qa: "VLM→VLA source relabel, scripted outcome→model result relabel, assistance 누락과 outcome drift를 거부한다."
    skeptic: "PASS만 고르지 않고 같은 초기 상태 쌍의 timeout까지 양 lane에 보존한다."
  dod:
    - "direct VLA와 VLM-skill 각각 PASS/FAIL event stream이 schema를 통과한다."
    - "lane별 실제 모델 revision과 assistance 차이가 보존된다."
    - "네 raw artifact hash와 상반 outcome이 comparison report에 고정된다."
```

## Verification

- [x] Four canonical streams schema PASS.
- [x] Direct VLA: PASS 235 events/success, FAIL 661 events/timeout provenance PASS.
- [x] VLM-skill: PASS 78 actions/success, FAIL 220 actions/timeout measured outcome와 assistance PASS.
- [x] Source/assistance/outcome/hidden-reasoning negative relabels FAIL 확인.
- [x] Process cleanup, 전체 LAB2 31/31 tests, Python compile와 `git diff --check` PASS.

## Result

- Status: completed 2026-07-21
- Evidence: `experiments/148-observable-decision-action-trace/verify/two-lane/comparison-report.json`.
- Reviewer verdict: 두 lane의 동일점은 camera+instruction에서 environment outcome까지 이어진다는 것뿐이며, action 생성 주체와 assistance가 서로 다름을 네 trace가 보존한다.
