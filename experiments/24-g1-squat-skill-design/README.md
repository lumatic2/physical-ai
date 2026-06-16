# 24-g1-squat-skill-design — G1 squat skill design gate

> M19 design gate. 더 학습하기 전에, "스쿼트"를 G1 디지털 트윈에서 어떤 skill로 볼지 정의하고, 성공 기준과 학습 방법론을 고정한다.

## 1. 가설 (Hypothesis)

G1 squat를 먼저 동작 정의, metric, controller choice, curriculum으로 분해하면, 다음 학습 실험은 "height를 낮춰본다"가 아니라 재현 가능한 humanoid skill acquisition 실험이 된다.

반증 기준:
- 스쿼트 성공 기준이 base height 하나로만 정의되어 knee/hip flexion, torso stability, foot contact, return-to-stand를 설명하지 못한다.
- 현재 G1 morphology와 actuator/contact 모델에서 요구하는 squat depth가 물리적으로 불명확하다.
- 선택한 학습 방법론이 exp15-23 실패 원인을 피하지 못한다.

## 2. 방법 (Method)

### 셋업
- 모델: G1 native/browser digital twin, `scene_g1_policy.xml`, prior G1 walking policy.
- 데이터: exp14 `g1_squat` behavior spec, exp17 squat reference motion, exp15-23 native diagnostics.
- 하네스 구성: 문서 설계 게이트. 이 단계에서는 새 학습을 돌리지 않는다.

### 스쿼트 정의

이 프로젝트에서 M19의 squat는 "사람 스쿼트를 정확히 모사"가 아니라 **G1 morphology에서 가능한 controlled squat-like lowering and return**으로 정의한다.

필수 조건:
- 양발 접촉을 유지한다.
- torso가 전도되지 않고 uprightness gate를 통과한다.
- hip/knee/ankle이 함께 굽혀져 base height가 standing보다 유의미하게 낮아진다.
- 낮아진 자세를 짧게 유지한 뒤 다시 stand로 복귀한다.
- 전체 동작이 native MuJoCo에서 no-fall로 재현된다.

비목표:
- 사람 체형 기준의 deep squat 재현.
- Atlas 영상과 같은 고난도 전신 acrobatics.
- browser에서 그럴듯하게 보이는 playback만 먼저 만드는 것.

### 성공 기준

M19의 다음 학습 실험은 아래를 모두 만족해야 "squat skill candidate"로 본다.

| Metric | 최소 기준 | 이유 |
|---|---:|---|
| native horizon | 6.0s no-fall | exp21 stabilizer 기준을 잃지 않기 위함 |
| min base height | <= 0.70m | exp21/22의 0.75m standing attractor와 구분 |
| controlled depth | target stage 도달 후 0.5s 이상 유지 | 순간 낙하를 squat로 오판하지 않기 위함 |
| return-to-stand | final height >= 0.74m | lowering만 성공한 정책 제외 |
| torso uprightness | fall gate 미통과 + torso up 유지 | sitting/collapse 제외 |
| foot stability | 양발 접촉 유지, 큰 slip 없음 | jump/fall 기반 height drop 제외 |
| action smoothness | residual/action penalty 로그 보존 | 불안정한 bang-bang controller 제외 |

`0.70m`는 최종 정의가 아니라 다음 gate다. 이 기준을 안정적으로 넘기면, knee/hip angle 기반 depth threshold를 추가해 "얕은 squat / medium squat / deep squat"로 다시 세분화한다.

### 후보 방법론

| 후보 | 장점 | 위험 | 판정 |
|---|---|---|---|
| open-loop position target | 구현 단순, target sanity 확인 가능 | exp15/23에서 1.22s 전후 fall | 보류 |
| scratch PPO reward | 새 skill policy라는 의미가 명확 | exp18-20에서 reward는 올라도 native fall 고정 | 보류 |
| reference tracking only | M22와 연결 쉬움 | stabilizer prior 없이 fall 해결 실패 | 단독 사용 보류 |
| walking stabilizer fine-tune | exp21에서 6s no-fall 증명 | standing attractor에 머무름 | 채택하되 curriculum 필요 |
| staged depth curriculum | 안정성을 유지하며 depth 요구를 점진 증가 | stage 설계가 약하면 얕은 자세에 수렴 | 다음 실험 후보 |
| residual controller with penalty schedule | stabilizer에서 멀어지는 action을 제어 가능 | 구현 복잡도 증가 | curriculum과 함께 사용 |

### 선택한 방향

다음 구현 실험은 **walking stabilizer prior + staged depth curriculum + residual/action regularization**으로 간다.

설계 원칙:
- exp21 stabilizer를 출발점으로 삼는다.
- target min height를 한 번에 강제하지 않는다.
- stage를 `0.74 -> 0.72 -> 0.70 -> 0.66` 순서로 낮춘다.
- 각 stage는 native diagnostic을 통과해야 다음 stage로 넘어간다.
- policy가 stabilizer pose에서 급격히 멀어지지 않도록 residual penalty 또는 action scale schedule을 둔다.
- browser playback은 native `<=0.70m + 6s no-fall + return-to-stand` 이후에만 연다.

### 측정 metric
- `fell_at`
- `min_base_height`
- `hold_duration_at_target`
- `final_base_height`
- `torso_up_min`
- `foot_contact_ratio`
- `foot_slip_distance`
- `max_reference_error`
- `mean_action_delta`
- `stage_passed`

## 3. 결과 (Results)

### 데이터
| Run | Verdict | Cost | Retries | 비고 |
|-----|---------|------|---------|------|
| S1 design gate | PASS_DESIGN | local docs | 0 | M19 다음 학습 방향을 curriculum/controller로 고정 |

### 박제 위치
- 이 문서 자체가 설계 게이트 artifact다.
- 다음 raw artifact는 `experiments/25-g1-squat-depth-curriculum/verify/stage-*/`에 남긴다.

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- M19의 목표는 "G1이 사람처럼 완벽히 스쿼트한다"가 아니라, G1 digital twin에서 정의된 squat-like skill을 안정적으로 lowering/hold/return하는 것이다.
- exp21의 no-fall 성과와 exp23의 target-lowering 성과는 각각 절반의 증거다. 다음 실험은 둘을 연결해야 한다.
- base height만으로는 부족하지만, 다음 gate에서는 `0.70m`가 standing attractor를 벗어났는지 판정하는 실용적인 1차 기준이다.
- browser demo는 연구 결과의 표현면이지, native skill 성공의 대체물이 아니다.

### 가설은 통과했나?
- [x] PASS — 다음 학습 실험의 정의, 성공 기준, 방법론, 보류한 방법이 분리됐다.
- [ ] FAIL — 무엇이 어긋났나, 가설 수정

### 정의에 반영
- M19는 `staged depth curriculum/controller redesign` 전에 이 design gate를 통과해야 한다.
- 다음 실험 번호는 `25-g1-squat-depth-curriculum`으로 둔다.

### 다음 실험 후보
- `experiments/25-g1-squat-depth-curriculum/`: exp21 stabilizer prior에서 시작해 stage별 native no-fall/depth/return metric을 검증한다.
- 성공 시 ONNX export와 browser reference-vs-policy playback으로 이동한다.
