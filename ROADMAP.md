# ROADMAP

> 이 레포의 마일스톤과 다음 증거 생산 계획. **포트폴리오 모드** - 완료 기준은 "내가 이해했다"가 아니라
> "남이 5분 보고 납득한다"이다. 마일스톤마다 보여줄 수 있는 산출물(showable artifact)이 나와야 한다.
> 마지막 업데이트: 2026-06-15

## 왜 이 레포

피지컬 AI(embodied AI/robotics) 기초 지식을 **실행 가능한 포트폴리오**로 입증한다.

한 문장: *"문헌과 이론을 읽었고 -> 직접 실험으로 검증했고 -> 브라우저에서 조작 가능한 로봇 정책 플랫폼을 만들었고 -> 이제 Atlas식 고난도 동작을 디지털 트윈에서 설계·학습·검증한다."*

현재 thesis: **피지컬 AI 연구 루프의 다음 증거는 로봇 수를 늘리는 것이 아니라, 원하는 동작을 명세하고 학습시켜 디지털 트윈에서 재현 가능한 skill로 만드는 것이다.**

노출면: GitHub README(개발자/채용), askewly 블로그(판단과 서사), `~/vault/`(장기 자료집), live demo(`physical-ai-arm.askewly.com`).

## 마일스톤 한눈에

| # | 목표군 | 입증하는 것 | showable artifact | 상태 |
|---|---|---|---|---|
| M1-M3 | 기초 지형 + 첫 실험 | 분야를 이해하고 논문 모델을 직접 실행한다 | `docs/landscape.md`, 5x analysis, exp01 LIBERO | 완료/압축 |
| M4-M6 | 포트폴리오 1차 + 디지털 트윈 | 실험을 남이 볼 수 있는 도구로 만든다 | README, 블로그 1편, SO-100 웹 트윈 | 완료/압축 |
| M8-M11 | 브라우저 정책 플랫폼 | 학습 정책을 웹 closed-loop로 돌리고 새 embodiment를 흡수한다 | Go1/G1/Spot, teleop, `add_scene.sh`, QA harness | 완료/압축 |
| M12-M14 | 강건성 검증 + 2차 패키징 | 명령/지형/정책 추가가 라이브에서 재현된다 | command sweep, rough terrain, G1 rough, README/글/vault | 완료/압축 |
| M7 | 실물 도달 | sim-to-real 전환 조건을 판단한다 | SO-101 2-arm + LeRobot + ACT 구매 전 게이트 | 게이트 완료 |
| M15 | 새 정책 1종 end-to-end 흡수 | 플랫폼이 미보유 policy를 새 학습부터 live QA까지 받아낸다 | Barkour train log, ONNX, native parity, web/live QA | 완료 |
| M16 | 정책 추가 루틴 일반화 | policy 추가가 매번 bespoke 작업이 아니라 운영 루틴이 된다 | `POLICY_ADDITION.md`, `check_policy_bundle.py` | 완료 |
| M17 | 비교 가능한 policy gallery | 단순 갤러리가 아니라 같은 프로토콜로 비교되는 실험판이 된다 | multi-policy command/terrain table + live links | 완료 |
| M18 | Skill authoring foundation | "원하는 동작"을 reward/metric/scene으로 번역할 수 있다 | behavior spec, task compiler, skill taxonomy | 완료 |
| M19 | Humanoid skill baseline | Atlas식 고난도 동작 전에 G1에서 균형·포즈·전환 skill을 만든다 | stand/squat/kick/pose-hold policies + QA | 게이트 완료 / RL 대기 |
| M20 | Acrobatic feasibility gate | 물구나무·덤블링 같은 동작을 현 스택으로 학습 가능한지 판단한다 | feasibility matrix, sim constraints, first hard skill | 완료 |
| M21 | Ball-skill sandbox | 축구/라보나슛을 위해 공·접촉·목표를 포함한 task를 만든다 | ball scene, kick reward, command/score metrics | scene/metric 완료 |
| M22 | Motion-to-policy loop | 키프레임/데모/참조동작을 policy 학습 신호로 바꾼다 | reference motion loader, imitation/RL hybrid probe | 후보 |

