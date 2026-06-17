# 50-g1-stance-constrained-curriculum-ppo — support/slip constrained squat curriculum

## 1. 가설 (Hypothesis)

exp49는 command-conditioned PPO가 visible drop은 만들지만 foot slip 약 3m와 contact loss를 허용했다. support margin과 foot slip을 episode-level failure로 만들고, support가 나빠질수록 action을 stance-locked prior로 되돌리면 shallow standing attractor와 large-slip collapse 사이에 더 안전한 curriculum step을 만들 수 있다.

근거:
- Gait-conditioned RL은 Unitree G1에서 command space를 단계적으로 넓혀 standing/walking/transition을 학습시킨다. https://arxiv.org/html/2505.20619v1 (accessed 2026-06-18)
- UniTracker는 Unitree G1 motion tracking을 goal-conditioned RL과 adaptation으로 처리한다. https://arxiv.org/html/2507.07356v3 (accessed 2026-06-18)
- HuMam은 humanoid RL에서 contact quality, posture, body stability를 reward term으로 분리한다. https://arxiv.org/abs/2509.18046 (accessed 2026-06-18)
- G1 Moves는 G1 motion imitation PPO에서 termination rate, tracking error 등 training metrics를 제공한다. https://huggingface.co/datasets/exptech/g1-moves (accessed 2026-06-18)

## 2. 방법 (Method)

### 셋업
- 모델: local MuJoCo Playground G1 env.
- 초기 정책: exp49 target-0p03 또는 exp46 force/torque residual checkpoint.
- 하네스 구성: one experiment = one commit, raw evidence under `verify/`.

### 시나리오
- V0: exp49 command-conditioned env를 상속한다.
- V1: reset 시 초기 foot XY를 저장하고, support margin 또는 foot slip breach를 episode termination으로 처리한다.
- V2: support/slip health가 낮으면 command action target을 0에 가깝게 줄이는 stance-lock action prior를 추가한다.
- V3: 3cm target drop부터 train/eval한다.

### 측정 metric
- visible pelvis drop, fall time, final height/return, both-feet contact ratio, foot slip, support margin, first support/slip breach.
- M19 PASS는 exp29 visible gate와 native/browser replay가 동시에 통과해야 한다.

## 3. 결과 (Results)

### 데이터
| Run | Verdict | Drop | Contact | 비고 |
|-----|---------|------|---------|------|
| target-0p03-slip-0p08 | DEPTH_PENDING | 0.0762m | 0.38 | exp46 source, 20k PPO, no fall but slip 3.276m and return/contact fail |

### 박제 위치
- `verify/target-0p03-slip-0p08/result.json`
- `verify/target-0p03-slip-0p08/native-eval.json`
- `verify/target-0p03-slip-0p08/stance-constrained-summary.md`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- support/slip termination is active in training: reward dropped to about 80 because breach episodes are strongly constrained.
- Starting from exp46 is more conservative than exp49 and reaches 7.62cm without fall, close to the 8cm visible threshold.
- The remaining blocker is not depth leverage but stance preservation: foot slip still grows to 3.276m, contact ratio stays 0.38, and return fails.

### 가설은 통과했나?
- [ ] PASS — stance/slip constrained training이 visible depth, contact, stance, return을 같이 개선하면.
- [x] FAIL — termination/prior improved depth but did not prevent support/slip breach or contact loss.

### 정의에 반영
- M19 완료 조건은 유지한다. browser replay 없이 native-only로 완료 처리하지 않는다.

### 다음 실험 후보
- foot-fixed residual/action projection 또는 stance-aware motor-target projection으로 발 미끄러짐 자체를 action space에서 제한한다.
