# ROADMAP

> 이 레포의 마일스톤과 다음 증거 생산 계획. **포트폴리오 모드** - 완료 기준은 "내가 이해했다"가 아니라 "남이 5분 보고 납득한다"이다.
> 마지막 업데이트: 2026-06-18

## 왜 이 레포

피지컬 AI(embodied AI/robotics) 기초 지식을 **실행 가능한 포트폴리오**로 입증한다.

한 문장: *"문헌과 이론을 읽었고 -> 직접 실험으로 검증했고 -> 브라우저에서 조작 가능한 로봇 정책 플랫폼을 만들었고 -> 이제 Atlas식 고난도 동작을 디지털 트윈에서 설계·학습·검증한다."*

현재 thesis: **Robotics Lab 공개 정리는 닫혔다. 이제 필요한 증거는 G1 humanoid에서 원하는 skill을 명세하고, 안정화/controller/replay gate를 통과시키는 Atlas식 skill lab 재개다.**

노출면: GitHub README(개발자/채용), askewly 블로그(판단과 서사), `~/vault/`(장기 자료집), live demo(`robotics.askewly.com`).

## 마일스톤 한눈에

| # | 목표군 | 입증하는 것 | showable artifact | 상태 |
|---|---|---|---|---|
| M1-M6 | 기초 지형 + 디지털 트윈 | 문헌/실험을 보이는 도구로 만든다 | `docs/landscape.md`, exp01/02, SO-100 web twin | 완료/압축 |
| M7 | 실물 도달 | sim-to-real 전환 조건을 판단한다 | SO-101 2-arm + LeRobot + ACT 구매 전 게이트 | 게이트 완료 |
| M8-M14 | 브라우저 정책 플랫폼 | 학습 정책을 웹 closed-loop로 돌리고 검증한다 | Go1/G1/Spot rough, teleop, command sweep, live QA | 완료/압축 |
| M15 | 새 정책 1종 end-to-end 흡수 | 미보유 policy를 학습부터 live QA까지 받는다 | Barkour train log, ONNX, native/web/live QA | 완료 |
| M16 | 정책 추가 루틴 일반화 | policy 추가가 운영 루틴이 된다 | `POLICY_ADDITION.md`, `check_policy_bundle.py` | 완료 |
| M17 | 비교 가능한 policy gallery | 같은 프로토콜로 정책을 비교한다 | multi-policy command/terrain table + live links | 완료 |
| M18 | Skill authoring foundation | "원하는 동작"을 reward/metric/scene으로 번역한다 | behavior spec, task compiler, skill taxonomy | 완료 |
| M19 | Humanoid skill baseline | G1에서 균형·포즈·전환 skill을 만든다 | visible squat gate + native/browser QA | 완료 |
| M20 | Acrobatic feasibility gate | 물구나무·덤블링 가능 조건을 분리한다 | feasibility matrix, sim constraints, first hard skill | 완료 |
| M21 | Ball-skill sandbox | 축구/라보나슛 전 공·접촉·목표 task를 만든다 | ball scene, kick reward, command/score metrics | 완료 |
| M22 | Motion-to-policy loop | 참조동작을 policy 학습 신호로 바꾼다 | reference motion loader, imitation/RL hybrid probe | 완료 |
| M23 | Robotics Lab gallery | 방문자가 로봇/동작/검증/한계를 바로 이해한다 | robotics.askewly.com lab gallery UI | 완료 |
| M24 | Digital Twin Architecture Gate | 공개 viewer와 연구 backend twin의 경계를 정한다 | stack comparison + ADR + Unitree DDS/browser gate | 완료 |
| M25 | G1 ball tap learned controller | scripted ball probe를 learned external-object skill로 올린다 | train/eval gate, native metrics, controller trajectory | 완료 |

## 닫힌 증거 요약

- M1-M6: 핵심 논문 분석, LIBERO/OpenVLA/pi0.5 비교, SO-100 scripted pick/place web twin까지 완료. 5-DOF 기구학 한계와 scripted replay trade-off는 ADR 0004에 남겼다.
- M8-M14: MuJoCo Playground Go1/G1/Spot 정책을 학습해 ONNX export, native rollout, browser closed-loop, WASD/마우스 teleop, rough terrain/command sweep, live QA까지 닫았다.
- M7: 신규 구매는 SO-101 leader+follower 2-arm + LeRobot + ACT-first로 좁혔다. 실제 M7a는 예산/배송/공간/카메라/조립 시간이 확보될 때만 연다. 근거: [ADR 0008](docs/adr/0008-m7-real-arm-gate.md), [exp09](experiments/09-real-arm-gate/README.md).
- M15-M17: Barkour policy를 새 학습부터 live demo까지 흡수했고, policy 추가 루틴과 비교 가능한 gallery를 문서/검증 스크립트로 일반화했다. live: `https://robotics.askewly.com/?exp=barkour-walk`.
- M23-M24: Robotics Lab public gallery와 simulated controller-backed G1 digital twin gate를 닫았다. real robot telemetry twin은 future work다.

## 현재 목표군 - Atlas식 skill lab

