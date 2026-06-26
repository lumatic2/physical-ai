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

## Current Horizon

<!-- harness:goal id="interactive-physics-diagnostics" -->
목표: command input과 MuJoCo runtime readout을 사람이 읽을 수 있는 debug UI와 timeline evidence로 연결한다.

## Active Milestones

<!-- harness:milestone id="M38" status="completed" priority="P2" evidence="experiments/139-contact-readout-interpretation/verify/contact-readout-interpretation.json" -->
### M38 - Contact Readout Interpretation Pass

- DoD: contact/readout 값이 어떤 claim을 지지하고 어떤 claim은 아직 지지하지 않는지 public copy와 QA evidence에 명시된다.
- Evidence: experiments/139-contact-readout-interpretation/verify/contact-readout-interpretation.json
- Gap: raw runtime field는 보이지만 리뷰어가 그 값을 physical AI claim으로 어떻게 읽어야 하는지 해석 레이어가 부족하다.
- Status: [x]
- Completed at: 2026-06-26
- Summary: Runtime readout interpretation is explicit in UI, public copy, and JSON/Markdown evidence; local/live boundary smoke PASS.
## Next Candidates
## Guardrails

- Assisted fixture evidence를 unassisted controller proof 또는 real robot telemetry로 쓰지 않는다.
- M30 visual-only 변경은 collision/contact/solver를 바꾸지 않고 `qaEnvironmentSummary().visualLayer.visualOnly === true`를 유지한다.
- M31부터만 physics/contact-bearing claim을 연다.
- Web mirror JSON은 derived다. canonical experiment edit은 `experiments/03-digital-twin/experiments.json`에서 시작하고 `sync_web.py`로 동기화한다.

## 대기 항목

- M7a 실물 bring-up: SO-101 2-arm 구매/배송/공간/카메라/조립 시간이 확보될 때만 LeRobot install, motor calibration, dataset capture, ACT baseline으로 이동한다.

## Archive Pointer

완료 이력은 `BACKLOG.md` 참조.
