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
| M30 | Visual Lab Scenes | preset이 색만 바뀌는 수준을 넘어 공간으로 보인다 | `experiments/131-visual-lab-scenes` | active |
| M31 | Physical Rough Terrain Scene | rough preset이 실제 contact-bearing scene variant로 연결된다 | `experiments/132-physical-rough-terrain-scene` | pending |
| M32 | Asset-backed Lab Shell | GLB/glTF asset 기반 실험실 shell을 넣을 수 있다 | `experiments/133-asset-backed-lab-shell` | pending |

## Current Horizon

<!-- harness:goal id="robotics-lab-environment-realism" -->
목표: Robotics Lab v2의 environment preset을 "색/라벨"이 아니라 시각 공간, 물리 terrain, asset pipeline으로 단계별 강화한다.

## Active Milestones

<!-- harness:milestone id="M30" status="active" priority="P0" evidence="experiments/131-visual-lab-scenes/verify/visual-lab-scenes-smoke.json" -->
### M30 - Visual Lab Scenes

- DoD: `flat-lab`, `instrumented-lab`, `rough-terrain`가 각각 다른 Three.js visual composition을 가진다. flat은 정돈된 calibration bay, instrumented는 센서/계측 장비가 보이는 measurement bay, rough는 curb/step/test lane 공간으로 보이며 MuJoCo physics는 바꾸지 않는다.
- Evidence: `experiments/131-visual-lab-scenes/verify/visual-lab-scenes-smoke.json`
- Gap: M28의 environment preset은 사용자 눈에는 색/라인 차이로만 보인다. 공개 viewer는 디지털 트윈 공간이라는 첫인상을 줘야 한다.
- Status: [ ]

## Next Candidates

<!-- harness:milestone id="M31" status="pending" priority="P0" evidence="experiments/132-physical-rough-terrain-scene/verify/rough-terrain-scene-smoke.json" -->
### M31 - Physical Rough Terrain Scene

- DoD: rough terrain preset이 실제 MJCF scene variant 또는 compatible terrain geometry로 연결되고, `g1-rough-walk`/4족 rough policies에서 contact-bearing QA가 통과한다.
- Evidence: `experiments/132-physical-rough-terrain-scene/verify/rough-terrain-scene-smoke.json`
- Gap: M30은 visual-only다. 실제 terrain claim은 collision/contact-bearing scene 증거가 있어야 한다.
- Status: [ ]

<!-- harness:milestone id="M32" status="pending" priority="P1" evidence="experiments/133-asset-backed-lab-shell/verify/asset-lab-shell-smoke.json" -->
### M32 - Asset-backed Lab Shell

- DoD: lightweight GLB/glTF lab shell 또는 generated static asset을 lazy-load하고, bundle/performance/visual QA를 통과한다.
- Evidence: `experiments/133-asset-backed-lab-shell/verify/asset-lab-shell-smoke.json`
- Gap: procedural primitives만으로는 실제 실험실 디테일과 브랜드 품질에 한계가 있다.
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
