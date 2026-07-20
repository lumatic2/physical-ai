# ROADMAP

> 이 레포의 마일스톤과 다음 증거 생산 계획. 포트폴리오 모드: 완료 기준은 "남이 5분 보고 납득한다"이다.
> 마지막 업데이트: 2026-07-21
> line budget: <=150

## 왜 이 레포

피지컬 AI 기초 지식을 실행 가능한 포트폴리오로 입증한다.

한 문장: "문헌과 정책 비교에서 출발해 -> 직접 실행과 디지털 트윈 evidence를 만들었고 -> 이제 카메라·센서·언어 지시가 행동으로 바뀌는 전 과정을 관찰 가능한 로봇팔 실험실로 통합한다."

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
| LAB3 | Public Robot Arm Laboratory | dual-camera와 decision/action/result timeline을 공개한다 | `experiments/149-public-robot-arm-laboratory` | pending |

## Current Horizon

<!-- harness:goal id="see-understand-act-robot-lab" -->
목표: 카메라·센서·언어 지시가 로봇 행동으로 변환되는 과정을 관찰·재생·검증 가능한 피지컬 AI 실험실로 만든다. (상세 → `plans/horizons/see-understand-act-robot-lab.md`)

## Active Milestones

<!-- harness:milestone id="LAB1" status="completed" priority="P0" evidence="archive/reports/2026-07-21-lab1-lerobot-episode-evidence.md" -->
### LAB1 — 카메라-행동 episode 계약

- DoD: 동일 과제의 PASS/FAIL episode가 main/wrist camera, raw state, instruction, raw/controller action, latency, termination/success를 versioned trace로 보존하고 clean rerun validator를 통과한다.
- Evidence: `archive/reports/2026-07-21-lab1-lerobot-episode-evidence.md`; changesets `20260721-lab1-canonical-contract-profile`, `20260721-lab1-libero-lerobot-writer`, `20260721-lab1-bounded-official-viewer-smoke`, `20260721-lab1-canonical-pass-fail-pair`
- Gap: 기존 LIBERO evaluator는 agentview와 action을 실행하지만 사람이 재생·감사할 episode evidence를 남기지 않는다.
- Scale: changesets>=3; surfaces: LIBERO producer, trace schema, canonical evidence; capability: 한 VLA episode를 camera부터 outcome까지 재현한다.
- Status: [x]

- Completed at: 2026-07-21
- Summary: 동일 과제의 실제 OpenVLA PASS·FAIL episode가 LeRobot·Rerun 검증을 통과했다.

<!-- harness:milestone id="LAB2" status="completed" priority="P1" evidence="archive/reports/2026-07-21-lab2-observable-causal-trace.md" -->
### LAB2 — 출처가 보이는 VLM/VLA 판단·행동 기록

- DoD: 계층형 VLM→skill과 direct VLA action episode가 동일 trace contract에서 실행되고 모든 event의 source·causal role·outcome이 검증되며 hidden-reasoning fixture가 거부된다.
- Evidence: `archive/reports/2026-07-21-lab2-observable-causal-trace.md`; changesets `20260721-lab2-provenance-event-contract`, `20260721-lab2-direct-vla-causal-emitter`, `20260721-lab2-vlm-bounded-skill-lane`, `20260721-lab2-two-lane-comparison-evidence`
- Gap: action은 실행되지만 VLM 관측, VLA action, controller 결과의 출처와 인과 경계가 보이지 않는다.
- Scale: changesets>=4; surfaces: VLM adapter, skill executor, VLA trace, provenance gate; capability: 판단과 행동의 실제 출처를 비교한다.
- Status: [x]

- Completed at: 2026-07-21
- Summary: Direct VLA와 VLM→scripted skill의 실제 PASS·FAIL source·assistance trace를 검증했다.
## Next Candidates

<!-- harness:milestone id="LAB3" status="pending" priority="P2" -->
### LAB3 — 공개 로봇팔 피지컬 AI 실험실

- DoD: 공개 사이트에서 main/wrist camera, instruction, source-tagged timeline을 재생·scrub하고 PASS/FAIL raw evidence로 추적하며 local/live QA가 claim boundary를 검증한다.
- Evidence: `experiments/149-public-robot-arm-laboratory/verify/`
- Gap: canonical episode가 생겨도 공개 UI와 reviewer evidence path가 없으면 피지컬 AI 제품으로 외부 증명되지 않는다.
- Scale: changesets>=4; surfaces: asset sync, React UI, replay timeline, live deploy; capability: 5분 안에 관측→판단→행동→결과를 이해한다.
- Status: [ ]

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
