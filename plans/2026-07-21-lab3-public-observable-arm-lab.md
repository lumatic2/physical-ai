# PLAN — LAB3 공개 관찰형 로봇팔 실험실

Status: approved 2026-07-21 — Horizon 전체 연쇄 실행 승인
Supersedes: `plans/2026-07-20-lab3-public-robot-arm-laboratory.md`

> LeRobot Dataset Visualizer의 검증된 동기화 패턴을 현재 Vite/React 실험실에 선택 이식하는 후속 실행안이다.

## 북극성 → Horizon → Milestone → Step

- **북극성**: 카메라와 센서로 세상을 보고, 언어 지시를 이해하고, 로봇 행동을 생성·실행하며, 그 전 과정을 사람이 관찰할 수 있는 피지컬 AI 실험실. (← `OBJECTIVE.md`)
- **Horizon**: 보고 판단하고 움직이는 로봇팔 실험실. (← `plans/horizons/see-understand-act-robot-lab.md`)
- **Milestone**: LAB1 episode와 LAB2 causal trace를 누구나 브라우저에서 재생·검증할 수 있는 대표 제품 화면으로 만드는 LAB3.
- **리서치 입력**: `experiments/147-camera-action-episode-contract/verify/official-viewer-reuse/README.md`의 배포 UI·Rerun·Foxglove probe.

## Scope Boundary

- 결정: 기존 `experiments/03-digital-twin/web` Vite/React 앱 안에 dual video, 공통 playback, synchronized chart cursor 패턴을 선택 이식하고 `관찰 → 판단 → 행동 → 결과` 인과 화면을 추가한다.
- 포함: 정적 asset bundle, dual-camera player, instruction, timeline scrub, state/action chart, provenance/evidence drawer, 반응형 공개 배포.
- 제외: LeRobot Dataset Visualizer 전체 fork, dataset-cleaning UI, 로그인, DB, live GPU backend, Foxglove public dependency, real/live claim.
- Execution mode: `continuous`
- Stop only: completed, blocked, decision_required, risk_gate, secret_required, external_authority_required, user_stopped.
- Rollback/cleanup: 새 화면은 route·asset registry 단위로 분리해 기존 workbench를 보존하고 changeset별 revert가 가능하게 한다. dev server와 browser session을 종료하고 미사용 대용량 media를 제거한다.

## planning_gate

- team_validation_mode: `manual-pass`
- scope_posture: `reduction` — 공식 UI의 필요한 상호작용만 이식하고 전체 앱·backend·정리 도구는 제외한다.
- delegation_decision: `skip` — 화면 구조와 재사용 경계가 probe screenshot/source audit로 고정되어 plan 단계 병렬 분해가 필요하지 않다.
- spec_delta: public UI source-of-truth를 LAB1 LeRobot episode + LAB2 causal trace의 정적 파생 bundle로 명시하고 공식 viewer interaction reuse를 DESIGN에 반영한다.
- product: 첫 화면에서 scene camera, wrist camera, instruction, 현재 판단/행동, 결과를 동시에 읽고 timeline을 움직여 원증거까지 내려갈 수 있어야 한다.
- architecture: 공개 앱은 결정론적 정적 replay이며 canonical episode를 직접 수정하지 않는다.
- security: 공개 bundle allowlist, path/token scrub, content hash와 size budget을 배포 전 검사한다.
- qa: local/live Playwright, desktop/mobile visual smoke, keyboard playback, invalid source/timestamp/claim negative fixture를 실행한다.
- skeptic: recorded simulation을 live digital twin처럼 보이게 하지 않고 camera label도 실제 provenance에 맞춘다.

## 스캐폴딩 결정

- source-of-truth: LAB1 LeRobot episode와 LAB2 event trace가 정본이며 `assets/arm-lab` registry는 공개용 파생물이다.
- 검증: converter unit test, asset hash/size gate, local/live Playwright, desktop/mobile screenshot, `qaArmLabSummary()`와 claim negative smoke.
- 배포/운영: 기존 Vercel static 배포 경로를 사용하고 backend를 추가하지 않는다. canonical raw artifact는 크기와 공개 안전 gate를 통과한 링크만 노출한다.
- frontend: 기존 Vite/React/Tailwind/shadcn 앱과 Recharts를 유지하고 Dataset Visualizer의 multi-video/playback/cursor 상호작용만 선택 이식한다.
- data: episode와 event를 content-hashed JSON/video bundle로 변환하며 변환 provenance와 canonical hash를 registry에 보존한다.
- design: dark laboratory workbench 안에서 dual camera를 1차 증거로, instruction과 현재 event를 2차 초점으로, graph/evidence를 검증 층으로 배치한다.
- 관측: selected timestep, playback state, event source, action/state values, artifact hash와 mode badge를 QA API로 노출한다.
- 검토 후 제외: backend·인증·DB·결제·실시간 스트리밍 — 공개 결과는 정적 recorded simulation replay다.

