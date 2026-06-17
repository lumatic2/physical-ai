# 49-g1-command-conditioned-squat-policy — command-conditioned visible squat PPO

## 1. 가설 (Hypothesis)

exp47/48은 static visible target을 외부에서 additive로 주입했기 때문에 policy가 support state를 보고 target을 조절할 기회가 없었다. 기존 observation의 3D `command` 슬롯을 squat phase/depth command로 재해석하고 PPO reward를 command-conditioned pose/action tracking으로 바꾸면, stabilizer prior를 유지하면서 visible-depth 방향으로 더 학습될 수 있다.

근거:
- UniTracker는 Unitree G1에서 goal-conditioned RL, deployable student policy, fast adaptation으로 다양한 motion tracking을 처리한다. https://arxiv.org/html/2507.07356v3 (accessed 2026-06-18)
- Unitree RL Gym은 G1을 포함하고 `Train -> Play -> Sim2Sim -> Sim2Real` 흐름을 제시한다. https://github.com/unitreerobotics/unitree_rl_gym (accessed 2026-06-18)
- Unitree RL Mjlab은 MuJoCo 기반 G1 RL 연구/배포 흐름을 지원한다. https://github.com/unitreerobotics/unitree_rl_mjlab (accessed 2026-06-18)
- Gait-conditioned RL은 Unitree G1에서 command/gait-conditioned objective routing과 curriculum으로 standing/walking/transition을 단일 정책에 넣는 접근을 제시한다. https://arxiv.org/abs/2505.20619 (accessed 2026-06-18)

## 2. 방법 (Method)

### 셋업
- 모델: local MuJoCo Playground G1 env.
- 초기 정책: exp46 force/torque residual stabilizer checkpoint.
- 하네스 구성: one experiment = one commit, raw evidence under `verify/`.

### 시나리오
- V0: observation 크기를 바꾸지 않고 기존 `command` 3D 슬롯을 `[target_drop_fraction, return_phase, visible_gain]`으로 재사용한다.
- V1: action target은 외부 injection이 아니라 policy output만 사용한다.
- V2: reward에 command pose/height/action target, support gate, return phase를 추가하고 restored PPO를 짧게 실행한다.

### 측정 metric
- visible pelvis drop, fall time, final height/return, both-feet contact ratio, foot slip, support margin, lower inverse torque.
- M19 PASS는 exp29 visible gate와 native/browser replay가 동시에 통과해야 한다.

## 3. 결과 (Results)

### 데이터
| Run | Verdict | Drop | Contact | 비고 |
|-----|---------|------|---------|------|
| target-0p08 | RETURN_PENDING | 0.2885m | 0.37 | 20k PPO, no fall but final height 0.4665m, slip 2.945m |
| target-0p03 | RETURN_PENDING | 0.2536m | 0.37 | 20k PPO, no fall but final height 0.5014m, slip 3.028m |

### 박제 위치
- `verify/target-0p08/result.json`
- `verify/target-0p08/native-eval.json`
- `verify/target-0p08/command-conditioned-summary.md`
- `verify/target-0p03/result.json`
- `verify/target-0p03/native-eval.json`
- `verify/target-0p03/command-conditioned-summary.md`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- 기존 3D command 슬롯을 squat phase/depth command로 재사용하면 checkpoint shape compatibility는 유지된다.
- 20k restored PPO는 8cm command와 3cm curriculum command 모두에서 support/contact를 지키지 못했다. drop은 커졌지만 발 slip이 약 3m로 커지고 return gate를 실패했다.
- command를 observation/reward에 넣는 것만으로는 부족하다. 다음 단계는 command curriculum 자체보다 support-constrained reset/termination 또는 stance-lock action prior를 학습 loop에 넣어야 한다.

### 가설은 통과했나?
- [ ] PASS — visible depth, no-fall, contact, stance, return gate가 같이 통과하면.
- [x] FAIL — command-conditioned PPO는 visible drop을 만들었지만 contact/stance/return gate를 동시에 만족하지 못했다.

### 정의에 반영
- M19 완료 조건은 유지한다. browser replay 없이 native-only로 완료 처리하지 않는다.

### 다음 실험 후보
- support-constrained reset/termination과 stance-lock action prior를 넣은 curriculum PPO를 3cm -> 5cm -> 8cm 단계로 늘린다.
