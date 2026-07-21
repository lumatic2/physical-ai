# ROADMAP

> 이 레포의 마일스톤과 다음 증거 생산 계획. 포트폴리오 모드: 완료 기준은 "남이 5분 보고 납득한다"이다.
> 마지막 업데이트: 2026-07-21
> line budget: <=150

## 왜 이 레포

피지컬 AI 기초 지식을 실행 가능한 포트폴리오로 입증한다.

한 문장: "단일 로봇팔 과제의 관찰 가능한 증거에서 출발해 -> 사전 고정한 여러 과제·초기 상태에서 두 VLA를 실행·비교하고 -> 성공과 실패 양상을 원 episode까지 검증하는 공개 실험 플랫폼으로 확장한다."

노출면: GitHub README, askewly 블로그, `~/vault/`, live demo `robotics.askewly.com`.

## 마일스톤 한눈에

| # | 목표군 | 입증하는 것 | showable artifact | 상태 |
|---|---|---|---|---|
| M1-M26 | 기초/정책/디지털 트윈 foundation | 문헌, 학습, replay, controller, workbench gate | docs, experiments, QA JSON | 완료/압축 |
| M27 | Robotics Lab shadcn UI Shell | React/Tailwind/shadcn shell + preserved MuJoCo runtime | `experiments/128-robotics-lab-ui-shell` | 완료 |
| M28 | Digital Twin Laboratory Environment Controls | 3개 environment preset + grounding/contact summary | `experiments/129-digital-twin-lab-environment` | 완료 |
| M29 | Public drift audit | 공개 claim drift 점검 | `experiments/130-public-drift-audit` | 완료/백로그 |
| M30 | Visual Lab Scenes | preset이 색만 바뀌는 수준을 넘어 공간으로 보인다 | `experiments/131-visual-lab-scenes` | 완료 |
| M31 | Physical Rough Terrain Scene | rough preset이 실제 contact-bearing scene variant로 연결된다 | `experiments/132-physical-rough-terrain-scene` | 완료 |
| M32 | Asset-backed Lab Shell | GLB/glTF asset 기반 실험실 shell을 넣을 수 있다 | `experiments/133-asset-backed-lab-shell` | 완료 |
| M33 | User-controllable Digital Twin | 입력이 policy command를 바꾸는 것을 UI/QA로 보인다 | `experiments/134-user-controllable-digital-twin` | 완료 |
| M34 | MuJoCo Contact/Force Readout Probe | contact/force claim을 runtime readout 가능성으로 검증한다 | `experiments/135-mujoco-contact-force-readout` | 완료 |
| M35 | Public Evidence Story Refresh | 최신 evidence와 claim boundary를 public story로 정리한다 | `experiments/136-public-evidence-refresh` | 완료 |
| M36 | Physics Diagnostics Panel | runtime readout을 debug UI에서 사람이 읽을 수 있게 한다 | `experiments/137-physics-diagnostics-panel` | 완료 |
| M37 | Command-to-Contact Timeline Smoke | command와 runtime readout을 같은 시간축 evidence로 묶는다 | `experiments/138-command-contact-timeline` | 완료 |
| M38 | Contact Readout Interpretation Pass | runtime readout claim의 지지/비지지 범위를 공개 문구로 분리한다 | `experiments/139-contact-readout-interpretation` | 완료 |
| M39 | Environment Scenario Manifest | 환경 preset을 재현 가능한 scenario contract로 승격한다 | `experiments/140-environment-scenario-manifest` | 완료 |
| M40 | Multi-Robot Environment Matrix | 여러 로봇이 같은 환경 scenario contract로 비교된다 | `experiments/141-multi-robot-environment-matrix` | 완료 |
| M41 | Interactive Obstacle Scene | static curb를 넘어 obstacle/contact task scene을 연다 | `experiments/142-interactive-obstacle-scene` | 완료 |
| M42 | Randomized Episode Scorecard | scenario가 여러 perturbation episode로 평가된다 | `experiments/143-randomized-episode-scorecard` | 완료 |
| M43 | Randomized Episode Comparison | baseline 대비 perturbation drift를 비교한다 | `experiments/144-randomized-episode-comparison` | 완료 |
| M44 | G1 Contact Body & Flicker Fix | G1 넘어짐 충돌과 visual floor flicker를 바로잡는다 | `experiments/145-g1-contactbody-flicker-fix` | 완료 |
| M45 | Real Robot Collision Contract | 실제 로봇 충돌 readiness를 sensor/stop-gate contract로 분리한다 | `experiments/146-real-robot-collision-contract` | 완료 |
| LAB1 | Camera-to-Action Episode Contract | dual-camera/state/instruction/action/outcome을 한 trace로 보존한다 | `experiments/147-camera-action-episode-contract` | 완료 |
| LAB2 | Observable Decision/Action Trace | VLM/VLA/controller event의 출처와 인과 경계를 검증한다 | `experiments/148-observable-decision-action-trace` | 완료 |
| LAB3 | Public Robot Arm Laboratory | dual-camera와 decision/action/result timeline을 공개한다 | `experiments/03-digital-twin/web/verify/arm-lab` | 완료 |
| GEN1 | Fixed Multitask Evaluation Contract | 12 task×5 state×2 policy의 평가 분모를 사전 고정한다 | `experiments/150-multitask-evaluation-contract` | 완료 |
| GEN2 | OpenVLA Multitask Baseline | OpenVLA 60 episode의 재개 가능한 기준선을 만든다 | `experiments/151-openvla-multitask-baseline` | 완료 |
| GEN3 | Paired VLA Comparison | OpenVLA와 π₀.₅-LIBERO를 같은 paired contract로 비교한다 | `experiments/152-paired-vla-comparison` | 완료 |
| GEN4 | Observable Failure Patterns | 실패를 원인 추정 없이 관측 가능한 양상으로 분류한다 | `experiments/153-observable-failure-patterns` | 완료 |
| GEN5 | Public Generalization Lab | aggregate에서 canonical episode까지 추적하는 공개 화면을 배포한다 | `experiments/154-public-generalization-lab` | 완료 |
| LIVE1 | Unified Inference Server | 세 실행 레인을 공통 localhost 계약과 단일 GPU lease로 제공한다 | `experiments/155-unified-policy-server` | 진행 중 |
| LIVE2 | Safe Experiment Session | 지원 지시와 실행 레인을 안전한 session으로 실행한다 | `experiments/156-safe-experiment-session` | 대기 |
| LIVE3 | Observable Live Stream | dual-camera와 VLM/VLA/controller event를 실시간 정렬한다 | `experiments/157-observable-live-stream` | 대기 |
| LIVE4 | Session Recording Promotion | live session을 canonical replay로 승격한다 | `experiments/158-session-recording-promotion` | 대기 |
| LIVE5 | Interactive Local Lab | 로컬 실행 UI와 공개 recorded proof를 완성한다 | `experiments/159-interactive-local-lab` | 대기 |

