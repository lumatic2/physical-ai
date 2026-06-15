# 23-g1-squat-target-sanity — G1 squat target sanity probe

> M19g. exp22에서 stabilizer fine-tune이 no-fall은 유지했지만 squat depth가 거의 생기지 않았기 때문에, 추가 PPO 전에 reference/action target 자체가 native MuJoCo에서 base height drop을 만들 수 있는지 분리 검증한다.

## 1. 가설 (Hypothesis)

exp17의 squat reference joint targets 또는 deepened leg targets를 native position-control로 직접 넣으면 base height가 0.70m 아래로 내려간다. 이때 안정적으로 내려가면 PPO/curriculum이 병목이고, 내려가지만 넘어지면 controller/curriculum이 병목이며, 내려가지 않으면 target/action 구조를 재설계해야 한다.

반증 기준:
- scripted target probe가 실행되지 않는다.
- 모든 variant가 0.70m 아래로 내려가기 전에 fall하거나, 안정적이더라도 height가 standing 근처에 머문다.

## 2. 방법 (Method)

### 셋업
- scene: `experiments/03-digital-twin/web/assets/scenes/g1/scene_g1_policy.xml`.
- reference: `experiments/17-motion-to-policy-loop/verify/g1_squat_reference.compiled.json`.
- engine: native `mujoco.MjData` direct position target, 50Hz control, 6s horizon.

### 시나리오
- S1: `reference_direct` - exp17 reference targets directly.
- S2: `reference_slow_2x` - same reference at half speed.
- S3: `reference_deepened_1p35` - lower-body/waist deltas amplified 1.35x.
- S4: `scripted_deep_legs` - exp15 deep leg pose interpolated over 2s.

### 측정 metric
- min/final base height
- fall time
- max reference error
- max joint-limit violation
- torso up vector

## 3. 결과 (Results)

### 데이터
| Run | Verdict | Cost | Retries | 비고 |
|-----|---------|------|---------|------|
| S1-S4 native target probe | TARGET_LOWERING_UNSTABLE | local native MuJoCo / 7.2s | 0 | 모든 variant가 height drop은 만들지만 1.22s 전후 fall |

| Variant | Verdict | Min height | Fell at | Max ref err | Joint limit |
|---|---|---:|---:|---:|---:|
| reference_direct | TARGET_LOWERING_UNSTABLE | -0.766 | 1.22 | 0.19066 | 0.02983 |
| reference_slow_2x | TARGET_LOWERING_UNSTABLE | -0.776 | 1.22 | 0.15013 | 0.02795 |
| reference_deepened_1p35 | TARGET_LOWERING_UNSTABLE | -0.765 | 1.22 | 0.18335 | 0.02996 |
| scripted_deep_legs | TARGET_LOWERING_UNSTABLE | -0.742 | 1.22 | 0.14317 | 0.03075 |

### 박제 위치
- `verify/g1-squat-target-sanity.json`
- `verify/g1-squat-target-sanity.md`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- exp17 squat reference와 exp15 deep leg pose는 native position-control에서 base height drop을 만들 수 있다. 즉 exp22의 shallow result는 target이 완전히 무효라서 생긴 현상은 아니다.
- 네 variant 모두 1.22초 전후에 fall했다. 속도를 2배 늦추거나 joint delta를 1.35배 키워도 안정성은 개선되지 않았다.
- 다음 병목은 target redesign보다 stabilizer를 유지한 depth curriculum/controller다. 특히 exp21/22 stabilizer가 standing attractor에 머무는 문제를, target을 한 번에 강제하는 대신 0.74 -> 0.72 -> 0.70처럼 stage별로 낮춰야 한다.

### 가설은 통과했나?
- [ ] PASS — target이 안정적으로 squat depth를 만든다.
- [x] FAIL — target은 depth를 만들지만 안정성이 없다.

### 정의에 반영
- `ROADMAP.md` M19의 다음 작업을 target redesign보다 depth curriculum/controller redesign으로 좁힌다.

### 다음 실험 후보
- staged depth curriculum: exp21 stabilizer init에서 시작해 target min height를 0.74 -> 0.72 -> 0.70 -> 0.66으로 낮춘다.
- balance controller redesign: direct target 대신 action residual이 stabilizer pose에서 너무 멀어지지 않도록 residual/action scale schedule을 둔다.
