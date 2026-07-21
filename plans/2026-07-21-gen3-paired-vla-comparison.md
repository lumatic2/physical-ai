# PLAN — GEN3 두 VLA의 공정 비교

Status: approved — 2026-07-21 사용자 승인; 3-Horizon 전체 연쇄 실행

## Objective → Horizon → Milestone

- Objective: 여러 정책을 동일 기준으로 직접 실행·비교한다. (`OBJECTIVE.md`)
- Horizon: 여러 과제에서 통하는 로봇 판단 실험실. (`plans/horizons/multitask-generalization-lab.md`)
- Milestone: π₀.₅-LIBERO 60 cell을 같은 계약으로 실행하고 OpenVLA와 paired comparison을 고정한다.

## Scope Boundary

- 포함: π₀.₅ exact revision/checkpoint, adapter parity, 60 rollout, paired statistics, fairness gate.
- 제외: model fine-tuning, 승자 일반화 주장, 서로 다른 denominator 비교, public dashboard.
- Execution mode: continuous
- Stop only: completed, blocked, decision_required, risk_gate, secret_required, user_stopped.
- Rollback/cleanup: openpi env/checkpoint cache는 repo 밖, evidence만 allowlist한다.

## planning_gate

```yaml
planning_gate:
  team_validation_mode: manual-pass
  scope_posture: reduction
  delegation_decision:
    remote_background_agents: skip
    reason: "두 GPU stack을 같은 manifest와 verifier에 통합하는 순차 milestone이다."
  perspectives:
    product: "순위보다 suite/task/state별 paired 결과와 분모가 보인다."
    architecture: "policy adapter만 교체하고 environment·episode writer·result contract를 고정한다."
    security: "외부 checkpoint credential과 cache path를 artifact에서 제거한다."
    qa: "observation/action transform parity와 suite checkpoint mapping을 검사한다."
    skeptic: "서로 다른 입력·재시도·checkpoint를 같은 조건으로 가장하지 않는다."
```

## 스캐폴딩 결정

- source-of-truth: GEN1 manifest, GEN2 baseline ledger와 π₀.₅ canonical episodes다.
- 검증: adapter parity, paired-key join, raw denominator 재계산과 fairness negative fixture를 사용한다.
- 배포/운영: local WSL/GPU evidence만 만들며 공개 배포는 GEN5까지 하지 않는다.
- runtime: openpi가 요구하는 Ubuntu 환경을 별도 WSL venv/container로 격리한다.
- inference: π₀.₅-LIBERO official checkpoint와 policy server/client contract.
- fairness: task/state/environment는 GEN1 고정, policy-specific transforms는 compatibility registry에 노출한다.
- statistics: paired success difference, suite/task breakdown, bootstrap interval과 raw counts를 함께 기록한다.
- 검토 후 제외: training curve, model-size 우열 주장, aggregate 하나만 노출.

## 결정 로그

- status: resolved
- resolved: comparator는 π₀.₅-LIBERO이며 fallback model을 조용히 바꾸지 않는다.
- resolved: 호환되지 않는 cell이 생기면 OpenVLA denominator도 같은 paired set으로 축소하고 exclusion을 공개한다.

## Step 트리

- [ ] **step-1 — pi05-compatibility-probe**
  - Artifact: exact revision/checkpoint를 load해 camera/state/instruction→action을 내는 최소 probe.
  - Files: `experiments/152-paired-vla-comparison/probe_pi05.py`, lock/verify evidence, changeset.
  - Dependencies: 없음
  - Verify: sample cell에서 deterministic input mapping, finite 7D action과 latency를 기록한다.
  - Failure probe: wrong suite checkpoint, missing norm stats, action dimension mismatch가 FAIL한다.
  - Commit: changeset 1 — π₀.₅ compatibility probe.
- [ ] **step-2 — shared-policy-adapter-gate**
  - Artifact: OpenVLA/π₀.₅가 공통 observation/result contract를 만족하는 adapter와 parity report.
  - Files: policy adapter interface, validator/tests, changeset.
  - Dependencies: step-1
  - Verify: camera roles, state/action units, gripper convention, timing fields가 registry와 일치한다.
  - Failure probe: hidden transform, sign/scale drift, wrist-input relabel이 FAIL한다.
  - Commit: changeset 2 — paired adapter parity.
- [ ] **step-3 — pi05-sixty-cell-execution**
  - Artifact: π₀.₅ 60 canonical rollout과 resumable ledger.
  - Files: runner integration, `verify/pi05/`, changeset.
  - Dependencies: step-2
  - Verify: 60/60 terminal cells, canonical episode/hash, process/GPU cleanup PASS.
  - Failure probe: missing/duplicate cell, retry overwrite, policy/source relabel이 FAIL한다.
  - Commit: changeset 3 — full π₀.₅ run.
- [ ] **step-4 — paired-statistics**
  - Artifact: 같은 task-state key에서 두 정책을 join한 raw counts, difference와 interval report.
  - Files: comparison script/schema, `verify/paired-report.json`, changeset.
  - Dependencies: step-3
  - Verify: every included pair has two canonical episode refs and denominator is recomputable.
  - Failure probe: unpaired cell, Simpson-style suite omission, zero-denominator와 rounded-only metric가 FAIL한다.
  - Commit: changeset 4 — paired comparison statistics.
- [ ] **step-5 — fairness-and-claim-gate**
  - Artifact: compatibility, exclusions, retries, denominator와 claim boundary를 함께 검증한 GEN3 report.
  - Files: fairness validator, negative fixtures, changeset, final report.
  - Dependencies: step-1, step-2, step-3, step-4
  - Verify: spec/quality gate가 두 policy의 exact provenance와 paired evidence를 확인한다.
  - Failure probe: `general winner`, `same checkpoint`, hidden exclusion/retry 문구가 FAIL한다.
  - Commit: changeset 5 — fair paired VLA comparison.

## Verification / DoD

- 두 policy의 paired denominator, adapter 차이, exact provenance와 120 canonical episode가 한 comparison contract에서 검증된다.
