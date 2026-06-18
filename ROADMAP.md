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
| M19 | Humanoid skill baseline | G1에서 균형·포즈·전환 skill을 만든다 | visible squat gate + native/browser QA | 다음 |
| M20 | Acrobatic feasibility gate | 물구나무·덤블링 가능 조건을 분리한다 | feasibility matrix, sim constraints, first hard skill | 완료 |
| M21 | Ball-skill sandbox | 축구/라보나슛 전 공·접촉·목표 task를 만든다 | ball scene, kick reward, command/score metrics | scene/metric 완료 |
| M22 | Motion-to-policy loop | 참조동작을 policy 학습 신호로 바꾼다 | reference motion loader, imitation/RL hybrid probe | env 결합 완료 / stabilizer 필요 |
| M23 | Robotics Lab gallery | 방문자가 로봇/동작/검증/한계를 바로 이해한다 | robotics.askewly.com lab gallery UI | 완료 |
| M24 | Digital Twin Architecture Gate | 공개 viewer와 연구 backend twin의 경계를 정한다 | stack comparison + ADR + Unitree DDS/browser gate | 완료 |

## 닫힌 증거 요약

- M1-M6: 핵심 논문 분석, LIBERO/OpenVLA/pi0.5 비교, SO-100 scripted pick/place web twin까지 완료. 5-DOF 기구학 한계와 scripted replay trade-off는 ADR 0004에 남겼다.
- M8-M14: MuJoCo Playground Go1/G1/Spot 정책을 학습해 ONNX export, native rollout, browser closed-loop, WASD/마우스 teleop, rough terrain/command sweep, live QA까지 닫았다.
- M7: 신규 구매는 SO-101 leader+follower 2-arm + LeRobot + ACT-first로 좁혔다. 실제 M7a는 예산/배송/공간/카메라/조립 시간이 확보될 때만 연다. 근거: [ADR 0008](docs/adr/0008-m7-real-arm-gate.md), [exp09](experiments/09-real-arm-gate/README.md).
- M15-M17: Barkour policy를 새 학습부터 live demo까지 흡수했고, policy 추가 루틴과 비교 가능한 gallery를 문서/검증 스크립트로 일반화했다. live: `https://robotics.askewly.com/?exp=barkour-walk`.
- M23-M24: Robotics Lab public gallery와 simulated controller-backed G1 digital twin gate를 닫았다. real robot telemetry twin은 future work다.

## 현재 목표군 - Atlas식 skill lab

현재는 public gallery 정리를 끝내고, G1 humanoid에서 **보이는 자세 전환 skill**을 다시 연다.

- 첫 목표는 M19 `g1_squat` stance-aware return policy / WBC prototype이다.
- 성공은 "낮아진 숫자"가 아니라 exp29 visible gate와 native/browser replay가 같이 통과하는 것이다.
- reward scale만 반복하지 않는다. exp30/34-41이 weak/ramp/reference-base/soft-WBC=shallow, visible/reference=fall을 보였고, reward/action-origin/hand-written guard는 depth/contact/return gate에서 막혔다.
- M22 side-by-side viewer와 M21 ball/kick은 M19 안정화 evidence 뒤에 붙인다.

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

### M18 - Skill authoring foundation

- [x] `experiments/14-skill-authoring/README.md`에서 skill taxonomy를 정의했다.
- [x] `behavior_spec.schema.json`으로 embodiment, objective, target, constraints, metrics를 표준화했다.
- [x] `g1_pose_hold`, `g1_squat`, `g1_front_kick`, `g1_ball_tap` spec과 `compile_behavior.py`를 만들었다.
- [x] 성공/실패 metric을 command sweep처럼 raw JSON으로 남기는 평가 형식을 정했다.

완료 기준: ✅ 새 skill을 자연어 목표가 아니라 versioned spec에서 시작한다. 증거: [exp14](experiments/14-skill-authoring/README.md).

### M19 - Humanoid skill baseline

> 목표: G1에서 Atlas식 동작의 기초가 되는 균형·포즈·전환 skill을 직접 학습한다.