현재는 public gallery 정리를 끝내고, G1 humanoid에서 **보이는 자세 전환 skill**의 baseline과 simulated controller-backed backend twin gate를 닫았다. 다음 horizon은 Robotics Lab v2로, 공개 UI의 완성도와 디지털 트윈 환경 조작성을 같이 끌어올린다.

- M19 `g1_squat`는 GR00T Decoupled WBC measured trace로 visible-depth/contact/slip/return/browser gate를 통과했다.
- 성공은 "낮아진 숫자"가 아니라 exp29 visible gate와 native/browser replay가 같이 통과하는 것이다.
- reward scale만 반복하지 않는다. exp30/34-41이 weak/ramp/reference-base/soft-WBC=shallow, visible/reference=fall을 보였고, reward/action-origin/hand-written guard는 depth/contact/return gate에서 막혔다.
- M25는 trainable-controller gate로 닫혔다. 다음 구현은 M26에서 backend evidence를 공개 viewer 안에서 조작 가능한 workbench로 끌어올리는 것이다.
- M27-M28은 shadcn/Tailwind UI shell, favicon, 실험실 환경, environment preset, grounding/physics controls를 분리해서 진행한다.

### 다음 목표군 - Public drift audit

2026-06-22 예약 글 공개 후 README/askewly/vault/live demo 메시지 drift를 점검한다.

### Skill ladder

| 단계 | skill 예시 | 왜 먼저/나중인가 |
|---|---|---|
| L0 안정화 | stand, pose hold, recover | 고난도 동작의 실패 판정과 안정성 기준 |
| L1 자세 전환 | squat, lean, one-foot balance | reward shaping과 balance metric 검증 |
| L2 접촉/타격 | front kick, side kick, ball tap | 축구/라보나슛 전의 단일 접촉 skill |
| L3 동적 전신 | jump, handstand prep, cartwheel prep | 고난도 동작의 전 단계 |
| L4 고난도 | handstand, flip/tumble, rabona kick | 장기 목표. 바로 시작하지 않는다 |

<!-- harness:milestone id="M27" status="completed" priority="P0" evidence="experiments/128-robotics-lab-ui-shell/verify/ui-shell-smoke.json" -->
### M27 - Robotics Lab shadcn UI Shell

- DoD: Vite/React/Tailwind/shadcn 기반 app shell이 기존 MuJoCo canvas/runtime을 보존하면서 robot picker, workbench evidence, QA status, responsive panel 구조를 제공하고 새 imagegen favicon이 로드된다.
- Evidence: experiments/128-robotics-lab-ui-shell/verify/ui-shell-smoke.json
- Gap: 현재 UI는 vanilla DOM string/CSS 중심이라 shadcn/Tailwind 컴포넌트 시스템, favicon 브랜딩, 모바일/데스크탑 polish를 안정적으로 확장하기 어렵다.
- Status: [x]

- Completed at: 2026-06-24
- Summary: Robotics Lab now has a Vite/React/Tailwind/shadcn shell, generated favicon, desktop/mobile QA, and preserved MuJoCo workbench gates.
<!-- harness:milestone id="M28" status="completed" priority="P0" evidence="experiments/129-digital-twin-lab-environment/verify/environment-controls-smoke.json" -->
### M28 - Digital Twin Laboratory Environment Controls

- DoD: 실험실 배경과 최소 3개 environment preset(flat lab, instrumented lab, rough/terrain)을 제공하고, floor/contact/grounding/physics setting summary가 UI와 QA artifact에 기록된다.
- Evidence: experiments/129-digital-twin-lab-environment/verify/environment-controls-smoke.json
- Gap: 현재 scene은 checker ground와 고정 배경 중심이며, 로봇이 땅에 붙어있는 assisted/grounding mechanism과 물리 튜닝 값을 사용자가 비교·검증하기 어렵다.
- Status: [x]
- Completed at: 2026-06-25
- Summary: Digital Twin Lab now has three environment presets, lab visuals, grounding/contact/physics summaries, and committed QA evidence.
### M18 - Skill authoring foundation

완료 기준: ✅ skill taxonomy, behavior spec schema, 4개 G1 skill spec, compiler, raw metric contract를 닫았다. 증거: [exp14](experiments/14-skill-authoring/README.md).

### M19 - Humanoid skill baseline

완료 기준: ✅ G1 squat를 exp29 visible gate로 재정의한 뒤 exp36-122 controller/WBC/trace probes를 거쳐 exp122 Decoupled WBC measured trace가 native + browser replay gate를 통과했다. 증거: [exp15](experiments/15-g1-skill-baseline/README.md)-[exp122](experiments/122-g1-decoupled-wbc-squat-trace-gate/README.md), web replay `?exp=g1-decoupled-wbc-squat`.

### M23 - Robotics Lab gallery

완료 기준: ✅ canonical domain, public overlay, stale-claim audit, desktop/mobile live QA를 닫았다. 증거: [exp31](experiments/31-robotics-lab-gallery-polish/README.md), [web](experiments/03-digital-twin/web/README.md), deploy `dpl_FjcwuMkkwUhztEvMM9Si3V9ZpzAW`.

