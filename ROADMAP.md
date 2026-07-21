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

## Current Horizon

<!-- harness:goal id="multitask-generalization-lab" -->
목표: 사전 고정한 여러 과제·초기 상태에서 두 VLA를 같은 증거 계약으로 실행·비교하고 성공·실패 양상을 공개한다. (상세 → `plans/horizons/multitask-generalization-lab.md`)

## Active Milestones

<!-- harness:milestone id="GEN1" status="completed" priority="P0" evidence="archive/reports/2026-07-21-gen1-multitask-evaluation-contract.md" -->
### GEN1 — 고정된 다과제 평가 계약
- DoD: 12 task×5 initial state×2 policy의 120 cell이 task/state/policy revision과 immutable run key로 사전 고정되고 clean contract gate를 통과한다.
- Evidence: archive/reports/2026-07-21-gen1-multitask-evaluation-contract.md
- Gap: LAB3 한 과제의 evidence만으로는 평가 분모와 cherry-pick 부재를 입증하지 못한다.
- Scale: changesets>=5; surfaces: task manifest, initial states, policy registry, result schema, clean gate; capability: 실행 전 다과제 paired 평가 계약을 재현한다.
- Status: [x]

- Completed at: 2026-07-21
- Summary: 12 task×5 state×2 policy 평가 계약과 clean gate PASS
<!-- harness:milestone id="GEN2" status="completed" priority="P1" evidence="archive/reports/2026-07-21-gen2-openvla-multitask-baseline.md" -->
### GEN2 — OpenVLA 다과제 기준선
- DoD: GEN1의 OpenVLA 60 cell이 resumable runner로 실행되고 aggregate에서 모든 canonical episode까지 추적된다.
- Evidence: archive/reports/2026-07-21-gen2-openvla-multitask-baseline.md
- Gap: 고정된 평가 계약만 있고 실제 다과제 OpenVLA 분모와 재개 가능한 실행 증거가 없다.
- Scale: changesets>=5; surfaces: runner, run ledger, episode exporter, 60 rollouts, aggregate; capability: OpenVLA 다과제 기준선을 재실행한다.
- Status: [x]

- Completed at: 2026-07-21
- Summary: OpenVLA 60개 actual rollout과 aggregate gate PASS
<!-- harness:milestone id="GEN3" status="completed" priority="P2" evidence="archive/reports/2026-07-21-gen3-paired-vla-comparison.md" -->
### GEN3 — 두 VLA의 공정 비교
- DoD: π₀.₅-LIBERO 60 cell과 OpenVLA 기준선이 adapter·checkpoint 차이를 공개한 동일 paired denominator로 비교된다.
- Evidence: archive/reports/2026-07-21-gen3-paired-vla-comparison.md
- Gap: 한 정책 기준선만으로는 비교 플랫폼과 policy-family 차이를 입증하지 못한다.
- Scale: changesets>=5; surfaces: pi05 probe, adapter parity, 60 rollouts, paired stats, fairness gate; capability: 두 VLA를 공정한 paired contract로 비교한다.
- Status: [x]

- Completed at: 2026-07-21
- Summary: 두 VLA 60쌍의 실제 실행·paired 통계·공정성 경계를 완료했다.
<!-- harness:milestone id="GEN4" status="completed" priority="P3" evidence="experiments/153-observable-failure-patterns/verify/failure-coverage-report.json" -->
### GEN4 — 증거 기반 실패 양상
- DoD: 모든 non-success episode가 frame/event predicate를 가진 관측 가능한 양상 또는 `unknown`으로 완전 집계되고 원인 과장 fixture가 거부된다.
- Evidence: experiments/153-observable-failure-patterns/verify/failure-coverage-report.json
- Gap: 성공률만으로는 정책이 어떻게 실패했는지 원 episode에서 검토할 수 없다.
- Scale: changesets>=5; surfaces: taxonomy, feature extraction, classifier, reviewer sample, coverage gate; capability: 실패 한계를 근거와 함께 설명한다.
- Status: [x]

- Completed at: 2026-07-21
- Summary: 27/27 non-success: no_progress 6, unknown 21; reviewer evidence agreement 7/7, negative claim gate PASS.
<!-- harness:milestone id="GEN5" status="completed" priority="P4" evidence="archive/reports/2026-07-21-gen5-public-generalization-lab.md" -->
### GEN5 — 공개 일반화 비교 실험실
- DoD: 공개 사이트에서 120 episode의 paired 결과와 실패 양상을 보고 aggregate cell에서 LAB3 canonical episode까지 추적한다.
- Evidence: `archive/reports/2026-07-21-gen5-public-generalization-lab.md`
- Gap: local aggregate만으로는 제3자가 분모·차이·실패 evidence를 5분 안에 검토하지 못한다.
- Scale: changesets>=5; surfaces: public index, comparison UI, failure explorer, drill-down, live release; capability: 다과제 정책 비교를 공개 제품으로 증명한다.
- Status: [x]

- Completed at: 2026-07-21
- Summary: 60 paired cell·120 episode·27 failure를 공개하고 aggregate에서 LAB3 canonical episode까지 추적하는 production reviewer gate PASS.

## Next Candidates

- **연쇄 2/3:** 지시를 바꿔 실행하는 로컬 피지컬 AI 실험실 — `plans/horizons/live-instruction-execution-lab.md` (25 changeset; GEN Horizon 완료 후 승격)
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
