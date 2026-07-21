# PLAN — REAL5 sim-real 증거 비교와 공개 검토

Status: approved — 2026-07-21 사용자 승인; 3-Horizon 전체 연쇄 실행

## Objective → Horizon → Milestone
- Objective: simulation과 real robot 주장을 같은 증거 계약으로 구분해 외부 검증한다.
- Horizon: `plans/horizons/sim-real-so101-evidence-loop.md`
- Milestone: sim/real episode, calibration, safety와 policy outcome을 공개 comparison으로 연결한다.

## Scope Boundary
- 포함: public allowlist bundle, sim/real schema comparison, real episode drill-down, safety/calibration evidence, release gate.
- 제외: remote robot control, live real camera, digital-twin fidelity claim, real/sim success rate direct ranking.
- Start gate: REAL4 final report PASS.
- Execution mode: continuous
- Stop only: completed, blocked, decision_required, risk_gate, secret_required, external_authority_required, user_stopped.
- Rollback/cleanup: real identifiers/privacy를 scrub하고 static route/bundle 단위로 revert한다.

## planning_gate
```yaml
planning_gate:
  team_validation_mode: manual-pass
  scope_posture: selective
  delegation_decision: {remote_background_agents: skip, reason: "safety/privacy review와 public release를 한 chain에서 검증한다."}
  security: "serial, workspace, face/voice, token과 local path를 public bundle에서 제거한다."
  skeptic: "schema compatibility를 digital twin fidelity로 표현하지 않는다."
```

## 스캐폴딩 결정
- source-of-truth: REAL1~REAL4 final reports와 allowlisted canonical sim/real episode registry다.
- 검증: privacy/path scrub, schema/claim negative fixture, local/live Playwright와 human review를 사용한다.
- 배포/운영: existing Vercel static route; real robot에 대한 inbound connection 없음.
- frontend: LAB episode player를 재사용하고 sim/real source, calibration/safety/outcome 차이를 병렬 표시한다.
- 관측: evidence coverage, dataset/checkpoint/calibration revisions와 real evaluation denominator를 노출한다.
- 검토 후 제외: 실시간 real stream, remote control, fidelity score, raw serial/workspace media.

## 결정 로그
- status: resolved
- public proof는 recorded real evidence이며 sim-real 동일성 대신 공통 schema와 다른 claim boundary를 보여준다.

## Step 트리
- [ ] **step-1 — privacy-safe-public-bundle**
  - Artifact: sim/real reports와 selected episodes를 content-hashed allowlist로 변환하는 generator.
  - Files: `experiments/164-sim-real-public-evidence/gen_bundle.py`, assets/tests, changeset.
  - Dependencies: 없음
  - Verify: secret/path/serial/privacy scrub, hash/size/license gate PASS.
  - Failure probe: raw serial, local path, face/voice frame, missing consent가 FAIL한다.
  - Commit: changeset 1 — public sim-real evidence bundle.
- [ ] **step-2 — sim-real-schema-comparison-ui**
  - Artifact: common/different fields, source/claim level과 dataset denominators를 보이는 comparison.
  - Files: React route/components/styles/QA, changeset.
  - Dependencies: step-1
  - Verify: schema coverage와 source-specific fields가 registry와 일치한다.
  - Failure probe: fidelity/equivalence wording, hidden missing sensor, score ranking가 FAIL한다.
  - Commit: changeset 2 — honest sim-real comparison.
- [ ] **step-3 — real-episode-safety-drilldown**
  - Artifact: real dual-camera/action/outcome player와 calibration/safety/intervention evidence drawer.
  - Files: LAB player adapters/evidence drawer/QA, changeset.
  - Dependencies: step-2
  - Verify: selected real episode hashes, source, policy, intervention and safety events align.
  - Failure probe: assisted run relabel, calibration omission, real/live confusion가 FAIL한다.
  - Commit: changeset 3 — real robot evidence drill-down.
- [ ] **step-4 — sim-real-claim-gate**
  - Artifact: simulation/real/digital-twin/performance/privacy negative fixture suite.
  - Files: claim validator/fixtures/report, changeset.
  - Dependencies: step-3
  - Verify: supported recorded evidence claims PASS and overclaim fixtures FAIL.
  - Failure probe: identical physics, sim-to-real success equivalence, autonomous assisted run, live telemetry labels가 FAIL한다.
  - Commit: changeset 4 — sim-real claim boundary gate.
- [ ] **step-5 — public-real-reviewer-release**
  - Artifact: deployed route, desktop/mobile screenshots, human reviewer checklist와 REAL5/Horizon close report.
  - Files: `verify/sim-real/`, deployment/ROADMAP/reports, changeset.
  - Dependencies: step-1, step-2, step-3, step-4
  - Verify: human visual, local/live Playwright, asset/hash/privacy/console/network and claim gates PASS.
  - Failure probe: privacy leak, asset 404, wrong denominator/source/claim가 release를 차단한다.
  - Commit: changeset 5 — public SO-101 sim-real evidence laboratory.

## Verification / DoD
- 공개 브라우저가 sim과 real evidence를 같은 상위 계약·다른 claim level로 보여주고 real safety/outcome까지 추적한다.
