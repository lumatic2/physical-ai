# PLAN — GEN4 증거 기반 실패 양상

Status: approved — 2026-07-21 사용자 승인; 3-Horizon 전체 연쇄 실행

## Objective → Horizon → Milestone

- Objective: 검증된 능력과 아직 검증되지 않은 한계가 함께 드러난다. (`OBJECTIVE.md`)
- Horizon: 여러 과제에서 통하는 로봇 판단 실험실. (`plans/horizons/multitask-generalization-lab.md`)
- Milestone: non-success episode를 추정 원인이 아닌 관측 가능한 실패 양상과 evidence pointer로 분류한다.

## Scope Boundary

- 포함: outcome/trajectory/event 기반 taxonomy, evidence rules, classifier, reviewer sample, policy/suite breakdown.
- 제외: hidden reasoning, model 내부 원인 추정, 자연어 자유 생성 진단, 자동 remediation.
- Execution mode: continuous
- Stop only: completed, blocked, decision_required, risk_gate, secret_required, user_stopped.
- Rollback/cleanup: derived label/index만 추가하고 canonical episode를 수정하지 않는다.

## planning_gate

```yaml
planning_gate:
  team_validation_mode: manual-pass
  scope_posture: reduction
  delegation_decision:
    remote_background_agents: skip
    reason: "taxonomy와 validator를 같은 evidence examples로 반복 교정하는 단일 판단 경계다."
  perspectives:
    product: "실패 카드마다 사람이 확인할 camera/event/metric이 있다."
    architecture: "label은 canonical evidence의 derived index이며 원본을 덮어쓰지 않는다."
    security: "자유 생성 텍스트와 로컬 path를 공개 label에 넣지 않는다."
    qa: "근거 부족·복수 가능성은 unknown/multiple로 보존한다."
    skeptic: "상관된 움직임을 perception 또는 planning 원인으로 부르지 않는다."
```

## 스캐폴딩 결정

- source-of-truth: GEN2/GEN3 canonical episodes와 derived feature/pattern index다.
- 검증: schema, deterministic classifier fixture, stratified reviewer sample과 coverage recomputation을 사용한다.
- 배포/운영: derived local evidence만 만들며 공개 배포는 GEN5까지 하지 않는다.
- taxonomy: `no_progress`, `wrong_object_interaction`, `grasp_lost`, `timeout_near_goal`, `controller_rejected`, `infrastructure_error`, `unknown`의 관측 용어만 사용한다.
- evidence: 각 label은 frame/time range, metric predicate와 source event ref가 필요하다.
- classification: deterministic rule first; 충돌하면 multiple, 미충족이면 unknown.
- review: suite/policy/label stratified sample을 사람이 원 episode로 확인한다.
- 검토 후 제외: LLM-generated diagnosis, confidence를 근거 없이 확률처럼 표현하기.

## 결정 로그

- status: resolved
- resolved: “원인” 대신 “실패 양상”을 정본 용어로 쓴다.
- resolved: unknown 비율은 결함이 아니라 evidence coverage metric으로 공개한다.

## Step 트리

- [ ] **step-1 — failure-pattern-contract**
  - Artifact: label 정의, 필수 predicate/evidence와 금지 claim schema.
  - Files: `experiments/153-observable-failure-patterns/failure-pattern-schema.json`, README/fixtures, changeset.
  - Dependencies: 없음
  - Verify: 모든 label이 관측 가능한 조건과 canonical pointer를 요구한다.
  - Failure probe: `bad reasoning`, `did not understand` 같은 원인 추정 label이 FAIL한다.
  - Commit: changeset 1 — observable failure contract.
- [ ] **step-2 — trajectory-event-features**
  - Artifact: progress, gripper/object relation, goal distance, rejection와 infra state를 추출하는 derived features.
  - Files: feature extractor/tests, fixtures, changeset.
  - Dependencies: step-1
  - Verify: feature가 episode hash와 frame range를 보존하고 원본을 수정하지 않는다.
  - Failure probe: missing camera/event, unit mismatch, NaN을 label로 승격하면 FAIL한다.
  - Commit: changeset 2 — evidence feature extraction.
- [ ] **step-3 — deterministic-classifier**
  - Artifact: rule version과 evidence pointer를 가진 failure-pattern index.
  - Files: classifier/rules/tests, `verify/patterns/`, changeset.
  - Dependencies: step-2
  - Verify: identical evidence는 byte-identical label/index를 만들고 conflicts는 multiple/unknown이다.
  - Failure probe: order-sensitive rule, unsupported causal label, missing pointer가 FAIL한다.
  - Commit: changeset 3 — deterministic failure patterns.
- [ ] **step-4 — reviewer-calibration**
  - Artifact: policy/suite/label stratified sample과 사람 검토 checklist·agreement report.
  - Files: sampler, reviewer packet, `verify/reviewer-report.json`, changeset.
  - Dependencies: step-3
  - Verify: sample에서 label predicate와 episode camera/event가 일치하고 disagreement를 보존한다.
  - Failure probe: success-only sample, unknown 제외, reviewer override 무기록이 FAIL한다.
  - Commit: changeset 4 — reviewer calibration evidence.
- [ ] **step-5 — failure-coverage-gate**
  - Artifact: policy/suite별 pattern·unknown coverage와 negative claim gate를 묶은 GEN4 report.
  - Files: aggregate/validator, verify report, changeset, final report.
  - Dependencies: step-1, step-2, step-3, step-4
  - Verify: 모든 non-success episode가 evidence-backed pattern 또는 unknown으로 완전 집계된다.
  - Failure probe: denominator omission, unknown 숨김, failure pattern을 root cause로 relabel하면 FAIL한다.
  - Commit: changeset 5 — verified failure coverage.

## Verification / DoD

- non-success episode 100%가 관측 가능한 evidence label 또는 unknown을 가지며 원인 과장 fixture가 거부된다.
