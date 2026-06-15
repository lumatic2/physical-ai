# 17-motion-to-policy-loop — reference motion compile probe

> M22. handstand/flip처럼 sparse reward만으로 어려운 동작을 위해, 먼저 reference motion을 policy 학습 신호로 바꿀 데이터 계약을 연다.

## 1. 가설 (Hypothesis)

키프레임 기반 reference motion을 schema로 고정하고 50Hz target trajectory로 보간할 수 있으면, 이후 imitation/RL hybrid가 쓸 `reference_tracking_error` reward를 만들 수 있다.

반증 기준:
- keyframe 시간이 단조 증가하지 않거나 joint target 길이가 맞지 않는다.
- reference motion을 fixed-rate samples로 바꿀 수 없다.
- reward/eval metric 계약이 behavior spec과 연결되지 않는다.

## 2. 방법 (Method)

### 셋업
- 모델: G1 15-joint lower-body + waist reference subset.
- 데이터: `examples/g1_squat_reference.json`
- 하네스 구성: `reference_motion.schema.json`, `compile_reference_motion.py`

### 시나리오
- S1: keyframe reference motion format을 만든다.
- S2: 50Hz samples로 보간한다.
- S3: duration, min base height, max joint delta, smoothness cost를 산출한다.

### 측정 metric
- sample count
- duration
- min base height
- max joint delta
- smoothness cost

## 3. 결과 (Results)

### 데이터
| Run | Verdict | Cost | Retries | 비고 |
|-----|---------|------|---------|------|
| S1-S3 reference compile | PASS | local Python | 0 | G1 squat reference motion 201 samples로 compile |

### 박제 위치
- `verify/g1_squat_reference.compiled.json`
- `verify/reference-motion-compile.md`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- M22의 첫 단계는 고난도 동작 자체가 아니라 reference target format이다. 이 계약이 있어야 handstand/cartwheel/tumble을 sparse reward가 아닌 tracking problem으로 낮출 수 있다.
- 현재 probe는 G1 lower-body squat reference만 다룬다. handstand/flip은 full-body contact/reference authoring이 추가로 필요하다.
- M19의 squat 실패는 reference trajectory만으로 해결되지 않는다. tracking reward와 balance/fall reward가 함께 필요하다.

### 가설은 통과했나?
- [x] PASS — keyframe reference motion을 fixed-rate trajectory와 reward term 계약으로 compile했다.
- [ ] FAIL — 무엇이 어긋났나, 가설 수정

### 정의에 반영
- `ROADMAP.md` M22를 reference format/probe 완료로 갱신한다.

### 다음 실험 후보
- full-body `handstand_prep_reference` authoring.
- M19 custom env에서 `reference_tracking_error + balance` reward 결합.
