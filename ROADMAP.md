# ROADMAP

> 이 레포의 마일스톤과 다음 증거 생산 계획. **포트폴리오 모드** - 완료 기준은 "내가 이해했다"가 아니라
> "남이 5분 보고 납득한다"이다. 마일스톤마다 보여줄 수 있는 산출물(showable artifact)이 나와야 한다.
> 마지막 업데이트: 2026-06-15

## 왜 이 레포

피지컬 AI(embodied AI/robotics) 기초 지식을 **실행 가능한 포트폴리오**로 입증한다.

한 문장: *"문헌과 이론을 읽었고 -> 직접 실험으로 검증했고 -> 브라우저에서 조작 가능한 로봇 정책 플랫폼으로 만들었고 -> 다음은 새 정책을 반복 흡수하거나 실물로 넘어간다."*

현재 thesis: **브라우저 로봇 정책 플랫폼이 새 embodiment/policy를 반복적으로 흡수할 수 있는지 검증한다.**

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
| M17 | 비교 가능한 policy gallery | 단순 갤러리가 아니라 같은 프로토콜로 비교되는 실험판이 된다 | multi-policy command/terrain table + live links | 후보 |

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

## 다음 목표군

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

- [ ] Go1/G1/Spot/M15 policy를 같은 command sweep/rough terrain 프로토콜로 비교한다.
- [ ] 거리, 속도, 낙상, NaN, heading drift, command tracking을 같은 표로 묶는다.
- [ ] README/live demo에서 "많이 넣었다"가 아니라 "같은 기준으로 비교했다"가 보이게 한다.

완료 기준: 외부 독자가 5분 안에 어떤 policy가 어떤 조건에서 강하고 약한지 볼 수 있다.

## 대기 항목

- **M7a 실물 bring-up**: SO-101 2-arm 구매가 확정되면 LeRobot install, motor calibration, camera setup, tabletop pick/place dataset capture, ACT baseline으로 이동한다.
- **2026-06-22 공개 후 정리**: askewly 예약 글 `robot-walk-qa-after-demo` 공개 후 README/askewly/vault 메시지 drift를 점검한다. 기술 새 증거가 적으므로 별도 마일스톤이 아니라 release hygiene로 둔다.

## 의사결정 이력

"왜 X 안 봄?", "왜 Y 갈래로 안 감?" 같은 의도적 제외는 `docs/adr/`에 ADR로 남긴다.