## 결정 로그

- status: resolved
- 기존 public workbench를 유지하고 LeRobot Dataset Visualizer 전체를 fork하지 않는다.
- synchronized multi-video, 공통 playback bar, chart cursor 패턴은 선택 이식하고 dataset-cleaning sidebar는 제외한다.
- Rerun은 내부 증거 재생 기준선, Foxglove는 선택적 개발 진단이며 public runtime dependency가 아니다.
- 화면은 `recorded simulation`을 명시하고 실제 model input이 아닌 camera를 model view로 부르지 않는다.
- free-form thought panel 대신 source-tagged structured event와 causal link를 표시한다.

## Step 트리

- [ ] **step-1 — public-evidence-bundle**
  - Artifact: LAB1/LAB2 canonical artifact를 content-hashed public JSON/video registry로 결정론적으로 변환하는 converter와 공개 안전 gate.
  - Files: `experiments/03-digital-twin/web/gen_arm_lab_manifest.py`, `experiments/03-digital-twin/web/assets/arm-lab/`, converter test와 `DESIGN.md`.
  - Dependencies: 없음
  - Start gate: LAB2 step-4의 two-lane comparison evidence가 완료된 뒤 실행한다.
  - Verify: 같은 입력은 byte-identical registry/hash를 만들고 모든 media/event reference가 존재하며 size budget과 secret/path scrub을 통과한다.
  - Failure probe: missing media, hash mismatch, absolute local path, token-like value, unsupported event source가 있으면 build 전에 FAIL한다.
  - Commit: changeset 1 — deterministic public arm-lab bundle.
- [ ] **step-2 — synchronized-dual-camera-player**
  - Artifact: 두 camera, instruction, 공통 playback controls, frame/time scrub과 state/action chart cursor가 동기화된 arm-lab 화면.
  - Files: `experiments/03-digital-twin/web/src/App.jsx`, `src/components/arm-lab/`, `src/index.css`, player QA.
  - Dependencies: step-1
  - Verify: play/pause/seek/frame-step이 두 video와 chart를 같은 timestep으로 이동시키고 keyboard·desktop·mobile smoke를 통과한다.
  - Failure probe: 한 camera나 chart timestamp를 어긋나게 한 fixture에서 synchronization QA가 FAIL한다.
  - Commit: changeset 2 — synchronized dual-camera replay.
- [ ] **step-3 — causal-timeline-evidence-drawer**
  - Artifact: `관찰 → 판단 → 행동 → 결과` timeline, direct VLA/VLM→skill mode badge, source/provenance detail과 raw evidence drawer.
  - Files: `experiments/03-digital-twin/web/src/components/arm-lab/`, `src/App.jsx`, `qa/arm_lab_check.mjs`, `qa/arm_lab_claim_check.mjs`.
  - Dependencies: step-2
  - Verify: selected event가 camera/chart timestep과 parent chain을 가리키고 `qaArmLabSummary()`가 source, mode, outcome, hashes를 반환한다.
  - Failure probe: hidden reasoning field, unknown source, broken parent, recorded/live 또는 simulation/real relabel fixture가 FAIL한다.
  - Commit: changeset 3 — causal timeline and evidence inspection.
- [ ] **step-4 — public-reviewer-gate**
  - Artifact: 배포된 arm-lab route, local/live 증거, desktop/mobile screenshots와 5분 reviewer checklist.
  - Files: `experiments/03-digital-twin/web/README.md`, deployment config, `verify/arm-lab/`, `ROADMAP.md`.
  - Dependencies: step-3
  - Verify: local/live Playwright에서 두 camera, instruction, scrub, timeline, graph, evidence link와 mode claim이 PASS하고 console error가 없다.
  - Failure probe: live build에서 asset 404, hash mismatch, 잘못된 claim badge, raw link 누락을 주입하면 reviewer gate가 FAIL한다.
  - Commit: changeset 4 — public observable robot-arm laboratory.

## 검증/DoD

- **DoD**: 공개 브라우저에서 main/wrist camera, instruction, decision/action/result timeline과 state/action graph를 같은 시간축으로 scrub하고, 각 event의 source·causal link·raw evidence와 `recorded simulation` 경계를 확인할 수 있다.

## finding 큐

- full Dataset Visualizer local source의 Recharts 실패는 fork 회피 근거로만 유지한다. 선택 이식 중 동일 오류가 재현되면 현재 앱 버전에 맞는 최소 cursor adapter로 제한한다.
