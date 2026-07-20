# PLAN — LAB2 관찰 가능한 판단·행동 인과 기록

Status: approved 2026-07-21 — Horizon 전체 연쇄 실행 승인
Supersedes: `plans/2026-07-20-lab2-observable-decision-action-trace.md`

> LAB1의 LeRobot episode 위에 direct VLA와 계층형 VLM→skill을 사실에 맞게 구분해 보여주는 후속 실행안이다.

## 북극성 → Horizon → Milestone → Step

- **북극성**: 카메라와 센서로 세상을 보고, 언어 지시를 이해하고, 로봇 행동을 생성·실행하며, 그 전 과정을 사람이 관찰할 수 있는 피지컬 AI 실험실. (← `OBJECTIVE.md`)
- **Horizon**: 보고 판단하고 움직이는 로봇팔 실험실. (← `plans/horizons/see-understand-act-robot-lab.md`)
- **Milestone**: LAB1의 물리 episode에 source·causal role이 검증되는 판단/행동 event를 결합하는 LAB2.

## Scope Boundary

- 결정: direct VLA 경로와 계층형 VLM→검증된 skill 경로를 같은 event contract에서 비교하되, 생성된 설명을 VLA의 숨은 사고 과정으로 제시하지 않는다.
- 포함: provenance event contract, direct VLA emitter, local open-weight VLM structured output, bounded skill executor, 통합 PASS/FAIL trace.
- 제외: free-form chain-of-thought, 클라우드 모델 API, 자율 장기 계획, 새 foundation model 학습, 공개 UI.
- Execution mode: `continuous`
- Stop only: completed, blocked, decision_required, risk_gate, secret_required, external_authority_required, user_stopped.
- Rollback/cleanup: event layer와 VLM lane은 LAB1 canonical episode를 변경하지 않는 파생 artifact로 만들고 changeset별 revert가 가능하게 한다. model server·GPU process·임시 frame cache를 종료·삭제한다.

## planning_gate

- team_validation_mode: `manual-pass`
- scope_posture: `selective` — VLM 이해를 보여줄 최소 계층형 lane만 추가하고 general-purpose agent는 만들지 않는다.
- delegation_decision: `skip` — 모델 선택은 명시된 로컬 기술 gate로 해결하며 사용자 선택이나 병렬 조사 없이 진행 가능하다.
- spec_delta: LAB1 sidecar를 provenance event로 승격하고 direct VLA와 VLM→skill을 별도 causal lane으로 정의한다.
- product: 사용자가 관찰·판단·행동·결과를 한 흐름으로 읽되, 무엇이 모델 출력이고 무엇이 시스템 설명인지 즉시 구분해야 한다.
- architecture: 모든 event는 episode timestep과 parent event를 가리키며 실제 controller action까지 이어지지 않은 narrative는 causal action으로 취급하지 않는다.
- security: prompt와 image metadata에서 로컬 경로·secret을 제거하고 외부 API 전송을 금지한다.
- qa: unknown source, hidden reasoning, 잘못된 parent, 실행되지 않은 action, ground-truth 미표기를 negative fixture로 막는다.
- skeptic: direct VLA에는 언어적 생각을 발명하지 않고 실제 input/action/latency만 보여준다. VLM lane의 simulator 도움은 명시한다.

## 스캐폴딩 결정

- source-of-truth: LAB1 LeRobot episode가 물리 시계열 정본이고 `experiments/148-observable-decision-action-trace`의 event stream이 판단·인과 정본이다.
- 검증: JSON schema/unit test, direct VLA integration smoke, VLM structured-output contract, skill safety gate, source/causal/outcome negative fixture.
- 배포/운영: LAB2는 로컬 파생 trace와 evidence까지만 만든다. 공개 asset은 LAB3가 content-hashed bundle로 변환한다.
- data: event는 timestep, source, kind, component revision, parent, payload reference, causal role과 assistance flag를 가진다.
- model: image+instruction structured JSON, 32GB 환경 적합성, open-weight/local execution, revision pin을 모두 통과하는 첫 후보를 사용한다. 두 후보가 연속 실패하면 technical blocker로 보고한다.
- control: VLM은 허용된 bounded skill만 선택하고 skill executor가 action을 만든다. direct VLA의 action은 raw→postprocessed→executed 단계를 분리한다.
- 관측: model latency, validation result, selected skill, action chunk, controller acceptance, environment outcome을 event로 연결한다.
- 검토 후 제외: frontend·public deploy·인증·DB — 이 Milestone은 인과 trace 생성과 검증에 한정한다.

