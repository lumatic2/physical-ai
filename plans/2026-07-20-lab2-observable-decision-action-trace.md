# PLAN — LAB2 출처가 보이는 VLM/VLA 판단·행동 기록

Status: approved 2026-07-20

> 생성: 2026-07-20 · 갈래: product · scope 결정: structured semantic/skill lane과 direct VLA action lane의 provenance 검증까지
> milestone-레벨 durable plan doc. 진행 상태의 정본은 산출물 status machine과 `ROADMAP.md`다.

## 북극성 → horizon → milestone → step

- **북극성**: 보고 이해하고 행동하는 전 과정을 사람이 관찰할 수 있게 한다. (← `OBJECTIVE.md`)
- **horizon**: 보고 판단하고 움직이는 로봇팔 실험실 (← `plans/horizons/see-understand-act-robot-lab.md`)
- **milestone**: semantic observation, causal skill execution, direct VLA action과 negative provenance gate가 여러 surface를 가로지르므로 milestone 규모다.

## Scope Boundary

- 결정: LAB1 trace에 source-tagged decision events를 추가하고, 계층형 VLM→skill lane과 end-to-end VLA lane의 차이를 실제 실행 기록으로 구분한다.
- Execution mode: `continuous`
- Stop only: completed, blocked, decision_required, risk_gate, secret_required, external_authority_required, user_stopped.
- 진행 보고: commentary only. 미완 leaf는 턴 종료점이 아니다.
- Rollback/cleanup: semantic lane, skill executor, VLA provenance changeset을 독립 revert하고 model server/process와 임시 prompts를 정리한다.

## 스캐폴딩 결정

- source-of-truth: LAB1 `physical-ai-arm-episode-v1` + 새 `experiments/148-observable-decision-action-trace` event schema/evidence.
- 검증: source enum validator, timestamp/provenance integration smoke, hidden-reasoning negative fixture, causal skill outcome check.
- 배포/운영: 로컬 open-weight model과 simulator만 사용한다. secret/API와 상시 inference service는 없다.
- AI: local open-weight VLM 후보를 compatibility probe로 선택해 schema-constrained scene/skill JSON만 기록한다. exact checkpoint는 first passing official candidate로 evidence에 pin한다.
- control: hierarchical lane은 VLM-selected target/skill을 명시적 skill executor에 전달하며 simulator ground-truth pose 사용 여부를 event source에 공개한다.
- data: event source는 `sensor|vlm|vla|controller|environment`; free-form hidden chain-of-thought 필드는 schema가 거부한다.
- 검토 후 제외: 인증·DB·결제·외부 API — 로컬 reproducible trace가 목적이다.

## 결정 로그

- status: resolved
- 읽을 수 있는 판단 기록을 위해 계층형 lane을 두되, direct VLA의 숨은 생각으로 위장하지 않는다 — 사용자 요구와 증거 정직성 기준 2026-07-20.
- 모델 내부 chain-of-thought 대신 structured observation, selected skill, action chunk, measured result만 공개한다 — 확정 2026-07-20.

## Step 트리

- [ ] **step-1 — source-tagged-event-contract**
  - Artifact: decision event schema, UI-facing vocabulary, valid/invalid fixtures.
  - Files: `experiments/148-observable-decision-action-trace/`, LAB1 schema references.
  - Dependencies: none
  - Verify: all valid events carry timestep/source/component; unknown source and hidden reasoning fields FAIL.
  - Failure probe: VLM event를 VLA source로 relabel하면 provenance gate가 거부한다.
  - Commit: changeset 1 — decision/action provenance contract.
- [ ] **step-2 — hierarchical-vlm-skill-lane**
  - Artifact: local VLM structured scene/skill JSON이 explicit skill executor input이 되고 environment outcome까지 trace에 연결된다.
  - Files: new VLM adapter, schema-constrained prompt/parser, bounded skill executor, experiment 148 evidence.
  - Dependencies: step-1
  - Verify: selected target/skill, executor input, controller commands and resulting contact/success share one causal id.
  - Failure probe: invalid target, unsupported skill, missing grounding source가 실행 전에 blocked event를 만든다.
  - Commit: changeset 2 — hierarchical observable lane.
- [ ] **step-3 — direct-vla-action-lane**
  - Artifact: VLA model input keys, action representation, raw action chunk, postprocessed action and latency events.
  - Files: LAB1 policy adapter, experiment 148 trace emitter/evidence.
  - Dependencies: step-1
  - Verify: one bounded episode records model input provenance and every executed action maps to a VLA output or explicit fallback.
  - Failure probe: observer-only camera를 model input으로 표시하거나 executed action origin이 없으면 FAIL.
  - Commit: changeset 3 — direct VLA provenance lane.
- [ ] **step-4 — decision-action-integration-gate**
  - Artifact: hierarchical/direct modes의 common summary와 PASS/FAIL provenance comparison.
  - Files: experiment 148 validator, README, verify summary.
  - Dependencies: step-2, step-3
  - Verify: both modes pass common timing/source contract and expose different causal boundaries.
  - Failure probe: generated narrative without source/action linkage cannot satisfy completion gate.
  - Commit: changeset 4 — integrated decision/action evidence.

## 검증/DoD

- **DoD**: 계층형 VLM→skill과 direct VLA action episode가 동일 trace contract에서 실행되고, 모든 event의 실제 source·causal role·outcome이 검증되며 가짜 hidden reasoning fixture가 거부된다.

## finding 큐

- local VLM이 stable structured output을 내지 못하면 모델 교체보다 deterministic constrained decoding/parser evidence를 먼저 조사한다.

## 진행 로그

- 2026-07-20 사용자 방향 승인 후 계획 작성.