## 닫힌 증거

### M1-M6 - 지식에서 보이는 트윈까지
- `docs/landscape.md`, 핵심 논문 5편 분석, ADR 0001로 동작표현 기준 수립.
- exp01에서 VLA 로컬 추론/LIBERO 평가를 실행하고, exp02에서 pi0.5 vs OpenVLA head-to-head를 재측정했다.
- SO-100 웹 디지털 트윈과 scripted pick/place replay를 live 배포했다. 5-DOF 기구학 한계와 scripted replay trade-off는 ADR 0004에 남겼다.

### M8-M11 - 브라우저 closed-loop 정책 플랫폼
- MuJoCo Playground Go1/G1 정책을 학습해 ONNX export, native rollout, browser closed-loop를 닫았다.
- Spot 정책과 8종 gallery를 추가하고, `experiments.json`/`sync_web.py`/`add_scene.sh`/manifest 기반으로 확장 구조를 만들었다.
- WASD 보행, 마우스 EE teleop, 모바일 fallback, Playwright visual QA를 붙여 "관전 데모"를 "조작 가능한 플랫폼"으로 바꿨다.

### M12-M14 - 검증과 포장
- Go1/Spot flat/rough command sweep으로 forward/strafe/turn/diagonal 시나리오를 측정했다.
- `g1-rough-walk` policy package를 추가해 G1 rough scene, byte-parity, local/live visual QA, command sweep을 닫았다.
- README를 "검증 가능한 브라우저 로봇 정책 플랫폼" 중심으로 재압축하고, askewly 예약 글 `robot-walk-qa-after-demo`와 vault synthesis를 만들었다.

### M7 - 실물 게이트
- 신규 구매는 SO-100이 아니라 SO-101 leader+follower 2-arm + LeRobot + ACT-first로 좁혔다.
- 첫 task는 stacking이 아니라 tabletop pick/place다.
- 실제 M7a는 예산, 배송, 작업공간, 카메라 2대, 조립 시간이 확보될 때만 연다.
- 근거: [ADR 0008](docs/adr/0008-m7-real-arm-gate.md), [exp09](experiments/09-real-arm-gate/README.md).

## 다음 목표군 - Atlas식 skill lab

사용자가 원하는 새 목표는 "로봇이 걷는다"가 아니라 **로봇에게 특정 동작을 학습시킨다**이다. 기준 이미지는 Atlas 같은 휴머노이드가 물구나무, 덤블링, 축구, 라보나슛처럼 이름 붙은 skill을 수행하는 장면이다.

이 레포의 다음 전환은 다음과 같다.

- 이전: env가 이미 제공하는 joystick locomotion policy를 학습하고 브라우저에 흡수한다.
- 이후: 내가 원하는 skill을 명세하고, reward/scene/metric으로 컴파일하고, 학습한 뒤, 브라우저에서 실패까지 보이는 demo로 검증한다.

우선순위는 **G1 humanoid를 주 embodiment로 삼고**, Go1/Spot/Barkour는 control/QA 비교군으로 유지한다. Atlas 자체를 복제하는 것이 아니라, Atlas식 연구 질문을 이 레포의 디지털 트윈에서 실험 가능한 작은 skill ladder로 쪼갠다.

### Skill ladder

| 단계 | skill 예시 | 왜 먼저/나중인가 |
|---|---|---|
| L0 안정화 | stand, pose hold, recover | 고난도 동작의 실패 판정과 안정성 기준 |
| L1 자세 전환 | squat, lean, one-foot balance | reward shaping과 balance metric 검증 |
| L2 접촉/타격 | front kick, side kick, ball tap | 축구/라보나슛 전의 단일 접촉 skill |
| L3 동적 전신 | jump, handstand prep, cartwheel prep | 고난도 동작의 전 단계 |
| L4 고난도 | handstand, flip/tumble, rabona kick | 장기 목표. 바로 시작하지 않는다 |

