# PLAN — LAB3 공개 로봇팔 피지컬 AI 실험실

Status: approved 2026-07-20

> 생성: 2026-07-20 · 갈래: product · scope 결정: dual-camera public replay, decision timeline, claim boundary와 live deploy까지
> milestone-레벨 durable plan doc. 진행 상태의 정본은 산출물 status machine과 `ROADMAP.md`다.

## 북극성 → horizon → milestone → step

- **북극성**: 피지컬 AI의 관측·이해·행동·결과를 외부 방문자가 직접 따라갈 수 있게 한다. (← `OBJECTIVE.md`)
- **horizon**: 보고 판단하고 움직이는 로봇팔 실험실 (← `plans/horizons/see-understand-act-robot-lab.md`)
- **milestone**: episode asset ingestion, multi-panel UI, synchronized replay, public QA/deploy를 가로지르는 통합 product capability이므로 milestone 규모다.

## Scope Boundary

- 결정: 기존 Robotics Lab Vite/React shell에 전용 arm laboratory view를 추가해 LAB1/LAB2 canonical episode를 공개하고 local/live evidence를 닫는다.
- Execution mode: `continuous`
- Stop only: completed, blocked, decision_required, risk_gate, secret_required, external_authority_required, user_stopped.
- 진행 보고: commentary only. 미완 leaf는 턴 종료점이 아니다.
- Rollback/cleanup: registry/asset sync, UI, QA/deploy changeset을 독립 revert하고 local Vite/Playwright child process를 종료한다.

## 스캐폴딩 결정

- source-of-truth: canonical episode/decision traces in experiments 147/148; public derived assets and UI under `experiments/03-digital-twin/web`.
- 검증: Vite build, trace asset validator, component/DOM summary, local/live Playwright smoke, actual browser visual inspection.
- 배포/운영: existing `deploy_vercel.py` and `robotics.askewly.com`; no new backend or secret names beyond the existing Vercel deployment path.
- 화면: one dedicated arm-lab view with main camera, wrist model-input camera, instruction/status, source-tagged timeline and evidence drawer.
- design: existing dark Robotics Lab tokens/shadcn primitives를 유지하되 camera feed와 trace가 우선이고 decorative overlay는 최소화한다.
- state: episode replay state stays local to the view; no new global store unless existing React composition requires it.
- 관측: `qaArmLabSummary()` exposes episode id, playback step, camera provenance, event counts, outcome, mode badges and evidence links.
- 검토 후 제외: DB·인증·결제·analytics — 공개 read-only evidence view이며 사용자 데이터가 없다.

## 결정 로그

- status: resolved
- 새 앱을 만들지 않고 기존 Robotics Lab shell과 배포 경로를 확장한다 — 스택 연속성과 사용자 승인 방향 2026-07-20.
- 첫 공개 버전은 recorded canonical evidence이며 local live inference를 가장하지 않는다 — 확정 2026-07-20.
- UI의 `생각` 표현은 structured source event만 사용하고 free-form chain-of-thought를 표시하지 않는다 — 확정 2026-07-20.

## Step 트리

- [ ] **step-1 — episode-asset-ingestion**
  - Artifact: canonical PASS/FAIL trace와 camera media를 public derived assets로 sync하는 deterministic pipeline.
  - Files: experiments 147/148 public manifests, `experiments/03-digital-twin/sync_web.py`, web assets/registry.
  - Dependencies: none
  - Verify: sync idempotence, content hashes, missing media/schema mismatch FAIL.
  - Failure probe: stale derived asset나 revision mismatch를 public registry가 거부한다.
  - Commit: changeset 1 — trace/media public ingestion.
- [ ] **step-2 — dual-camera-arm-lab-view**
  - Artifact: main camera, wrist model-input view, instruction/status, mode badges와 responsive layout.
  - Files: Vite/React app components/styles under `experiments/03-digital-twin/web`.
  - Dependencies: step-1
  - Verify: build + desktop/mobile DOM smoke; wrist camera provenance visible.
  - Failure probe: observer camera를 model input으로 바꾼 fixture가 UI/QA mismatch를 낸다.
  - Commit: changeset 2 — arm laboratory visual shell.
- [ ] **step-3 — synchronized-decision-timeline**
  - Artifact: scrub/play controls and source-tagged observation/decision/action/result events synchronized to camera playback.
  - Files: arm-lab replay state/components, `qaArmLabSummary()`, fixtures.
  - Dependencies: step-2
  - Verify: frame/time scrub updates both cameras and active event; PASS/FAIL episodes preserve identical evidence surfaces.
  - Failure probe: event timestep beyond media range or missing source fails QA.
  - Commit: changeset 3 — synchronized trace workbench.
- [ ] **step-4 — public-proof-and-live-gate**
  - Artifact: reviewer evidence drawer, README entry, local/live Playwright JSON, deployed public route.
  - Files: README, experiment 149 evidence, web QA, deploy evidence.
  - Dependencies: step-3
  - Verify: build; local/live smoke; browser visual audit; raw evidence links resolve; console errors empty.
  - Failure probe: `recorded evidence` missing, `real telemetry` overclaim, or raw evidence dead link fails claim-boundary smoke.
  - Commit: changeset 4 — public proof and deployment.

## 검증/DoD

- **DoD**: `robotics.askewly.com`에서 방문자가 main/wrist camera, instruction, source-tagged decision/action/result timeline을 재생·scrub하고 PASS/FAIL raw evidence까지 추적하며, local/live QA가 mode/claim boundaries를 검증한다.

## finding 큐

- camera media가 Vercel bundle budget을 넘으면 content-hashed external static asset route를 별도 decision gate로 올린다.

## 진행 로그

- 2026-07-20 사용자 방향 승인 후 계획 작성.
