# 13-acrobatic-feasibility — G1 acrobatic skill feasibility gate

> M20. Atlas식 skill lab으로 넘어가기 전에, 현재 G1 디지털 트윈으로 물구나무·덤블링·축구·라보나슛 계열을 바로 학습할 수 있는지 정적 모델 증거로 자른다.

## 1. 가설 (Hypothesis)

현재 G1 모델/scene은 `squat`, `pose hold`, `front kick` 같은 낮은 단계 skill은 바로 M19 학습 후보로 삼을 수 있지만, `handstand`, `cartwheel/tumble`, `rabona kick`은 contact model, ball scene, reference motion 루프 없이는 바로 RL 학습 대상으로 삼으면 실패할 것이다.

반증 기준:
- 현재 G1 scene에 palm-floor contact와 hand support sensor가 이미 있어 handstand prep을 바로 시도할 수 있다.
- 공/goal metric이 이미 있어 ball skill이 scene 작업 없이 가능하다.
- aerial full-body rotation을 위한 reference motion 또는 tracking objective가 이미 있다.

## 2. 방법 (Method)

### 셋업
- 모델: `experiments/03-digital-twin/web/assets/scenes/g1/g1_mjx_feetonly.xml`
- 데이터: 현재 repo에 배포된 G1 browser/native asset.
- 하네스 구성: 정적 XML inspector `analyze_g1_acrobatics.py`.

### 시나리오
- S1: G1 joint/actuator/sensor/contact inventory를 뽑는다.
- S2: hand/foot contact pair와 wrist/arm/leg torque range를 확인한다.
- S3: skill ladder별 go / guardrail / blocked / defer 판정을 만든다.

### 측정 metric
- joints, actuators, sensors, contact pairs.
- foot-floor pair 존재 여부.
- hand-floor pair 존재 여부.
- arm/leg torque range.
- skill별 next gate.

## 3. 결과 (Results)

### 데이터
| Run | Verdict | Cost | Retries | 비고 |
|-----|---------|------|---------|------|
| S1-S3 static gate | PASS | local XML inspect | 0 | G1 현 모델 기준 feasibility matrix 생성 |

### 요약
| Skill | Verdict | 이유 |
|---|---|---|
| squat / pose hold | go | 기존 foot-floor contact와 leg/waist position control로 시작 가능 |
| front kick | go_with_guardrails | leg torque는 충분하지만 single-support balance gate 필요 |
| ball tap / simple kick | needs_scene | 공 body, ball sensor, goal metric이 아직 없음 |
| handstand | blocked_until_contact_model_update | palm site/hand collision은 있으나 hand-floor contact pair가 없고 wrist pitch/yaw torque가 5 Nm |
| cartwheel / tumble | blocked_until_reference_motion | aerial full-body rotation은 sparse reward만으로 바로 가기 어렵고 reference motion/tracking objective가 없음 |
| rabona kick | defer | ball scene + crossing-leg balance + target-direction kick이 필요하므로 simple kick 이후 |

### 박제 위치
- `verify/g1-acrobatics-feasibility.json`
- `verify/g1-acrobatics-feasibility.md`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- Atlas식 동작 목표는 맞지만, 바로 `handstand`나 `tumble` 학습으로 들어가면 contact/reward/reference-motion 병목에 막힐 가능성이 높다.
- M19의 첫 custom humanoid skill은 `squat -> stand` 또는 `front kick`이 맞다. 둘 다 현재 G1 모델로 시작할 수 있고, 실패해도 balance/reward 문제로 국소화된다.
- M21은 ball scene을 먼저 열어야 한다. 라보나슛은 축구 skill의 첫 목표가 아니라 `front kick -> ball tap -> angled kick -> crossing-leg kick` 다음 단계다.
- M22 reference-motion loop는 선택 기능이 아니라 handstand/cartwheel/tumble류의 필수 기반이다.

### 가설은 통과했나?
- [x] PASS — 현재 G1 asset은 낮은 단계 humanoid skill에는 충분하지만, acrobatic/ball skill은 scene/contact/reference-motion 보강 없이는 바로 학습 대상으로 삼기 어렵다.
- [ ] FAIL — 무엇이 어긋났나, 가설 수정

### 정의에 반영
- `ROADMAP.md` M20을 feasibility gate 완료로 갱신하고, M19/M21/M22의 선후관계를 보강한다.

### 다음 실험 후보
- M19: `experiments/14-g1-skill-baseline/`에서 `squat -> stand` 또는 `front kick` custom reward wrapper를 실제 학습한다.
- M21: G1 + ball scene을 추가해 `ball tap` metric을 만든다.