### M20 - Acrobatic feasibility gate

완료 기준: ✅ 고난도 skill의 병목을 기술적으로 분리했다. 증거: [exp13](experiments/13-acrobatic-feasibility/README.md).

<!-- harness:milestone id="M21" status="completed" priority="P0" evidence="experiments/125-g1-crossing-leg-kick-feasibility/verify/g1-crossing-leg-kick-feasibility.json" -->
### M21 - Ball-skill sandbox

- [x] G1 + ball scene을 만들고 공 위치/속도/goal metric을 읽었다.
- [x] `ball_tap` skill spec과 scene requirement를 M18에서 정의했다.
- [x] 공 이동거리와 방향 오차 metric을 native MuJoCo smoke로 검증했다.
- [x] 발-공 접촉과 낙상 여부를 kick probe에서 평가했다.
- [x] 라보나슛은 바로 목표로 삼지 않고 crossing-leg kick feasibility까지 봤다.

- DoD: ✅ foot-ball contact, ball movement, direction error, fall/no-fall, and crossing-leg feasibility are evaluated in probes.
- Evidence: [exp16](experiments/16-ball-skill-sandbox/README.md), [exp124](experiments/124-g1-ball-kick-contact-probe/README.md), [exp125](experiments/125-g1-crossing-leg-kick-feasibility/README.md)
- Gap: learned rabona/external-object controller is future work, not part of this sandbox gate.
- Status: ✅ M21 PASS

<!-- harness:milestone id="M22" status="completed" priority="P0" evidence="experiments/123-g1-reference-vs-rollout-viewer/verify/browser-reference-vs-rollout.json" -->
### M22 - Motion-to-policy loop

- [x] 키프레임 reference trajectory 포맷을 정했다.
- [x] G1 squat reference를 50Hz fixed-rate trajectory로 compile했다.
- [x] tracking/height/smoothness/fall reward term 계약을 만들었다.
- [x] motion tracking reward를 실제 G1 squat env에 결합했다.
- [x] 브라우저에서 reference vs measured rollout을 나란히 확인하는 compare viewer를 만들었다.

- DoD: reference motion과 measured rollout을 같은 browser qpos contract로 비교하고 QA evidence를 남긴다.
- Evidence: [exp17](experiments/17-motion-to-policy-loop/README.md), [exp20](experiments/20-g1-squat-reference-tracking/README.md), [exp123](experiments/123-g1-reference-vs-rollout-viewer/README.md)
- Gap: motion tracking reward는 native fall을 해결하지 못했지만, viewer gate가 없어 실패/성공 trace를 비교하기 어려웠다.
- Status: [x]

<!-- harness:milestone id="M25" status="completed" priority="P0" evidence="experiments/126-g1-ball-tap-learned-controller-gate/verify/g1-ball-tap-learned-controller-gate.json" -->
### M25 - G1 ball tap learned controller

- DoD: ✅ M21 scripted ball/contact/crossing probes를 학습용 external-object task로 바꾸고, trainable-controller 후보가 native eval에서 `contact_frames > 0`, `ball_distance >= 0.6m`, `direction_error < 0.2rad`, `fall=false`를 증거 JSON으로 남겼다.
- Evidence: [exp126](experiments/126-g1-ball-tap-learned-controller-gate/README.md), source probes [exp124](experiments/124-g1-ball-kick-contact-probe/README.md), [exp125](experiments/125-g1-crossing-leg-kick-feasibility/README.md)
- Gap: full neural RL 또는 dynamic balance policy는 future milestone로 분리한다.
- Status: ✅ M25 PASS

### M24 - Digital Twin Architecture Gate

진행: ✅ 현재 구현을 browser-based MuJoCo robotics lab / public twin viewer로 재정의하고, MuJoCo/Web 유지 + backend twin gate로 결정했다. Unitree G1 trace adapter, Unitree MJCF DDS bridge, assisted LowCmd closed loop, collapse rejection, external DDS candidate, 그리고 Unitree RL Lab G1-29DOF unassisted policy -> official MuJoCo -> DDS -> browser candidate PASS로 readiness `COMPLETE`를 통과했다. real robot telemetry twin은 별도 future work다. 증거: [exp32](experiments/32-digital-twin-architecture-gate/README.md), [exp33](experiments/33-unitree-mujoco-g1-bridge-probe/README.md), [ADR 0009](docs/adr/0009-digital-twin-layering.md).

## 대기 항목

- **M7a 실물 bring-up**: SO-101 2-arm 구매가 확정되면 LeRobot install, motor calibration, camera setup, tabletop pick/place dataset capture, ACT baseline으로 이동한다.
- **2026-06-22 공개 후 정리**: askewly 예약 글 `robot-walk-qa-after-demo` 공개 후 README/askewly/vault 메시지 drift를 점검한다.

## 의사결정 이력

"왜 X 안 봄?", "왜 Y 갈래로 안 감?" 같은 의도적 제외는 `docs/adr/`에 ADR로 남긴다.
