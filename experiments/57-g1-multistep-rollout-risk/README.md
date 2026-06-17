# 57-g1-multistep-rollout-risk - G1 multi-step rollout risk selector

> `experiments/57-g1-multistep-rollout-risk/README.md` - M19 visible squat 재개 실험. 접근일: 2026-06-18.

## 1. 가설 (Hypothesis)

exp56의 one-step selector가 delayed support collapse를 못 봐서 실패했다면, 후보 blend/CoM feedback을 0.4~0.8초 MuJoCo rollout으로 미리 굴려 비용화하면 8cm visible squat의 fall을 줄이거나 no-fall corridor를 깊게 만들 수 있다.

외부 근거:
- G1은 하체가 각 leg 6 DoF이고 knee range가 약 -0.087~2.880rad, hip pitch가 약 -2.531~2.880rad라 squat pose 자체의 기구학 여지는 있다. Knee motor가 가장 강하고 max torque 120Nm로 문서화되어 있다. URL: https://docs.westonrobot.com/tutorial/unitree/g1_dev_guide/, access date: 2026-06-18.
- Unitree G1 개발 문서도 한쪽 다리 6 DoF 구조를 설명한다. URL: https://support.unitree.com/home/en/G1_developer, access date: 2026-06-18.
- humanoid squat 논문은 TP-MPC + WBC가 WBC 단독보다 trajectory tracking과 knee torque spike를 개선한다고 보고한다. URL: https://www.mdpi.com/1424-8220/25/2/435, access date: 2026-06-18.
- 최근 WB-MPC 문헌은 biped에서 ZMP와 full-body kinematics를 결합해 미래 상태를 예측하고 제어 입력을 최적화하는 방향을 제시한다. URL: https://arxiv.org/html/2505.19540v1, access date: 2026-06-18.
- ZMP regulation을 포함한 WBC는 feet tracking, CoM tracking, joint limit avoidance를 안정성 task로 묶는다. URL: https://www.lirmm.fr/krut/pdf/2014_galdeano_ssd-0568454426/2014_galdeano_ssd.pdf, access date: 2026-06-18.

## 2. 방법 (Method)

### 셋업
- 모델: local G1 MuJoCo model + exp52/55 stabilizer policy/controller stack.
- 코드: `run_multistep_rollout_risk.py`.
- 입력: exp44 selector metrics, exp55 CoM feedback, exp29 visible gate.
- raw evidence: `verify/multistep-rollout-risk/`.

### 시나리오
- Mock/control: exp56 one-step selector 구조를 복사한 뒤, candidate 비용 함수만 multi-step rollout으로 교체했다.
- Real/native: 각 control step에서 blend/feedback candidate를 만들고, candidate마다 0.4s 또는 0.8s 동안 MuJoCo를 미리 굴렸다. 비용은 height error, support/ZMP breach, contact loss, foot slip, normal force imbalance, inverse torque, upright loss를 누적했다.
- Variants:
  - `h0p4-balanced-0p08`
  - `h0p8-balanced-0p08`
  - `h0p4-depth-0p10`
  - `h0p8-depth-0p10`

### 측정 metric
- M19 native gate: fall 없음, visible drop >=0.08m, knee >=0.60rad, hip pitch >=0.35rad, return, contact >=0.90, slip <=0.15m.
- 추가 metric: horizon length, selected blend, feedback scale, support/ZMP margin, total foot normal force, inverse torque.

## 3. 결과 (Results)

### 데이터
| Run | Verdict | Horizon | Drop | Knee | Hip | Contact | Slip | Fell |
|-----|---------|--------:|-----:|-----:|----:|--------:|-----:|------|
| h0p4-balanced-0p08 | FAIL_FALL | 0.4s | 1.5090m | 0.569 | 0.371 | 0.95 | 0.717m | 3.06s |
| h0p8-balanced-0p08 | FAIL_FALL | 0.8s | 1.5078m | 0.465 | 0.430 | 0.91 | 0.890m | 4.62s |
| h0p4-depth-0p10 | FAIL_FALL | 0.4s | 1.5046m | 0.484 | 0.417 | 0.97 | 0.687m | 2.94s |
| h0p8-depth-0p10 | FAIL_FALL | 0.8s | 1.5070m | 0.618 | 0.407 | 0.91 | 0.801m | 4.26s |

Best no-fall run: none.

0.8s horizon은 balanced 8cm 계열에서 fall time을 3.06s -> 4.62s로 늦췄지만, stance slip과 support/ZMP breach를 막지 못했다. 모든 run이 결국 full collapse로 떨어졌고, M19 native gate는 실패했다.

### 박제 위치
- `verify/multistep-rollout-risk/result.json`
- `verify/multistep-rollout-risk/multistep-rollout-risk-summary.md`
- `verify/multistep-rollout-risk/*/native-eval.json`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- G1 squat는 공개 joint range/torque 관점에서는 가능성이 있지만, 현재 stack에서는 pose feasibility가 아니라 contact-consistent whole-body control 문제가 병목이다.
- multi-step rollout risk는 delayed fall을 더 잘 드러내고 일부 fall time을 늦추지만, selector가 안정적인 깊은 basin을 새로 만들지는 못했다.
- 8cm 이상 visible target을 hand-written selector로 밀면 support/ZMP margin이 크게 음수로 깨지고 slip이 0.68~0.89m까지 커진다. 이는 단순 blend 선택 문제가 아니라 stance/contact dynamics 자체를 학습하거나 WBC torque-level로 닫아야 한다는 신호다.

### 가설은 통과했나?
- [ ] PASS
- [x] FAIL - 0.4~0.8s rollout selector는 M19 native gate를 닫지 못했다. 0.8s horizon은 collapse를 지연시켰지만 no-fall visible squat을 만들지 못했다.

### 정의에 반영
- ROADMAP M19의 다음 작업을 one-step selector/hand-written rollout 반복이 아니라 teacher-based residual fine-tune 또는 torque/contact-aware WBC로 좁힌다.

### 다음 실험 후보
- exp55 best no-fall controller를 teacher로 삼아 residual policy를 offline imitation/fine-tune하고, support/ZMP/slip을 termination 또는 critic feature로 넣는다.
- 또는 MuJoCo inverse dynamics/contact force를 직접 쓰는 torque-level WBC prototype으로 stance foot constraint를 hard cost에 가깝게 둔다.
