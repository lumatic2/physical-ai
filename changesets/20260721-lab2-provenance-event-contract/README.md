# 20260721-lab2-provenance-event-contract

## Target

- ROADMAP milestone: LAB2 — 출처가 보이는 VLM/VLA 판단·행동 기록.
- Plan leaf: `plans/2026-07-21-lab2-observable-causal-trace.md` step-1.
- Goal: 판단·행동 event의 실제 출처, 인과 역할, parent, assistance와 component revision을 기계 검증한다.

## Planning Gate

```yaml
planning_gate:
  team_validation_mode: manual-pass
  scope_posture: selective
  delegation_decision:
    remote_background_agents: skip
    reason: "승인 계획이 필드와 failure probe를 고정한 단일 Python 계약 changeset이며 공유 편집 이득이 없다."
    target_roles: []
    execution_path: local_manual
  perspectives:
    product: "사람이 각 기록의 실제 생성 주체와 행동으로 이어진 근거를 바로 구분해야 한다."
    architecture: "LAB1 episode는 물리 정본으로 유지하고 event stream은 참조만 하는 파생 정본이다."
    security: "숨은 reasoning, 로컬 경로와 secret을 payload에 허용하지 않는다."
    qa: "unknown source, hidden reasoning, missing/cyclic parent, unmarked assistance와 causal relabel을 거부한다."
    skeptic: "시간상 인접한 설명을 controller action의 원인으로 둔갑시키지 않는다."
  dod:
    - "valid direct VLA event chain이 PASS한다."
    - "모든 event가 source, causal role, parent, revision, assistance를 보존한다."
    - "hidden reasoning과 잘못된 인과·도움 표식 fixture가 FAIL한다."
```

## Scope

| File/Path | Reason | Expected effect |
|---|---|---|
| `experiments/148-observable-decision-action-trace/event_schema.py` | 의미 검증 | source·parent·role·assistance drift를 막는다. |
| `experiments/148-observable-decision-action-trace/event-schema.json` | 공개 구조 계약 | producer와 LAB3 consumer가 같은 필드를 사용한다. |
| `experiments/148-observable-decision-action-trace/test_event_schema.py` | 정상·실패 회귀 | hidden reasoning과 가짜 인과를 거부한다. |
| `docs/PRD.md`, `docs/ARCHITECTURE.md` | 제품·구조 계약 | event stream의 정본과 금지 경계를 명시한다. |

## Verification

- [x] Contract unit tests: 9/9 PASS.
- [x] Valid fixture CLI: exit 0, `valid=true`.
- [x] Hidden reasoning fixture CLI: exit 1, `hidden_reasoning_forbidden`.
- [x] Python compile와 `git diff --check` PASS.
- [x] `git status --short`에서 LAB1 canonical pair 변경 없음 확인.

## Result

- Status: completed 2026-07-21
- Evidence: formal JSON Schema, dependency-free semantic validator, valid/invalid CLI fixtures와 9개 unit failure probes.
- Reviewer verdict: source-role mapping과 topological parent 규칙이 시간 인접성을 인과로 둔갑시키는 경로를 막고, hidden reasoning 및 미표식 assistance를 거부한다.