- [x] 첫 skill 후보를 `g1_squat`으로 고정하고 compiled behavior spec에서 시작했다.
- [x] native scripted baseline과 scratch/recovery/reference PPO는 모두 1.24초 전후 fall로 실패했다.
- [x] 기존 G1 walking policy를 stabilizer prior로 restore해 native 6초 no-fall을 달성했다.
- [x] stabilizer 기반 height/reference reward 강화는 no-fall을 유지했지만 min height가 0.7523m -> 0.7501m로만 개선됐다.
- [x] native target sanity probe에서 squat reference/action target이 height drop은 만들지만 1.22초 전후 fall함을 확인했다.
- [x] squat skill design gate에서 G1 squat를 controlled lowering/hold/return으로 재정의하고 success metric을 고정했다.
- [x] staged curriculum scaffold와 stage 0.74 native diagnostic을 만들었다. exp22 source policy는 6초 no-fall이지만 min height 0.7501m로 stage depth는 아직 미달이다.
- [x] exp28에서 calibrated reference controller로 약한 stage 0.74 numeric gate를 통과했다: no-fall 6.0s, min height 0.7446m, hold 1.32s, foot contact 1.00.
- [x] exp28 rollout을 50Hz qpos trajectory로 기록해 browser replay artifact `g1-controlled-squat`로 연결했다.
- [x] 사용자 visual review와 trajectory audit으로 exp28 replay가 visible squat이 아니라 약 1cm micro-dip임을 확인했다.
- [x] exp29에서 visible squat gate를 다시 정의했다: pelvis drop >=8cm, knee flexion delta >=0.60rad, hip pitch delta >=0.35rad.
- [x] exp29 static audit상 local G1 lower-body joint ranges는 visible squat target 후보를 담을 수 있다. 단, 동역학/접촉/학습 성공은 아직 미증명이다.
- [x] exp30에서 stage 0.67 visible-depth target을 기존 controller로 native probe했다. weak blend는 안정적이지만 1.2cm만 내려가고, strong blend는 visible-depth에 들어가지만 2.06초에 fall한다.
- [x] exp34에서 guarded descent controller를 native probe했다. `strict-low`는 8.7cm visible drop과 no-fall을 만들었지만 contact 0.85, foot slip 1.267m, final height 0.7034m로 return/contact gate를 실패했다.
- [x] exp35에서 stance-anchor/early-return controller를 native probe했다. visible threshold 직후 return해도 fall했고, learned residual을 끄면 1.24초 fall로 더 나빠졌다.
- [x] exp36-120에서 controller/selector/WBC/stance curriculum/corridor PPO/reference/native/ONNX adapter/public XML/mjlab/action-wrapper/future-reference/friction planner/contact-force audit/QP-lite/static ID-QP/dynamic tracking smoke/retrain/full-order formulation/longer tracker/deployable WBC/trace adapter gate를 probe했다. exp109는 visible pose가 static ID-QP에서는 plausible함을 보였고, exp118은 20k-step local tracker도 drop 2.62cm로 gate에 멀었으며, exp119는 GR00T/SONIC 29-DOF contract와 exp33 browser transport가 맞는다고 봤고, exp120은 GR00T debug trace -> web/visible gate adapter를 열었지만 WSL Git LFS가 막혔다.
- [ ] **재개** — 다음 기술 작업은 WSL Git LFS를 복구한 뒤 GR00T/SONIC model download + sim2sim을 실행하고, 실제 `g1_debug`/CSV measured 29-DOF trace를 exp120 adapter와 exp33 browser gate로 흘려 exp29 visible gate와 browser replay를 닫는 것이다. 대안은 동등한 deployable WBC trace를 확보해 같은 gate에 넣는 것이다.

완료 기준: 🟨 M19는 균형 prior와 micro-dip/controller evidence는 확보했고 8cm depth/contact/slip+knee까지 동시에 보였으며 static ID-QP상 visible target 자체는 plausible하다고 분리했지만, controller/retrain/qfrc/20k local tracker gate는 실패했다. exp119-120으로 GR00T/SONIC 통합 후보와 trace adapter는 열렸지만 "보이는 스쿼트"는 아직 완료가 아니다. 완료 조건은 exp29 visible gate를 native rollout과 browser replay가 동시에 통과하는 것이다. 증거: [exp15](experiments/15-g1-skill-baseline/README.md), [exp18](experiments/18-g1-squat-reward-smoke/README.md), [exp19](experiments/19-g1-squat-recovery-longrun/README.md), [exp20](experiments/20-g1-squat-reference-tracking/README.md), [exp21](experiments/21-g1-stabilizer-init-probe/README.md), [exp22](experiments/22-g1-squat-depth-finetune/README.md), [exp23](experiments/23-g1-squat-target-sanity/README.md), [exp24](experiments/24-g1-squat-skill-design/README.md), [exp25](experiments/25-g1-squat-depth-curriculum/README.md), [exp28](experiments/28-g1-controlled-squat-stage0p74/README.md), [exp29](experiments/29-g1-visible-squat-feasibility/README.md), [exp30](experiments/30-g1-visible-squat-controller/README.md), [exp34](experiments/34-g1-guarded-descent-controller/README.md), [exp35](experiments/35-g1-stance-anchored-squat-controller/README.md), [exp36](experiments/36-g1-wbc-ik-squat-prototype/README.md)-[exp120](experiments/120-g1-gr00t-trace-adapter-visible-gate/README.md).

### M23 - Robotics Lab gallery

