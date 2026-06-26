# ROADMAP

> 이 레포의 마일스톤과 다음 증거 생산 계획. 포트폴리오 모드: 완료 기준은 "남이 5분 보고 납득한다"이다.
> 마지막 업데이트: 2026-06-26
> line budget: <=150

## 왜 이 레포

피지컬 AI 기초 지식을 실행 가능한 포트폴리오로 입증한다.

한 문장: "문헌과 이론을 읽었고 -> 직접 실험으로 검증했고 -> 브라우저에서 조작 가능한 로봇 정책 플랫폼을 만들었고 -> 이제 디지털 트윈 환경에서 로봇 skill과 scene evidence를 설계·학습·검증한다."

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

## Current Horizon

<!-- harness:goal id="environment-scenario-harness" -->
목표: 디지털 트윈 환경을 배경 preset이 아니라 scenario/parameter/matrix/obstacle/randomized episode evidence로 재현 가능한 실험 변수로 만든다.

## Active Milestones

<!-- harness:milestone id="M39" status="completed" priority="P0" evidence="experiments/140-environment-scenario-manifest/verify/environment-scenario-manifest.json" -->
### M39 - Environment Scenario Manifest

- DoD: `envScenario` id/seed/terrain/friction/lighting/obstacle parameters가 UI summary와 QA evidence에 노출된다.
- Evidence: experiments/140-environment-scenario-manifest/verify/environment-scenario-manifest.json
- Gap: 현재 환경은 preset 중심이라 friction, curb, lighting, obstacle 같은 실험 변수가 독립 contract로 남지 않는다.
- Status: [x]
- Completed at: 2026-06-26
- Summary: Scenario manifest/URL/UI/QA evidence가 `rough-curb-v1` contract를 local/live로 검증한다.
## Next Candidates

<!-- harness:milestone id="M40" status="completed" priority="P1" evidence="experiments/141-multi-robot-environment-matrix/verify/environment-matrix-smoke.json" -->
### M40 - Multi-Robot Environment Matrix

- DoD: G1/Go1/Spot의 flat/rough scenario summary가 같은 matrix evidence에 기록되고 각 row가 pass/fail/claim boundary를 가진다.
- Evidence: experiments/141-multi-robot-environment-matrix/verify/environment-matrix-smoke.json
- Gap: rough 환경 evidence가 G1 중심으로 강해졌지만 여러 로봇이 같은 환경 contract로 비교되지는 않는다.
- Status: [x]
- Completed at: 2026-06-26
- Summary: G1/Go1/Spot x flat/rough 6-row matrix가 local/live에서 scenario shape와 claim boundary를 검증한다.

<!-- harness:milestone id="M41" status="completed" priority="P2" evidence="experiments/142-interactive-obstacle-scene/verify/obstacle-scene-smoke.json" -->
### M41 - Interactive Obstacle Scene

- DoD: obstacle scenario가 active MJCF scene/visual marker/QA summary로 노출되고, static curb와 다른 obstacle contract가 검증된다.
- Evidence: experiments/142-interactive-obstacle-scene/verify/obstacle-scene-smoke.json
- Gap: 현재 rough terrain은 static curb lane이며, task-like obstacle/contact world가 없다.
- Status: [x]
- Completed at: 2026-06-26
- Summary: `g1-obstacle-walk`와 `obstacle-lane-v1`이 active MJCF obstacle geoms, UI status, local/live smoke evidence로 검증된다.

<!-- harness:milestone id="M42" status="completed" priority="P1" evidence="experiments/143-randomized-episode-scorecard/verify/randomized-episode-scorecard.json" -->
### M42 - Randomized Episode Scorecard

- DoD: seed 기반 episode profile이 command/noise perturbation을 실행하고 각 episode의 distance/height/fall/NaN/pass/score를 local/live evidence로 남긴다.
- Evidence: experiments/143-randomized-episode-scorecard/verify/randomized-episode-scorecard.json
- Gap: obstacle scene은 열렸지만 아직 같은 scenario 안에서 perturbation episode set과 scorecard가 없다.
- Status: [x]
- Completed at: 2026-06-26
- Summary: `obstacle-command-noise-v1` profile이 3개 command/control-noise episode를 local/live에서 실행하고 scorecard evidence로 검증한다.
## Guardrails

- Assisted fixture evidence를 unassisted controller proof 또는 real robot telemetry로 쓰지 않는다.
- M30 visual-only 변경은 collision/contact/solver를 바꾸지 않고 `qaEnvironmentSummary().visualLayer.visualOnly === true`를 유지한다.
- M31부터만 physics/contact-bearing claim을 연다.
- Web mirror JSON은 derived다. canonical experiment edit은 `experiments/03-digital-twin/experiments.json`에서 시작하고 `sync_web.py`로 동기화한다.

## 대기 항목

- M7a 실물 bring-up: SO-101 2-arm 구매/배송/공간/카메라/조립 시간이 확보될 때만 LeRobot install, motor calibration, dataset capture, ACT baseline으로 이동한다.

## Archive Pointer

완료 이력은 `BACKLOG.md` 참조.
