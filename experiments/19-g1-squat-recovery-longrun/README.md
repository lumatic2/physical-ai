# 19-g1-squat-recovery-longrun — G1 squat recovery shaping

> M19c. exp18의 100k short-trained policy가 native MuJoCo에서 1.24초에 fall한 뒤, fall 기준을 학습 env에 더 직접 넣고 longer PPO smoke로 native fall time이 개선되는지 확인한다.

## 1. 가설 (Hypothesis)

exp18은 reward/PPO loop에는 진입했지만, native diagnostic이 보는 `base_height` 실패를 학습 termination이 충분히 강하게 보지 못했다. `base_height < 0.50`, torso upright threshold, recovery/upright reward를 학습 env에 넣으면 short policy보다 native fall time이 개선될 수 있다.

반증 기준:
- recovery env reset/step이 깨진다.
- 200k-300k PPO smoke가 학습 루프에 진입하지 못한다.
- native diagnostic fall time이 exp18 baseline 1.24초 이하로 유지된다.

## 2. 방법 (Method)

### 셋업
- 기반: exp18 `G1Squat`의 repo-local subclass 패턴.
- 변경: shallow squat target, slower schedule, height/upright termination, recovery reward.
- 평가 기준: native MuJoCo closed-loop 6초 diagnostic.

### 시나리오
- S1: recovery env zero-action rollout smoke.
- S2: 300k 이하 PPO smoke.
- S3: saved params native diagnostic.

### 측정 metric
- rollout obs/action shape
- eval reward curve
- native `fell_at`, `upright_s`, `min_height`, `max_pose_error`, `max_joint_limit_violation`, `energy_proxy`

## 3. 결과 (Results)

### 데이터
| Run | Verdict | Cost | Retries | 비고 |
|-----|---------|------|---------|------|
| S1 recovery env rollout smoke | PASS | local WSL/JAX | 0 | 20-step no termination, height min 0.722, torso_up min 0.995 |
| S2 PPO smoke | PASS | 300k target / 327680 eval steps / 5.53min | 0 | eval reward 1.406 -> 5.994 |
| S3 native diagnostic | FAIL_DIAGNOSTIC | 6.0s native MuJoCo | 0 | 1.24s fall, no improvement vs exp18 baseline |

### 박제 위치
- `verify/g1-squat-recovery-longrun.json`
- `verify/train-native.log`
- `verify/train/rewards.txt`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- Height/upright termination과 recovery reward를 넣어도, short/medium PPO reward 상승이 native stability로 바로 이어지지 않는다.
- 300k target run은 eval reward를 1.406 -> 5.994까지 올렸지만 native fall time은 exp18과 같은 1.24초였다.
- 실패 시점은 squat target이 깊어지기 전부터 base height가 빠르게 낮아지는 구간이다. 단순 reward scale 보강보다 stabilizer prior, reference motion tracking, pretrained policy initialization이 필요하다.

### 가설은 통과했나?
- [ ] PASS — native fall time이 exp18 1.24초보다 개선됐다.
- [x] FAIL — reward/recovery shaping만으로는 개선되지 않았다.

### 정의에 반영
- `ROADMAP.md` M19를 "reward-only 개선 실패"로 갱신한다. 다음 단계는 ONNX/browser export가 아니라 M22의 reference tracking 또는 pretrained stabilizer 결합이다.

### 다음 실험 후보
- G1 squat reference trajectory를 env reward에 직접 결합한다.
- 기존 G1 walking/standing policy를 stabilizer prior로 쓸 수 있는지 조사한다.
- native diagnostic이 6초 no-fall에 도달하기 전에는 browser playback을 보류한다.
