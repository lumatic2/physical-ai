# PLAN — REAL2 보정된 dual-camera teleoperation

Status: approved — 2026-07-21 사용자 승인; 3-Horizon 전체 연쇄 실행

## Objective → Horizon → Milestone
- Objective: 실물 camera/state/action을 동일 증거 계약으로 관찰한다.
- Horizon: `plans/horizons/sim-real-so101-evidence-loop.md`
- Milestone: leader/follower calibration과 front/wrist camera가 동기화된 안전 teleop trace를 만든다.

## Scope Boundary
- 포함: calibration, joint limits, camera calibration/sync, teleop, safety event와 trace quality.
- 제외: dataset 50회 수집, policy execution, public deploy.
- Start gate: REAL1 final report PASS.
- Execution mode: continuous
- Stop only: completed, blocked, decision_required, risk_gate, secret_required, user_stopped.
- Rollback/cleanup: calibration/config backup을 보존하고 motor power는 각 test 뒤 수동 off한다.

## planning_gate
```yaml
planning_gate:
  team_validation_mode: manual-pass
  scope_posture: selective
  delegation_decision: {remote_background_agents: skip, reason: "physical calibration과 teleop은 현장 순차 검증이다."}
  safety: "joint limit, stop event와 human spotter gate를 각 motion test에 적용한다."
```

## 스캐폴딩 결정
- source-of-truth: LeRobot calibration id, device inventory와 raw teleop trace다.
- 검증: joint-range replay, camera timestamp/sync, stop injection과 operator checklist를 사용한다.
- 배포/운영: local tethered operation only; network remote control 없음.
- cameras: fixed front는 scene view, wrist는 model/observer role을 명시한다.
- 관측: commanded/executed joint, leader input, stop/intervention, camera timestamp를 기록한다.
- 검토 후 제외: calibration auto-accept, wireless teleop, camera role 추정.

## 결정 로그
- status: resolved
- calibration과 camera sync quality gate 전에는 dataset recording을 시작하지 않는다.

## Step 트리
- [ ] **step-1 — leader-follower-calibration**
  - Artifact: stable LeRobot calibration ids와 joint range/zero evidence.
  - Files: `experiments/161-calibrated-teleoperation/calibration/`, verifier, changeset.
  - Dependencies: 없음
  - Verify: reconnect/reboot 후 joint mapping과 limits가 재현된다.
  - Failure probe: swapped ids, incomplete range, stale calibration가 FAIL한다.
  - Commit: changeset 1 — SO-101 calibration evidence.
- [ ] **step-2 — dual-camera-identity-sync**
  - Artifact: front/wrist identity, role, resolution/fps와 timestamp sync calibration.
  - Files: camera config/probe/evidence, changeset.
  - Dependencies: step-1
  - Verify: sampled motion event에서 두 camera sync delta가 budget 이하다.
  - Failure probe: camera swap, dropped timestamp, auto exposure blackout가 FAIL한다.
  - Commit: changeset 2 — real dual-camera sync.
- [ ] **step-3 — bounded-teleoperation-loop**
  - Artifact: leader input→bounded follower action→joint state loop와 raw trace.
  - Files: teleop adapter/trace schema/tests, changeset.
  - Dependencies: step-2
  - Verify: commanded/executed action link와 joint/gripper bounds PASS.
  - Failure probe: leader disconnect, rate spike, out-of-range action가 fail-closed다.
  - Commit: changeset 3 — bounded SO-101 teleoperation.
- [ ] **step-4 — stop-and-recovery-drills**
  - Artifact: operator stop, physical cut, obstruction와 reconnect recovery evidence.
  - Files: drill protocol/logs/report, changeset.
  - Dependencies: step-3
  - Verify: each stop prevents further executed action and restart is explicit/manual.
  - Failure probe: buffered action after stop, auto-enable, missing event가 FAIL한다.
  - Commit: changeset 4 — teleop stop and recovery drills.
- [ ] **step-5 — teleop-quality-gate**
  - Artifact: calibration/camera/action/safety가 있는 representative teleop episodes와 REAL2 report.
  - Files: `verify/teleop/`, quality validator, changeset, final report.
  - Dependencies: step-1, step-2, step-3, step-4
  - Verify: camera/state/action sync, bounds, stop and cleanup PASS.
  - Failure probe: blur/drop, missing action link, calibration drift가 dataset capture를 차단한다.
  - Commit: changeset 5 — calibrated teleoperation gate.

## Verification / DoD
- 보정된 SO-101 teleop이 dual-camera/state/action/safety trace로 재현되고 dataset capture gate를 통과한다.