## Current Horizon

<!-- harness:goal id="live-instruction-execution-lab" -->
목표: 지원 지시와 실행 레인을 선택해 local GPU inference를 실제 실행하고, VLM·VLA·controller의 서로 다른 역할을 실시간 관찰과 canonical recording으로 연결한다. (상세 → `plans/horizons/live-instruction-execution-lab.md`)

## Active Milestones

<!-- harness:milestone id="LIVE1" status="active" priority="P0" -->
### LIVE1 — 통합 로컬 inference server
- DoD: OpenVLA·π₀.₅·Qwen3-VL 세 실행 레인이 exact revision, 공통 localhost envelope, exclusive GPU lease와 fail-closed lifecycle로 실제 inference를 제공한다.
- Evidence: `archive/reports/2026-07-21-live1-unified-inference-server.md`
- Gap: GEN 실행기는 batch 전용이라 사용자가 선택한 지시·실행 레인을 안전한 live session으로 제공하지 못한다.
- Scale: changesets>=6; surfaces: envelope, three adapters, GPU lease/supervisor, cross-lane gate; capability: 세 로컬 inference 레인을 안전한 공통 계약으로 제공한다.
- Status: [ ]

<!-- harness:milestone id="LIVE2" status="pending" priority="P1" -->
### LIVE2 — 안전한 실험 session 제어
- DoD: 두 task×두 instruction form×세 실행 레인의 12 session이 pause/stop/timeout/action limit와 cleanup gate를 통과한다.
- Evidence: `archive/reports/2026-07-21-live2-safe-experiment-session.md`
- Gap: inference endpoint만으로는 지원 지시 해석, 환경 lifecycle, operator control과 action safety를 보장하지 못한다.
- Scale: changesets>=5; surfaces: instruction catalog, state machine, action safety, fault smoke, 12-session gate; capability: 지시를 바꾼 local session을 fail-closed로 실행한다.
- Status: [ ]

