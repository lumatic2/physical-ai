# PLAN — GEN1 고정된 다과제 평가 계약

Status: approved — 2026-07-21 사용자 승인; 3-Horizon 전체 연쇄 실행

## Objective → Horizon → Milestone

- Objective: 정책을 직접 실행·비교하고 시뮬레이션부터 실물까지 같은 증거 계약으로 검증한다. (`OBJECTIVE.md`)
- Horizon: 여러 과제에서 통하는 로봇 판단 실험실. (`plans/horizons/multitask-generalization-lab.md`)
- Milestone: 12 task×5 initial state×2 policy를 흔들림 없이 실행할 평가군·result·compatibility 계약을 고정한다.

## Scope Boundary

- 포함: LIBERO Spatial/Object/Goal 각 4 task, initial state 5개, immutable run key, policy compatibility, episode/result schema, clean-rerun gate.
- 제외: 실제 policy rollout, 통계 비교, failure taxonomy, public UI.
- Execution mode: continuous
- Stop only: completed, blocked, decision_required, risk_gate, secret_required, user_stopped.
- Rollback/cleanup: 새 `experiments/150-multitask-evaluation-contract/`만 revert 가능하게 유지하고 cache·download는 repo 밖에 둔다.

## planning_gate

```yaml
planning_gate:
  team_validation_mode: manual-pass
  scope_posture: reduction
  delegation_decision:
    remote_background_agents: skip
    reason: "하나의 schema와 manifest를 순서대로 고정하는 계약 milestone이다."
  perspectives:
    product: "리뷰어가 평가 분모와 제외 조건을 먼저 읽을 수 있다."
    architecture: "LAB1 episode를 재사용하고 task/policy index만 추가한다."
    security: "공개 manifest에 로컬 경로·token·cache 위치가 들어가지 않는다."
    qa: "task/state/policy drift, duplicate run key와 schema mismatch를 negative fixture로 거부한다."
    skeptic: "suite별 checkpoint 차이를 숨긴 공정하지 않은 비교를 금지한다."
```

## 스캐폴딩 결정

- source-of-truth: `benchmark-manifest.json`이 task/state/policy 실행 분모 정본이다.
- 검증: JSON Schema + semantic validator + clean checkout smoke.
- 배포/운영: local contract artifact만 만들며 공개 배포는 GEN5까지 하지 않는다.
- data: 파일 기반 manifest/result; DB·Hub push 없음.
- 관측: run key=`suite/task/init_state/policy_revision/adapter_revision`과 exclusion reason을 기록한다.
- 검토 후 제외: 전체 LIBERO-130, random task sampling, 성공 결과만 저장하기.

## 결정 로그

- status: resolved
- resolved: Spatial/Object/Goal 각 4 task는 instruction/object/spatial diversity를 기준으로 사전 고정한다.
- resolved: policy별 60 episode denominator를 동일하게 유지한다.
- resolved: incompatibility는 실행 실패가 아니라 manifest 단계의 explicit exclusion로 기록한다.

## Step 트리

- [ ] **step-1 — suite-task-slice**
  - Artifact: 3 suite×4 task의 exact id, language, BDDL와 선정 근거가 있는 frozen slice.
  - Files: `experiments/150-multitask-evaluation-contract/benchmark-manifest.json`, `README.md`, changeset.
  - Dependencies: 없음
  - Verify: LIBERO exact revision에서 12 task가 존재하고 instruction·BDDL hash가 일치한다.
  - Failure probe: unknown task, duplicated task, suite relabel fixture가 FAIL한다.
  - Commit: changeset 1 — frozen task slice.
- [ ] **step-2 — initial-state-contract**
  - Artifact: task별 5 initial state index/hash와 deterministic reset probe.
  - Files: `initial-states.json`, `verify_initial_states.py`, verify output, changeset.
  - Dependencies: step-1
  - Verify: 두 clean reset에서 observation/state fingerprint가 일치한다.
  - Failure probe: state order·seed·hash drift가 FAIL한다.
  - Commit: changeset 2 — fixed initial states.
- [ ] **step-3 — policy-compatibility-registry**
  - Artifact: OpenVLA/π₀.₅의 suite checkpoint, revision, camera/state/action adapter 계약.
  - Files: `policy-registry.json`, schema/validator, changeset.
  - Dependencies: step-1
  - Verify: 모든 task-policy pair가 compatible 또는 reasoned exclusion을 가진다.
  - Failure probe: action dimension·camera role·checkpoint suite mismatch가 FAIL한다.
  - Commit: changeset 3 — policy compatibility registry.
- [ ] **step-4 — multitask-result-contract**
  - Artifact: LAB1 episode reference를 가리키는 run/result index schema와 immutable run key.
  - Files: `schemas/multitask-run-v1.json`, fixtures, tests, changeset.
  - Dependencies: step-2, step-3
  - Verify: success/timeout/error/excluded와 timing·hash·revision이 lossless round-trip한다.
  - Failure probe: duplicate key, missing denominator, result without episode evidence가 FAIL한다.
  - Commit: changeset 4 — result and run-key contract.
- [ ] **step-5 — clean-contract-gate**
  - Artifact: manifest 전체의 12×5×2=120 cell 완전성과 negative fixture를 검증한 GEN1 report.
  - Files: `verify_contract.py`, `verify/canonical/`, changeset, final report.
  - Dependencies: step-1, step-2, step-3, step-4
  - Verify: clean run에서 120 unique cells, schema·semantic·path scrub PASS.
  - Failure probe: task/state/policy 한 cell 삭제·중복·revision drift 주입 시 FAIL한다.
  - Commit: changeset 5 — integrated evaluation contract gate.

## Verification / DoD

- 120 cell의 평가 분모가 실행 전에 immutable manifest로 고정되고 모든 compatibility/exclusion이 재계산 가능하다.
