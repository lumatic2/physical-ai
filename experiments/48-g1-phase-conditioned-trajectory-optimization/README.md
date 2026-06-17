# 48-g1-phase-conditioned-trajectory-optimization — phase-conditioned G1 squat trajectory

## 1. 가설 (Hypothesis)

G1에서 visible squat 자체는 공개 evidence상 가능하지만, exp47처럼 command를 시간 기반으로 계속 누르면 support breach가 먼저 온다. 따라서 descend/return phase를 support, slip, upright, depth guard로 전환하면 2.32cm보다 깊은 stable drop을 만들 수 있다.

근거:
- Unitree 공식 G1 페이지는 큰 관절 가동 범위, 23~43 joint motors, imitation/reinforcement-learning driven 구성을 명시한다. https://www.unitree.com/g1/ (accessed 2026-06-18)
- Clone은 Unitree G1에서 waving, squatting, squatted-position stand-up, jumping 같은 whole-body motion tracking을 보고한다. https://arxiv.org/html/2506.08931v1 (accessed 2026-06-18)
- UniTracker는 29-DoF Unitree G1에서 8,100개 이상 motion tracking 및 MuJoCo lateral squat balance 사례를 보고한다. https://arxiv.org/html/2507.07356v2 (accessed 2026-06-18)
- Unitree RL Gym은 G1을 포함하고 `Train -> Play -> Sim2Sim -> Sim2Real` 흐름을 제시한다. https://github.com/unitreerobotics/unitree_rl_gym (accessed 2026-06-18)

## 2. 방법 (Method)

### 셋업
- 모델: local MuJoCo Playground G1 env + exp46 force/torque residual policy checkpoint.
- 데이터: exp45 static stance-stable visible target, exp47 visible-target command runner.
- 하네스 구성: one experiment = one commit, raw evidence under `verify/`.

### 시나리오
- V0: exp47 additive visible target을 재사용한다.
- V1: controller phase를 `descend -> return -> stand`로 나누고, target drop/support/slip/upright guard 중 하나가 걸리면 즉시 return한다.
- V2: guard margin과 return rate를 sweep해서 stable depth 상한을 측정한다.

### 측정 metric
- visible pelvis drop, fall time, final height/return, both-feet contact ratio, foot slip, support margin, lower inverse torque, phase switch reason.
- M19 PASS는 exp29 visible gate와 native/browser replay가 동시에 통과해야 한다.

## 3. 결과 (Results)

### 데이터
| Run | Verdict | Drop | Contact | 비고 |
|-----|---------|------|---------|------|
| stop-0p03-support0p030 | DEPTH_PENDING | 0.0311m | 1.00 | no-fall, return PASS, slip 0.016m |
| stop-0p05-support0p030 | FAIL_FALL | 1.5104m | 0.84 | support breach 뒤 3.42s fall |
| stop-0p08-support0p030 | FAIL_FALL | 1.5171m | 0.78 | support breach 뒤 3.20s fall |
| guard-0p08-support0p045 | DEPTH_PENDING | 0.0292m | 1.00 | stricter support guard, no-fall |
| fast-return-0p08 | FAIL_FALL | 1.5227m | 0.87 | return을 빠르게 해도 2.84s fall |
| low-policy-fast-return | FAIL_FALL | 1.5384m | 0.89 | 8cm 진입 후 return했지만 4.00s fall |

### 박제 위치
- `verify/attempts/*/native-eval.json`
- `verify/phase-trajectory-summary.md`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- phase-conditioned guard는 exp47 best stable 2.32cm보다 깊은 3.11cm no-fall return을 만들었다.
- 5cm 이상을 노리는 variant는 command를 0으로 되돌린 뒤에도 이미 support state가 깨져 지연 fall로 이어졌다.
- 공개 사례는 G1 squat 가능성을 지지하지만, 이 repo의 stabilizer+additive visible target contract는 8cm visible gate를 안정적으로 통과하기에 부족하다.

### 가설은 통과했나?
- [ ] PASS — 8cm visible gate를 no-fall/contact/return으로 통과하면.
- [x] FAIL — phase-conditioned return은 stable depth를 3.11cm까지 개선했지만 8cm 전에 support/stance trade-off에 막혔다.

### 정의에 반영
- M19 완료 조건은 유지한다. browser replay 없이 native-only로 완료 처리하지 않는다.

### 다음 실험 후보
- phase controller로 8cm에 못 가면, target command를 observation/action contract에 넣고 PPO로 재학습한다.