### M18 - Skill authoring foundation

> 목표: "이 동작을 만들어줘"를 바로 학습으로 보내지 않고, 먼저 실험 가능한 task spec으로 고정한다.

- [x] `experiments/14-skill-authoring/README.md`를 만들고 skill taxonomy를 정의했다.
- [x] `behavior_spec.schema.json`으로 embodiment, objective, target, constraints, metrics를 표준화했다.
- [x] 예시 spec 4개를 만들었다: `g1_pose_hold`, `g1_squat`, `g1_front_kick`, `g1_ball_tap`.
- [x] spec을 train/eval config 초안으로 바꾸는 `compile_behavior.py`를 만들었다.
- [x] 성공/실패 metric을 command sweep처럼 raw JSON으로 남기는 평가 형식을 정했다.

완료 기준: ✅ 새 skill을 시작할 때 자연어 목표가 아니라 versioned spec에서 출발한다. 결과는 [exp14](experiments/14-skill-authoring/README.md)에 박제했다.

### M19 - Humanoid skill baseline

> 목표: G1에서 Atlas식 동작의 기초가 되는 균형·포즈·전환 skill을 직접 학습한다.

- [x] 첫 skill 후보를 `g1_squat`으로 고정하고 compiled behavior spec에서 시작했다.
- [x] native MuJoCo에서 hold/mild/deep squat scripted baseline을 평가했다.
- [x] 세 변형 모두 1.24~1.25초에 fall했다. open-loop position target은 실패한다.
- [ ] G1 기존 walking env에 balance-stabilized custom reward wrapper를 붙인다.
- [ ] short PPO smoke 후 native MuJoCo에서 fall, height, joint-limit, energy, target error를 평가한다.
- [ ] ONNX export와 browser playback/live inference까지 연결한다.

완료 기준: 🟨 scripted baseline gate는 완료. G1이 기존 joystick walking이 아니라, 내가 정의한 단일 skill을 학습해 수행하려면 balance reward wrapper + PPO smoke가 남았다. 현재 증거는 [exp15](experiments/15-g1-skill-baseline/README.md)에 박제했다.

### M20 - Acrobatic feasibility gate

> 목표: 물구나무/덤블링을 지금 스택으로 바로 할지, reference motion/imitation이 필요한지 판단한다.

- [x] handstand, cartwheel, flip/tumble, rabona를 난이도와 필요 기술로 분해했다.
- [x] 현 G1 모델의 손 접촉, 관절 한계, actuator 성능, scene 요구사항을 정적 검사했다.
- [x] 바로 학습할 후보는 `squat_or_pose_hold`와 `front_kick`으로 좁혔다.
- [x] handstand는 palm site/hand collision은 있으나 hand-floor contact pair가 없어 보류, tumble/cartwheel은 reference motion 루프 전에는 보류로 판정했다.

완료 기준: ✅ "멋진 동작"을 막연히 시도하지 않고, 고난도 skill의 병목을 기술적으로 분리했다. 결과는 [exp13](experiments/13-acrobatic-feasibility/README.md)에 박제했다.

### M21 - Ball-skill sandbox

> 목표: 축구/라보나슛의 전 단계로 공이 있는 접촉 task를 만든다.

- [x] G1 + ball scene을 만들고 공 위치/속도/goal metric을 읽었다.
- [x] `ball_tap` skill spec과 scene requirement를 M18에서 정의했다.
- [x] 공 이동거리와 방향 오차 metric을 native MuJoCo smoke로 검증했다.
- [ ] 발-공 접촉과 낙상 여부를 실제 kick policy에서 평가한다.
- [ ] 라보나슛은 바로 목표로 삼지 않고, crossing-leg kick feasibility까지 본다.

완료 기준: ✅ scene/metric gate는 완료. 로봇이 실제로 외부 물체를 목표 방향으로 움직이는 learned skill은 M19 balance wrapper 이후 진행한다. 현재 증거는 [exp16](experiments/16-ball-skill-sandbox/README.md)에 박제했다.

### M22 - Motion-to-policy loop

