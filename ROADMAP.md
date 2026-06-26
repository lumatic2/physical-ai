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
| M33 | User-controllable Digital Twin | 입력이 policy command를 바꾸는 것을 UI/QA로 보인다 | `experiments/134-user-controllable-digital-twin` | active |
| M34 | MuJoCo Contact/Force Readout Probe | contact/force claim을 runtime readout 가능성으로 검증한다 | `experiments/135-mujoco-contact-force-readout` | pending |
| M35 | Public Evidence Story Refresh | 최신 evidence와 claim boundary를 public story로 정리한다 | `experiments/136-public-evidence-refresh` | pending |

## Current Horizon

<!-- harness:goal id="controllable-physics-evidence-workbench" -->
목표: Robotics Lab v2를 보기 좋은 scene에서 한 단계 올려, 사용자가 정책 command를 조작하고 MuJoCo runtime state/contact evidence로 그 결과를 읽을 수 있는 workbench로 만든다.

## Active Milestones

<!-- harness:milestone id="M33" status="completed" priority="P0" evidence="experiments/134-user-controllable-digital-twin/verify/control-smoke.json" -->
### M33 - User-controllable Digital Twin

- DoD: `g1-walk`에서 keyboard command 상태가 visible UI와 QA summary에 드러나고, local/live Playwright가 command down/release 변화를 검증한다.
- Evidence: experiments/134-user-controllable-digital-twin/verify/control-smoke.json
- Gap: 방향키 command 조작은 구현됐지만 첫 방문자가 "내 입력이 policy command를 바꾼다"를 UI와 evidence로 즉시 확인하기 어렵다.
- Status: [x]

- Completed at: 2026-06-26
- Summary: Policy command UI and local/live keyboard control smoke PASS for g1-walk.
## Next Candidates

<!-- harness:milestone id="M34" status="pending" priority="P1" evidence="experiments/135-mujoco-contact-force-readout/verify/contact-readout-probe.json" -->
### M34 - MuJoCo Contact/Force Readout Probe

- DoD: `mujoco-js` runtime에서 노출 가능한 `ncon`/contact/force/sensor 값을 read-only probe로 확인하고, 가능하면 debug-only QA summary에 연결한다.
- Evidence: experiments/135-mujoco-contact-force-readout/verify/contact-readout-probe.json
- Gap: 물리 상호작용 claim을 visual cue가 아니라 실제 MuJoCo runtime state로 설명하려면 어떤 값이 브라우저에서 읽히는지 먼저 닫아야 한다.
- Status: [ ]

<!-- harness:milestone id="M35" status="pending" priority="P2" evidence="experiments/136-public-evidence-refresh/verify/public-story-smoke.json" -->
### M35 - Public Evidence Story Refresh

- DoD: README/experiments index/live copy가 M27-M34 evidence와 claim boundary를 반영하고, `robotics.askewly.com` smoke evidence가 남는다.
- Evidence: experiments/136-public-evidence-refresh/verify/public-story-smoke.json
- Gap: public story는 여전히 M17 policy gallery 중심이고, M27-M32 및 controllability/contact evidence arc가 5분 리뷰어에게 충분히 연결되지 않았다.
- Status: [ ]

## Guardrails

- Assisted fixture evidence를 unassisted controller proof 또는 real robot telemetry로 쓰지 않는다.
- M30 visual-only 변경은 collision/contact/solver를 바꾸지 않고 `qaEnvironmentSummary().visualLayer.visualOnly === true`를 유지한다.
- M31부터만 physics/contact-bearing claim을 연다.
- Web mirror JSON은 derived다. canonical experiment edit은 `experiments/03-digital-twin/experiments.json`에서 시작하고 `sync_web.py`로 동기화한다.

## 대기 항목

- M7a 실물 bring-up: SO-101 2-arm 구매/배송/공간/카메라/조립 시간이 확보될 때만 LeRobot install, motor calibration, dataset capture, ACT baseline으로 이동한다.

## Archive Pointer

완료 이력은 `BACKLOG.md` 참조.