<!-- harness:milestone id="LIVE3" status="pending" priority="P2" -->
### LIVE3 — 실시간 관찰 stream
- DoD: 실제 session의 dual-camera·state·VLM/VLA/controller event가 source와 timestamp를 보존한 read-only browser stream으로 관찰된다.
- Evidence: `archive/reports/2026-07-21-live3-observable-live-stream.md`
- Gap: 실행 로그만으로는 사용자가 로봇이 보고 판단하고 움직이는 순간을 한 화면에서 이해하지 못한다.
- Scale: changesets>=5; surfaces: stream schema, dual camera, event alignment, browser subscriber, live gate; capability: live physical-AI loop를 source별로 관찰한다.
- Status: [ ]

<!-- harness:milestone id="LIVE4" status="pending" priority="P3" -->
### LIVE4 — 실행 기록과 replay 승격
- DoD: valid live session이 LAB canonical episode로 원자적 승격되고 partial/failure와 live-replay hash·summary 관계가 검증된다.
- Evidence: `archive/reports/2026-07-21-live4-session-recording-promotion.md`
- Gap: 실시간 화면만으로는 제3자가 재현·감사할 수 있는 포트폴리오 증거가 남지 않는다.
- Scale: changesets>=5; surfaces: recorder, recovery, promotion, equivalence, representative bundle; capability: live 실행을 재현 가능한 증거로 고정한다.
- Status: [ ]

<!-- harness:milestone id="LIVE5" status="pending" priority="P4" -->
### LIVE5 — 로컬 실행형 실험실과 공개 증명
- DoD: one-command local UI에서 지시·실행 레인을 선택해 실행·중단·관찰·기록하고, public route는 검증된 recording만 claim boundary와 함께 공개한다.
- Evidence: `archive/reports/2026-07-21-live5-interactive-local-lab.md`
- Gap: 앞 단계의 서비스와 증거를 사용자가 이해할 수 있는 하나의 실험실 제품과 외부 증명으로 묶어야 한다.
- Scale: changesets>=5; surfaces: launcher, controls, live panels, recorded gallery, release gate; capability: 지시를 바꿔 실제 실행하는 피지컬 AI 실험실을 시연한다.
- Status: [ ]

## Next Candidates

- **연쇄 3/3:** 시뮬레이션과 실물을 잇는 SO-101 검증 — `plans/horizons/sim-real-so101-evidence-loop.md` (25 changeset; hardware external gate)

## Guardrails

- Assisted fixture evidence를 unassisted controller proof 또는 real robot telemetry로 쓰지 않는다.
- M30 visual-only 변경은 collision/contact/solver를 바꾸지 않고 `qaEnvironmentSummary().visualLayer.visualOnly === true`를 유지한다.
- M31부터만 physics/contact-bearing claim을 연다.
- Web mirror JSON은 derived다. canonical experiment edit은 `experiments/03-digital-twin/experiments.json`에서 시작하고 `sync_web.py`로 동기화한다.
- VLM 설명을 VLA의 숨은 생각으로 표시하지 않는다. 모든 event는 실제 source와 component를 가진다.
- recorded episode를 live inference로, simulation을 real telemetry로 표시하지 않는다.

## 대기 항목

- M7a 실물 bring-up: SO-101 2-arm 구매/배송/공간/카메라/조립 시간이 확보될 때만 LeRobot install, motor calibration, dataset capture, ACT baseline으로 이동한다.

## Archive Pointer

완료 이력은 `docs/BACKLOG.md` 참조.
