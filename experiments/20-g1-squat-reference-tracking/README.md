# 20-g1-squat-reference-tracking — G1 squat reference reward

> M19d/M22. reward-only recovery shaping이 native fall time을 개선하지 못한 뒤, exp17의 compiled squat reference motion을 실제 PPO reward에 결합해 native stability가 개선되는지 확인한다.

## 1. 가설 (Hypothesis)

exp18/19는 target pose schedule을 env 안에서 직접 만들었고, reward가 올라가도 native fall time은 1.24초에 머물렀다. exp17의 50Hz reference trajectory를 reward target으로 쓰고, lower-body+waist tracking과 balance/fall reward를 같이 주면 native fall time이 개선될 수 있다.

반증 기준:
- compiled reference trajectory를 env reward에 넣을 수 없다.
- rollout smoke 또는 PPO smoke가 깨진다.
- native diagnostic fall time이 exp18/19 baseline 1.24초 이하로 유지된다.

## 2. 방법 (Method)

### 셋업
- 기반: exp19 training/native diagnostic harness.
- reference: `experiments/17-motion-to-policy-loop/verify/g1_squat_reference.compiled.json`.
- 추적 대상: G1 qpos[7:]의 앞 15개 lower-body+waist joints.
- arm joints: default pose 유지 항으로 처리.

### 시나리오
- S1: reference tracking env zero-action rollout smoke.
- S2: 300k 이하 PPO smoke.
- S3: saved params native MuJoCo diagnostic.

### 측정 metric
- rollout obs/action shape
- eval reward curve
- native `fell_at`, `upright_s`, `min_height`, `max_reference_error`, `max_joint_limit_violation`, `energy_proxy`

## 3. 결과 (Results)

### 데이터
| Run | Verdict | Cost | Retries | 비고 |
|-----|---------|------|---------|------|
| S1 reference env rollout smoke | PASS | local WSL/JAX | 0 | 20-step no termination, reference_error_last 0.0139 |
| S2 PPO smoke | PASS | 300k target / 327680 eval steps / 5.23min | 0 | eval reward 2.612 -> 7.565 |
| S3 native diagnostic | FAIL_DIAGNOSTIC | 6.0s native MuJoCo | 0 | 1.24s fall, no improvement vs exp18/19 baseline |

### 박제 위치
- `verify/g1-squat-reference-tracking.json`
- `verify/train-native.log`
- `verify/train/rewards.txt`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- exp17의 compiled reference trajectory를 실제 PPO reward에 결합하는 경로는 열렸다.
- 300k target run은 eval reward를 2.612 -> 7.565까지 올렸지만 native fall time은 exp18/19와 같은 1.24초였다.
- reference joint tracking도 단독으로는 G1 squat 안정화를 해결하지 못한다. 실패 구간은 1.0~1.4초 사이 base height collapse이며, reference error보다 balance/stabilizer 문제가 더 지배적이다.

### 가설은 통과했나?
- [ ] PASS — native fall time이 1.24초보다 개선됐다.
- [x] FAIL — reference tracking만으로는 개선되지 않았다.

### 정의에 반영
- `ROADMAP.md` M22의 motion tracking reward 결합 항목은 완료로 갱신한다. M19의 learned squat 성공 조건은 pretrained stabilizer 또는 standing/recovery policy initialization 이후로 미룬다.

### 다음 실험 후보
- G1 walking/standing policy params를 stabilizer prior로 재사용할 수 있는지 조사한다.
- squat를 처음부터 학습하지 말고 stable standing policy에서 fine-tune하는 경로를 연다.
- native diagnostic이 6초 no-fall에 도달하기 전에는 browser playback을 보류한다.
