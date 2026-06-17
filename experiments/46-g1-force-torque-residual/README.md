# 46-g1-force-torque-residual — G1 force/torque-aware residual learning

## 1. 가설 (Hypothesis)

exp42/45가 visible-depth collapse를 foot normal force imbalance, support breach, inverse torque spike로 분리했으므로, PPO reward 안에 contact force balance와 lower-body torque proxy를 넣으면 standing attractor를 유지하는 support-only reward보다 visible-depth residual이 개선된다.

## 2. 방법 (Method)

### 셋업
- 모델: local MuJoCo Playground G1 runtime (`C:\tmp\e34`).
- 시작점: exp38 support-aware params가 있으면 그것을 restore하고, 없으면 exp28 default source를 쓴다.
- 하네스 구성: learning experiment 1개. `run_force_torque_residual.py --train` 결과를 `verify/`에 박제한다.

### 외부 근거
- MuJoCo Playground report는 real transfer에서 힘 제한 초과 문제를 torque penalty로 완화했다고 설명한다. URL: https://arxiv.org/html/2502.08844v1 (accessed 2026-06-18)
- FALCON은 Unitree G1 humanoid force-adaptive task에서 torque limit을 고려한 force curriculum과 task-specific reward를 사용한다. URL: https://arxiv.org/html/2505.06776v2 (accessed 2026-06-18)
- Unitree RL Gym은 G1 motion control workflow를 Train -> Play -> Sim2Sim -> Sim2Real로 둔다. URL: https://github.com/unitreerobotics/unitree_rl_gym (accessed 2026-06-18)

### 시나리오
- F0: env compatibility. source policy shape가 새 reward env와 맞는지 확인한다.
- F1: zero-action rollout smoke. contact force balance, lower torque, depth force gate metric이 JAX loop에서 계산되는지 확인한다.
- F2: restored PPO short finetune.
- F3: native MuJoCo gate audit. visible drop, fall, contact, slip, support margin, contact wrench, inverse dynamics를 측정한다.

### 측정 metric
- Training: eval reward trend, reward metric smoke.
- Native: visible drop `>=0.08m`, no fall, final height `>=0.74m`, contact ratio `>=0.90`, foot slip `<=0.15m`.
- Diagnostics: min support margin, LR normal force imbalance, max lower inverse torque.

## 3. 결과 (Results)

### 데이터
| Run | Verdict | Train | Drop | Fell at | 비고 |
|-----|---------|-------|------|---------|------|
| smoke-source | DEPTH_PENDING | - | 0.0080m | never | metric wiring PASS, LR imbalance 0.223, inverse torque 21.6 |
| force-torque-20k | DEPTH_PENDING | 20k | 0.0087m | never | reward 180.211 -> 184.844 -> 180.400, LR imbalance 0.154 |
| force-torque-20k-blend0p25-eval | DEPTH_PENDING | eval only | 0.0097m | never | stable/contact 1.00, but still micro-dip |
| force-torque-20k-blend0p35-eval | DEPTH_PENDING | eval only | 0.0500m | never | larger drop but contact 0.83, slip 1.543m, support min -0.0723m |

### 박제 위치
- `verify/stage-0p74/force-torque-summary.md`
- `verify/stage-0p74/attempts/*/result.json`
- `verify/stage-0p74/attempts/*/native-eval.json`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- Force/torque reward metric은 JAX PPO env에 정상 결합됐다. compatibility, zero-action rollout, restored PPO, native diagnostic이 모두 실행됐다.
- 20k restored PPO는 force balance 쪽을 개선했다. source smoke의 max LR imbalance 0.223이 20k params에서 0.154로 낮아졌고, max lower inverse torque도 21.6 -> 20.8로 소폭 낮아졌다.
- 하지만 visible-depth residual은 생기지 않았다. 기본 0.18 blend는 0.87cm, 0.25 blend는 0.97cm에 머물렀다.
- 0.35 blend는 5.00cm까지 내려가지만 support/contact/stance gate가 깨졌다. exp45와 달리 fall은 피했지만, foot slip 1.543m와 LR imbalance 1.00은 M19 gate 실패다.

### 가설은 통과했나?
- [ ] PASS — native visible squat gate까지 통과
- [x] FAIL — force/torque reward가 force balance는 개선했지만 exp29 visible gate를 통과하지 못했다.

### 정의에 반영
- M19 완료 기준은 유지한다. native gate가 통과하지 않으면 browser replay를 만들지 않는다.

### 다음 실험 후보
- residual action target을 visible pose 쪽으로 더 직접 바꾸거나, WBC/static manifold target을 policy action space에 command로 넣는다. reward-only shaping은 exp38/46에서 둘 다 standing attractor를 못 깼다.