> 목표: handstand/flip처럼 sparse reward만으로 어려운 동작을 위해 reference motion 기반 루프를 연다.

- [ ] 키프레임 또는 reference trajectory 포맷을 정한다.
- [ ] motion tracking reward 또는 imitation pretraining 후보를 비교한다.
- [ ] 브라우저에서 reference vs policy rollout을 나란히 확인하는 viewer를 만든다.

완료 기준: "동작을 보여주고 policy가 따라 하게 한다"는 경로가 최소 실험으로 열린다.

## 닫힌 목표군 상세

### M15 - 새 Playground policy 1종 end-to-end 흡수

> 완료: Go2는 registry env가 없어 제외하고, `BarkourJoystick`을 새 학습 세션으로 열어 live demo까지 닫았다.

- [x] 로컬/WSL의 MuJoCo Playground 소스와 사용 가능한 env 목록을 확인했다.
- [x] Go2는 env 부재로 제외하고, train/export 가능성이 확인된 Barkour를 선택했다.
- [x] `experiments/10-barkour-rl-walk/README.md`에 가설, 방법, 실패 기준, 완료 게이트를 썼다.
- [x] 100M step 학습 log와 reward curve를 남기고 ONNX export를 만들었다.
- [x] ONNX parity, native rollout, golden obs, command convention을 확인했다.
- [x] `experiments/03-digital-twin/experiments.json`에 `barkour-walk`를 등록하고 web bundle/manifest를 생성했다.
- [x] local visual QA, command sweep, live deploy/QA까지 닫았다.

완료 기준: ✅ live `https://physical-ai-arm.askewly.com/?exp=barkour-walk`, local/live visual QA PASS, command sweep PASS, raw artifact는 [exp10](experiments/10-barkour-rl-walk/README.md)에 박제.

### M16 - 정책 추가 루틴 일반화

- [x] Go1/G1/Spot/Barkour에서 반복된 `train -> export -> verify -> bundle -> QA` 단계를 [POLICY_ADDITION.md](experiments/03-digital-twin/POLICY_ADDITION.md) checklist로 줄였다.
- [x] registry, scene, ONNX, golden, manifest, required policy fields를 [check_policy_bundle.py](experiments/03-digital-twin/check_policy_bundle.py)로 점검한다.
- [x] ADR 0007 규칙을 checklist에 올렸다: env가 런타임에 PD gain, damping, mass, friction, actuator gain 등을 바꾸면 정적 XML에 bake해야 한다.

완료 기준: ✅ 현재 policy 7종 bundle sanity PASS. 다음 policy 추가가 "새 연구"가 아니라 문서화된 운영 절차로 시작 가능하다.

### M17 - 비교 가능한 policy gallery

- [x] Go1/G1/Spot/M15 policy를 같은 command sweep/rough terrain 프로토콜로 비교했다.
- [x] 거리, 낙상, NaN, heading drift, command tracking을 같은 표로 묶었다.
- [x] README/live demo 메시지를 "많이 넣었다"보다 "같은 기준으로 비교했다" 쪽으로 이동했다.

완료 기준: ✅ 외부 독자가 5분 안에 어떤 policy가 어떤 조건에서 강하고 약한지 볼 수 있다. 결과는 [exp12 report](experiments/12-policy-gallery-comparison/verify/policy-gallery-report.md)에 박제했다.

## 대기 항목

- **M7a 실물 bring-up**: SO-101 2-arm 구매가 확정되면 LeRobot install, motor calibration, camera setup, tabletop pick/place dataset capture, ACT baseline으로 이동한다.
- **2026-06-22 공개 후 정리**: askewly 예약 글 `robot-walk-qa-after-demo` 공개 후 README/askewly/vault 메시지 drift를 점검한다. 기술 새 증거가 적으므로 별도 마일스톤이 아니라 release hygiene로 둔다.

## 의사결정 이력

"왜 X 안 봄?", "왜 Y 갈래로 안 감?" 같은 의도적 제외는 `docs/adr/`에 ADR로 남긴다.
