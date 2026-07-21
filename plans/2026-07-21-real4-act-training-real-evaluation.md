# PLAN — REAL4 ACT 학습과 실물 평가

Status: approval-ready — 3-Horizon 연쇄 실행 승인 대기

## Objective → Horizon → Milestone
- Objective: consumer hardware에서 정책을 직접 학습·실행·비교한다.
- Horizon: `plans/horizons/sim-real-so101-evidence-loop.md`
- Milestone: 50 real demonstrations로 ACT를 학습하고 unseen-condition 30 episode를 안전하게 평가한다.

## Scope Boundary
- 포함: dataset split, ACT config/train, offline validation, guarded deployment, 30 real eval, safety/outcome report.
- 제외: SmolVLA/HIL, hyperparameter sweep, unattended evaluation, sim-real score equality.
- Start gate: REAL3 final report PASS.
- Execution mode: continuous
- Stop only: completed, blocked, decision_required, risk_gate, secret_required, user_stopped.
- Rollback/cleanup: checkpoint/config/data revisions를 보존하고 real rollout마다 motor power와 process를 정리한다.

## planning_gate
```yaml
planning_gate:
  team_validation_mode: manual-pass
  scope_posture: reduction
  delegation_decision: {remote_background_agents: skip, reason: "single-GPU training과 supervised real evaluation의 순차 safety chain이다."}
  safety: "operator와 physical stop 없이 policy action을 실물에 적용하지 않는다."
```

## 스캐폴딩 결정
- source-of-truth: REAL3 dataset revision, ACT config/checkpoint와 append-only real eval ledger다.
- 검증: split leakage, offline replay, action bound/dry-run, 30-episode denominator와 safety audit를 사용한다.
- 배포/운영: local tethered robot only; public control/checkpoint service 없음.
- training: LeRobot ACT baseline 하나, fixed config/seed와 checkpoint selection rule.
- evaluation: 3 initial-position strata×10 episodes, operator present, intervention/stop recorded.
- 검토 후 제외: best-of retry, failed run deletion, hyperparameter leaderboard, autonomous overnight run.

## 결정 로그
- status: resolved
- first real policy는 ACT이며 30 episode 완료 전 performance claim을 하지 않는다.

## Step 트리
- [ ] **step-1 — act-training-contract**
  - Artifact: dataset split, normalization, config, seed, checkpoint selection과 resource budget.
  - Files: `experiments/163-act-real-evaluation/training-contract/`, validator, changeset.
  - Dependencies: 없음
  - Verify: dataset/hash/config에서 training command가 재생성되고 split leakage 0이다.
  - Failure probe: eval leakage, mutable latest checkpoint, unpinned config가 FAIL한다.
  - Commit: changeset 1 — ACT training contract.
- [ ] **step-2 — act-training-run**
  - Artifact: fixed ACT training run, metrics, checkpoints와 selected model provenance.
  - Files: run manifest/metrics/checkpoint report, changeset.
  - Dependencies: step-1
  - Verify: training completion, finite metrics, selected checkpoint rule와 resource cleanup PASS.
  - Failure probe: cherry-picked checkpoint, missing seed, incomplete run relabel가 FAIL한다.
  - Commit: changeset 2 — trained ACT baseline.
- [ ] **step-3 — offline-and-dry-run-safety**
  - Artifact: held-out episode replay, action distribution/bounds와 motors-disabled dry-run report.
  - Files: offline eval/dry-run tools/evidence, changeset.
  - Dependencies: step-2
  - Verify: predicted actions finite/bounded and command adapter matches real joint/gripper semantics.
  - Failure probe: sign/scale mismatch, NaN, out-of-workspace action가 motor enable을 차단한다.
  - Commit: changeset 3 — ACT deployment safety gate.
- [ ] **step-4 — thirty-real-evaluation-episodes**
  - Artifact: 30 unseen-condition real eval episodes with camera/state/action/outcome/safety events.
  - Files: eval dataset/ledger/canonical evidence, changeset.
  - Dependencies: step-3
  - Verify: 30/30 terminal attempts across 3 strata and all interventions/retries accounted.
  - Failure probe: best-of rerun, missing failure, unsafe continuation after stop가 FAIL한다.
  - Commit: changeset 4 — guarded real policy evaluation.
- [ ] **step-5 — real-policy-evidence-gate**
  - Artifact: raw success count, strata, latency, intervention/safety와 representative episodes를 묶은 REAL4 report.
  - Files: aggregate/verifier/report, changeset, final report.
  - Dependencies: step-1, step-2, step-3, step-4
  - Verify: denominator recomputation, episode hashes, operator/safety and cleanup PASS.
  - Failure probe: teleop-assisted success를 autonomous로 표시, failure omission, sim score comparison가 FAIL한다.
  - Commit: changeset 5 — verified ACT real evaluation.

## Verification / DoD
- ACT가 30 real episodes에서 안전·intervention·모든 outcome을 포함한 canonical evidence로 평가된다.