## 결정 로그

- status: resolved
- 화면의 ‘생각’은 structured observation·selected skill·action·measured result로 제한하고 hidden chain-of-thought는 저장하거나 표시하지 않는다.
- direct VLA와 계층형 VLM→skill은 서로 다른 실험 lane이며 같은 모델의 내부 단계처럼 합치지 않는다.
- local open-weight VLM은 브랜드보다 기술 gate로 고르고 exact revision과 prompt schema를 evidence에 고정한다.
- simulator ground truth나 scripted skill이 사용되면 assistance flag와 source로 공개한다.

## Step 트리

- [ ] **step-1 — provenance-event-contract**
  - Artifact: `sensor|vlm|vla|controller|environment` source와 parent/causal role/assistance를 검증하는 event schema, 정상·실패 fixture와 문서.
  - Files: `experiments/148-observable-decision-action-trace/`, `docs/PRD.md`, `docs/ARCHITECTURE.md`.
  - Dependencies: 없음
  - Start gate: LAB1 step-4의 canonical PASS/FAIL pair가 완료된 뒤 실행한다.
  - Verify: valid event chain PASS; unknown source, hidden reasoning field, missing parent, cyclic parent, unmarked assistance fixture FAIL.
  - Failure probe: timestamp만 인접하고 parent가 없는 설명 event를 controller action의 원인으로 relabel하면 validator가 거부한다.
  - Commit: changeset 1 — provenance and causal event contract.
- [ ] **step-2 — direct-vla-causal-emitter**
  - Artifact: LAB1 OpenVLA rollout의 실제 model input provenance, raw output, postprocessed action, executed action, latency와 outcome을 연결한 direct VLA event stream.
  - Files: `experiments/01-vla-local-eval/client.py`, `experiments/148-observable-decision-action-trace/direct_vla.py`, integration test와 evidence fixture.
  - Dependencies: step-1
  - Verify: 모든 executed action이 단 하나의 raw VLA output과 controller acceptance로 역추적되고 episode timestep과 일치한다.
  - Failure probe: observer-only wrist camera를 model input으로 표시하거나 실행되지 않은 proposal을 executed로 표시하면 FAIL한다.
  - Commit: changeset 2 — direct VLA causal events.
- [ ] **step-3 — vlm-bounded-skill-lane**
  - Artifact: main camera+instruction에서 schema-valid scene observation과 selected skill을 내고, allowlist executor가 bounded action을 실행해 result를 기록하는 local VLM lane.
  - Files: `experiments/148-observable-decision-action-trace/vlm_runner.py`, `skill_executor.py`, prompt/schema, unit/integration test와 model revision record.
  - Dependencies: step-1
  - Verify: 고정 frames에서 structured output이 schema를 통과하고 selected skill→controller action→environment result가 parent chain으로 이어진다.
  - Failure probe: unknown object, invalid target, allowlist 밖 skill, malformed JSON이면 action 실행 전에 차단한다.
  - Commit: changeset 3 — local VLM to bounded skill lane.
- [ ] **step-4 — two-lane-comparison-evidence**
  - Artifact: 같은 event contract에서 direct VLA와 VLM→skill의 PASS/FAIL trace, provenance summary와 비교 재현 명령.
  - Files: `experiments/148-observable-decision-action-trace/verify/`, README/evidence index, `ROADMAP.md`.
  - Dependencies: step-2, step-3
  - Verify: 두 lane 모두 schema PASS하고 observation→decision/action→controller→outcome 연결과 assistance/model revision을 보존한다.
  - Failure probe: VLM 설명을 VLA thought로 바꾸거나 scripted outcome을 model result로 바꾸면 claim gate가 FAIL한다.
  - Commit: changeset 4 — two-lane observable causal evidence.

## 검증/DoD

- **DoD**: 계층형 VLM→skill과 direct VLA action episode가 동일 event contract에서 실행되고, 모든 event의 실제 source·causal role·assistance·outcome이 검증되며 hidden-reasoning fixture가 거부된다.

## finding 큐

- 첫 local VLM 후보의 exact checkpoint는 step-3에서 32GB 적합성·structured output·license gate를 모두 통과한 결과로 고정하고 evidence에 출처와 revision을 남긴다.
