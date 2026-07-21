# PLAN — REAL1 SO-101 획득·안전 준비

Status: approval-ready — 3-Horizon 연쇄 실행 승인 대기; hardware external gate

## Objective → Horizon → Milestone
- Objective: 시뮬레이션 증거를 실물 telemetry와 안전 게이트로 연결한다.
- Horizon: `plans/horizons/sim-real-so101-evidence-loop.md`
- Milestone: 실제 hardware identity, 작업 공간과 물리 stop을 검증해 실물 동작 착수 조건을 닫는다.

## Scope Boundary
- 포함: BOM, 사용자 구매 gate, inventory, USB/power identity, workspace, E-stop, firmware/version readiness.
- 제외: 에이전트 자동 구매, calibration motion, teleop, dataset capture.
- Start gate: LIVE Horizon final report PASS + 사용자 hardware 구매·도착 확인.
- Execution mode: continuous
- Stop only: completed, blocked, decision_required, risk_gate, secret_required, external_authority_required, user_stopped.
- Rollback/cleanup: 구매는 사용자 소유이며 코드는 hardware에 write하기 전 read-only inventory로 시작한다.

## planning_gate
```yaml
planning_gate:
  team_validation_mode: manual-pass
  scope_posture: reduction
  delegation_decision: {remote_background_agents: skip, reason: "physical inventory와 safety gate는 사용자 현장 확인이 필요하다."}
  safety: "physical power cut와 workspace limit 없이는 motor enable을 금지한다."
```

## 스캐폴딩 결정
- source-of-truth: user-approved BOM, hardware inventory와 signed safety checklist다.
- 검증: read-only device inventory, physical stop test와 photo/video evidence checklist를 사용한다.
- 배포/운영: real hardware local only; remote/public control 없음.
- hardware: SO-101 leader/follower, front/wrist camera, stable power, physical cut와 bounded workspace.
- 관측: serial/port, firmware, calibration id, camera identity와 safety test timestamp를 기록한다.
- 검토 후 제외: 자동 결제, unattended motor enable, safety bypass.

## 결정 로그
- status: resolved
- 실제 구매·배송·공간 승인은 REAL1 직전 별도 external authority로 받는다.

## Step 트리
- [ ] **step-1 — approved-bom-and-acquisition-gate**
  - Artifact: 가격/공급처/부품/카메라/전원/stop/workspace를 가진 사용자 승인 BOM.
  - Files: `experiments/160-so101-acquisition-safety/bom.md`, gate checklist, changeset.
  - Dependencies: 없음
  - Verify: 모든 필수 품목과 사용자 승인/도착 상태가 명시된다.
  - Failure probe: 승인 없는 구매 명령, missing stop/camera/leader가 FAIL한다.
  - Commit: changeset 1 — approved SO-101 acquisition contract.
- [ ] **step-2 — hardware-identity-inventory**
  - Artifact: leader/follower/camera/power의 serial, port와 physical label inventory.
  - Files: inventory tool/schema/evidence, changeset.
  - Dependencies: step-1
  - Verify: reconnect 후 stable id mapping과 no duplicate device PASS.
  - Failure probe: port-only identity, swapped leader/follower, unknown camera가 FAIL한다.
  - Commit: changeset 2 — hardware identity inventory.
- [ ] **step-3 — workspace-and-power-safety**
  - Artifact: reach envelope, keep-out zone, cable/power/physical cut와 manual recovery checklist.
  - Files: safety contract/test evidence, changeset.
  - Dependencies: step-2
  - Verify: physical stop test가 power/action을 제한 시간 안에 제거하고 restart는 manual이다.
  - Failure probe: software-only stop, auto restart, unbounded workspace가 FAIL한다.
  - Commit: changeset 3 — physical workspace and stop gate.
- [ ] **step-4 — firmware-and-config-lock**
  - Artifact: LeRobot revision, firmware, motor limits, camera config와 host environment lock.
  - Files: config lock/validator/report, changeset.
  - Dependencies: step-3
  - Verify: read-only probe가 expected versions/limits를 확인한다.
  - Failure probe: unknown firmware, limit omission, camera fps/resolution drift가 FAIL한다.
  - Commit: changeset 4 — real hardware configuration lock.
- [ ] **step-5 — motor-enable-readiness-gate**
  - Artifact: identity/config/safety를 종합해 calibration motion 허용 여부를 결정한 REAL1 report.
  - Files: readiness verifier, evidence packet, changeset, final report.
  - Dependencies: step-1, step-2, step-3, step-4
  - Verify: user physical confirmation과 automated inventory/safety checks 모두 PASS.
  - Failure probe: any missing approval/device/stop/limit가 motor enable을 차단한다.
  - Commit: changeset 5 — SO-101 motor-enable readiness.

## Verification / DoD
- 사용자 승인 hardware와 물리 safety gate가 evidence로 확인된 뒤에만 calibration motion이 허용된다.
