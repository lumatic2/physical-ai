# PLAN — LIVE5 로컬 실행형 실험실과 공개 증명

Status: pending current approval — 2026-07-21 계획 보강

## Objective → Horizon → Milestone
- Objective: 사람이 지시·정책·행동 전 과정을 관찰하는 피지컬 AI 실험실.
- Horizon: `plans/horizons/live-instruction-execution-lab.md`
- Milestone: VLM/VLA 역할이 구분되는 one-command local lab과 검증된 recorded public proof를 완성한다.

## Scope Boundary
- 포함: local launcher, task/policy controls, live panels, session history, recorded public gallery, local/live QA.
- 제외: public inference backend, remote action control, auth/DB.
- Start gate: LIVE4 final report PASS.
- Execution mode: continuous
- Stop only: completed, blocked, decision_required, risk_gate, secret_required, external_authority_required, user_stopped.
- Rollback/cleanup: local services를 launcher가 종료하고 public route/bundle은 독립 revert한다.

## planning_gate
```yaml
planning_gate:
  team_validation_mode: manual-pass
  scope_posture: selective
  delegation_decision: {remote_background_agents: skip, reason: "기존 LAB UI와 local runtime을 한 release chain에서 연결한다."}
  product: "지원 지시 선택→실행→관찰→기록 replay를 한 화면에서 이해한다."
  security: "public build는 localhost server endpoint와 secret을 포함하지 않는다."
```

## 스캐폴딩 결정
- source-of-truth: live session API와 promoted canonical recording registry다.
- 검증: launcher smoke, local Playwright, public recorded route asset/hash/claim gate를 사용한다.
- 배포/운영: local mode는 localhost services, public mode는 Vercel static recorded evidence다.
- frontend: 기존 arm-lab components에 supported instruction/execution-lane/session controls를 추가한다.
- design: live/recorded mode와 VLM/VLA/controller source를 강하게 분리하고 control 권한·stop state를 상시 표시한다.
- 검토 후 제외: public GPU proxy, arbitrary prompt input, background unattended run.

## 결정 로그
- status: resolved
- local 실행 UI와 public recorded UI를 같은 route가 아닌 명시적 mode/entry로 분리한다.
- 실행 방식은 OpenVLA, π₀.₅, Qwen3-VL→허용 기술의 세 레인으로 표시하고, 마지막 레인의 저수준 action은 scripted controller assistance임을 상시 노출한다.

## Step 트리
- [ ] **step-1 — one-command-local-launcher**
  - Artifact: env checks, policy server, session controller, stream과 web을 순서대로 띄우고 닫는 launcher.
  - Files: `experiments/159-interactive-local-lab/launcher/`, diagnostics/tests, changeset.
  - Dependencies: 없음
  - Verify: clean WSL/Windows에서 readiness와 cleanup smoke PASS.
  - Failure probe: port conflict, missing GPU/model, stale process가 actionable error로 FAIL한다.
  - Commit: changeset 1 — local laboratory launcher.
- [ ] **step-2 — instruction-lane-controls**
  - Artifact: supported task/instruction, execution lane, initial state와 start/pause/resume/stop controls.
  - Files: React controls/API adapter/QA, changeset.
  - Dependencies: step-1
  - Verify: UI state and server session transition/id match.
  - Failure probe: unsupported instruction, double start, stop 권한 상실이 FAIL한다.
  - Commit: changeset 2 — safe instruction and execution-lane controls.
- [ ] **step-3 — live-laboratory-panels**
  - Artifact: dual-camera, current VLM/VLA/controller source event, structured observation/skill, action/state, latency, health와 stop reason panels.
  - Files: live panels/styles/QA, changeset.
  - Dependencies: step-2
  - Verify: live summary sync/drop/source/health and desktop/mobile layout PASS.
  - Failure probe: chain-of-thought label, VLM/VLA source collapse, stale frame, recorded/live relabel이 FAIL한다.
  - Commit: changeset 3 — observable local lab UI.
- [ ] **step-4 — recorded-session-gallery**
  - Artifact: promoted sessions를 public static bundle과 LAB drill-down으로 보여주는 gallery.
  - Files: public bundle generator/route/QA, changeset.
  - Dependencies: step-3
  - Verify: public build has no localhost endpoint and all sessions link canonical hashes.
  - Failure probe: live badge, secret/path leak, missing failure session가 FAIL한다.
  - Commit: changeset 4 — public recorded session proof.
- [ ] **step-5 — interactive-reviewer-release**
  - Artifact: local operator checklist, public route, screenshots, release gate와 LIVE5 report.
  - Files: `verify/interactive-lab/`, deployment docs, changeset, final report.
  - Dependencies: step-1, step-2, step-3, step-4
  - Verify: human local run, local/live Playwright, asset/console/network/claim gates PASS.
  - Failure probe: public control exposure, mode ambiguity, stale recording hash가 release를 차단한다.
  - Commit: changeset 5 — interactive local physical AI laboratory.

## Verification / DoD
- 사용자가 local에서 지시·실행 레인을 선택해 실제 VLM/VLA inference를 실행·중단·관찰·기록하고 public에서는 검증된 recording만 본다.