- [x] `robotics.askewly.com`을 canonical 도메인으로 고정했다.
- [x] Vercel project domain에서 legacy `physical-ai-arm.askewly.com`을 제거했다.
- [x] askewly.com 진입 링크를 `robotics.askewly.com`으로 교체했다.
- [x] 로봇 선택, 설명, 가능한 조작, 검증/학습 내용을 first-view panel에서 명확히 보이게 다듬었다.
- [x] public overlay를 `robot + motion + evidence + limit` 구조로 재편했다.
- [x] G1 lowering probe를 "not a squat"으로 노출하고 M19 재개 조건을 명확히 뒀다.
- [x] desktop/mobile live QA를 다시 통과했다.

완료 기준: ✅ live gallery가 기술 실험 장부가 아니라 방문자가 이해 가능한 로봇 포트폴리오로 보이고, old label/stale claim audit과 desktop/mobile live QA를 통과했다. 증거: [exp31](experiments/31-robotics-lab-gallery-polish/README.md), [web](experiments/03-digital-twin/web/README.md), deploy `dpl_FjcwuMkkwUhztEvMM9Si3V9ZpzAW`.

### M20 - Acrobatic feasibility gate

- [x] handstand, cartwheel, flip/tumble, rabona를 난이도와 필요 기술로 분해했다.
- [x] 현 G1 모델의 손 접촉, 관절 한계, actuator 성능, scene 요구사항을 정적 검사했다.
- [x] 바로 학습할 후보는 `squat_or_pose_hold`와 `front_kick`으로 좁혔다.
- [x] handstand는 hand-floor contact pair 부재로 보류, tumble/cartwheel은 reference motion 루프 전에는 보류로 판정했다.

완료 기준: ✅ 고난도 skill의 병목을 기술적으로 분리했다. 증거: [exp13](experiments/13-acrobatic-feasibility/README.md).

### M21 - Ball-skill sandbox

- [x] G1 + ball scene을 만들고 공 위치/속도/goal metric을 읽었다.
- [x] `ball_tap` skill spec과 scene requirement를 M18에서 정의했다.
- [x] 공 이동거리와 방향 오차 metric을 native MuJoCo smoke로 검증했다.
- [ ] 발-공 접촉과 낙상 여부를 실제 kick policy에서 평가한다.
- [ ] 라보나슛은 바로 목표로 삼지 않고 crossing-leg kick feasibility까지 본다.

완료 기준: 🟨 scene/metric gate는 완료. learned external-object skill은 M19 balance/depth 이후 진행한다. 증거: [exp16](experiments/16-ball-skill-sandbox/README.md).

### M22 - Motion-to-policy loop

- [x] 키프레임 reference trajectory 포맷을 정했다.
- [x] G1 squat reference를 50Hz fixed-rate trajectory로 compile했다.
- [x] tracking/height/smoothness/fall reward term 계약을 만들었다.
- [x] motion tracking reward를 실제 G1 squat env에 결합했다.
- [ ] 브라우저에서 reference vs policy rollout을 나란히 확인하는 viewer를 만든다.

완료 기준: 🟨 reference format/probe와 reward-env 결합은 열렸다. 다만 stabilizer prior 없이 motion tracking만으로는 native fall을 해결하지 못했다. 증거: [exp17](experiments/17-motion-to-policy-loop/README.md), [exp20](experiments/20-g1-squat-reference-tracking/README.md).

### M24 - Digital Twin Architecture Gate

진행: ✅ 현재 구현을 browser-based MuJoCo robotics lab / public twin viewer로 재정의하고, MuJoCo/Web 유지 + backend twin gate로 결정했다. Unitree G1 trace adapter, Unitree MJCF DDS bridge, assisted LowCmd closed loop, collapse rejection, external DDS candidate, 그리고 Unitree RL Lab G1-29DOF unassisted policy -> official MuJoCo -> DDS -> browser candidate PASS로 readiness `COMPLETE`를 통과했다. real robot telemetry twin은 별도 future work다. 증거: [exp32](experiments/32-digital-twin-architecture-gate/README.md), [exp33](experiments/33-unitree-mujoco-g1-bridge-probe/README.md), [ADR 0009](docs/adr/0009-digital-twin-layering.md).

## 대기 항목

- **M7a 실물 bring-up**: SO-101 2-arm 구매가 확정되면 LeRobot install, motor calibration, camera setup, tabletop pick/place dataset capture, ACT baseline으로 이동한다.
- **2026-06-22 공개 후 정리**: askewly 예약 글 `robot-walk-qa-after-demo` 공개 후 README/askewly/vault 메시지 drift를 점검한다.

## 의사결정 이력

"왜 X 안 봄?", "왜 Y 갈래로 안 감?" 같은 의도적 제외는 `docs/adr/`에 ADR로 남긴다.
