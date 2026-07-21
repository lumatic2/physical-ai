# PLAN — GEN2 OpenVLA 다과제 기준선

Status: approved — 2026-07-21 사용자 승인; 3-Horizon 전체 연쇄 실행

## Objective → Horizon → Milestone

- Objective: 정책 실행을 수치 비교와 재현 가능한 실험 증거로 끌어올린다. (`OBJECTIVE.md`)
- Horizon: 여러 과제에서 통하는 로봇 판단 실험실. (`plans/horizons/multitask-generalization-lab.md`)
- Milestone: GEN1의 60 OpenVLA cell을 실제 실행하고 중단·재개 가능한 canonical baseline으로 고정한다.

## Scope Boundary

- 포함: OpenVLA exact checkpoint, 12 task×5 state rollout, resumable runner, LAB1 episode/event export, baseline aggregate.
- 제외: π₀.₅ 실행, policy ranking, public UI, root-cause diagnosis.
- Execution mode: continuous
- Stop only: completed, blocked, decision_required, risk_gate, secret_required, user_stopped.
- Rollback/cleanup: WSL env/cache는 repo 밖, canonical output만 allowlist해 추적한다.

## planning_gate

```yaml
planning_gate:
  team_validation_mode: manual-pass
  scope_posture: selective
  delegation_decision:
    remote_background_agents: skip
    reason: "한 GPU runner의 순차 execution과 checkpoint가 핵심이라 병렬 writer가 이득이 없다."
  perspectives:
    product: "성공률보다 60개 분모와 대표 실패 evidence가 먼저 보인다."
    architecture: "기존 LAB1 writer와 LAB2 direct VLA emitter를 호출하고 복제하지 않는다."
    security: "checkpoint token·cache·절대경로를 public artifact에서 scrub한다."
    qa: "resume가 이미 완료된 run key를 재실행하지 않는다."
    skeptic: "OOM·environment error를 policy failure로 합산하지 않는다."
```

## 스캐폴딩 결정

- source-of-truth: GEN1 manifest + append-only run ledger + LAB1 LeRobot episode다.
- 검증: dry-run, resume fault injection, episode validator와 aggregate recomputation을 사용한다.
- 배포/운영: local WSL/GPU 실행만 하며 공개 배포는 GEN5까지 하지 않는다.
- runtime: Ubuntu WSL2 + local RTX 5090, exact OpenVLA/LIBERO revisions.
- 관측: wall latency, model latency, steps, termination, environment/infrastructure failure를 분리한다.
- 공개 경계: 이 milestone은 local canonical evidence까지만; 배포 없음.
- 검토 후 제외: retry로 성공률 보정, failed episode 삭제, checkpoint fine-tuning.

## 결정 로그

- status: resolved
- resolved: environment/infrastructure error는 denominator와 별도 집계하고 동일 run key를 재시도 로그로 연결한다.
- resolved: policy outcome은 첫 valid attempt를 기준으로 하며 숨은 재시도를 금지한다.

## Step 트리

- [ ] **step-1 — manifest-driven-runner**
  - Artifact: GEN1 cell을 읽어 단일 OpenVLA rollout을 재현하는 CLI.
  - Files: `experiments/151-openvla-multitask-baseline/run_baseline.py`, config/tests, changeset.
  - Dependencies: 없음
  - Verify: dry-run이 정확히 60 OpenVLA cell과 실행 순서를 출력한다.
  - Failure probe: manifest 밖 task/state 요청과 revision mismatch가 실행 전에 FAIL한다.
  - Commit: changeset 1 — manifest-driven runner.
- [ ] **step-2 — resumable-run-ledger**
  - Artifact: task-state 단위 atomic checkpoint, retry linkage와 idempotent resume.
  - Files: run ledger module/schema/tests, changeset.
  - Dependencies: step-1
  - Verify: 강제 중단 뒤 resume가 completed cell을 건너뛰고 partial cell만 재실행한다.
  - Failure probe: duplicate completion, partial artifact promotion, retry 숨김이 FAIL한다.
  - Commit: changeset 2 — resumable execution ledger.
- [ ] **step-3 — canonical-episode-export**
  - Artifact: 각 valid rollout의 LAB1 LeRobot episode와 direct VLA causal event.
  - Files: LAB1/LAB2 adapter extensions, `verify/episodes/`, changeset.
  - Dependencies: step-1, step-2
  - Verify: camera/state/action/timestamp/outcome과 raw→executed action link가 모든 frame에 존재한다.
  - Failure probe: camera relabel, missing action link, local path leak가 FAIL한다.
  - Commit: changeset 3 — canonical baseline evidence.
- [ ] **step-4 — sixty-cell-execution**
  - Artifact: 60 OpenVLA canonical rollout과 complete run ledger.
  - Files: `verify/canonical/manifest.json`, episode/result artifacts, changeset.
  - Dependencies: step-3
  - Verify: 60/60 cells terminal state, valid attempt와 infra error 분리, process/GPU cleanup PASS.
  - Failure probe: missing/duplicate cell과 corrupt episode hash가 aggregate 전에 FAIL한다.
  - Commit: changeset 4 — full OpenVLA baseline run.
- [ ] **step-5 — baseline-aggregate-gate**
  - Artifact: suite/task success, steps, latency, outcome와 representative PASS/FAIL을 묶은 GEN2 report.
  - Files: aggregate script, `verify/baseline-report.json`, changeset, final report.
  - Dependencies: step-4
  - Verify: aggregate denominator가 run ledger에서 재계산되고 raw episode로 역추적된다.
  - Failure probe: 실패 누락, retry 성공 덮어쓰기, infra error를 policy failure로 relabel하면 FAIL한다.
  - Commit: changeset 5 — verified OpenVLA baseline.

## Verification / DoD

- OpenVLA 60 cell이 중단·재개 가능한 runner로 실행되고 aggregate에서 모든 canonical episode까지 추적된다.
