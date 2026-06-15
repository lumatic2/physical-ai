# 15-g1-skill-baseline — G1 squat skill baseline

> M19a. G1이 기존 joystick walking이 아니라, compiled behavior spec에서 온 첫 custom skill target을 native MuJoCo에서 실행 가능한지 확인한다.

## 1. 가설 (Hypothesis)

`g1_squat` behavior spec이 실제 G1 scene에서 scripted position-control baseline으로도 안정적으로 실행되지 않으면, RL reward wrapper를 학습하기 전에 target 자체를 수정해야 한다.

반증 기준:
- native MuJoCo에서 6초 squat trajectory 중 낙상한다.
- base height gate 아래로 내려가거나 joint limit을 넘는다.
- compiled spec의 metric/constraint가 evaluator로 연결되지 않는다.

## 2. 방법 (Method)

### 셋업
- 모델: `experiments/03-digital-twin/web/assets/scenes/g1/scene_g1_policy.xml`
- 데이터: `experiments/14-skill-authoring/verify/g1_squat.compiled.json`
- 하네스 구성: `evaluate_squat_baseline.py`

### 시나리오
- S1: `knees_bent` keyframe에서 시작한다.
- S2: 2초 descend, 1초 hold, 3초 return-to-stand target schedule을 position actuator에 넣는다.
- S3: fall, base height, joint-limit violation, energy proxy를 raw JSON으로 남긴다.

### 측정 metric
- `fell_at`
- `min_height`
- `max_joint_limit_violation`
- `energy_proxy`

## 3. 결과 (Results)

### 데이터
| Run | Verdict | Cost | Retries | 비고 |
|-----|---------|------|---------|------|
| S1-S3 scripted native baseline | FAIL | local MuJoCo | 1 | hold/mild/deep 모두 1.24~1.25초에 fall |

### 박제 위치
- `verify/g1-squat-scripted-baseline.json`
- `verify/g1-squat-scripted-baseline.md`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- `g1_squat`는 target spec으로는 명확하지만, open-loop position-control baseline은 안정적이지 않다.
- hold/mild/deep squat 모두 1.24~1.25초에 fall한다. 즉 "스쿼트 target이 너무 깊어서"가 아니라 balance stabilization 없이 posture target만 넣는 접근이 약하다.
- M19의 다음 단계는 바로 long-run PPO가 아니라, balance reward/controller stabilization을 먼저 넣은 custom env smoke다.

### 가설은 통과했나?
- [ ] PASS — scripted baseline이 no-fall로 통과해 RL target으로 쓸 수 있다.
- [x] FAIL — scripted baseline이 넘어졌다. M19는 learned policy 전에 balance-stabilized reward wrapper가 필요하다.

### 정의에 반영
- `ROADMAP.md` M19는 scripted baseline gate 완료, learned policy는 balance-stabilized reward wrapper 이후 long-run으로 분리한다.

### 다음 실험 후보
- M19b: `g1_squat` balance reward wrapper + short PPO smoke.
- M19c: ONNX export + browser skill playback.
