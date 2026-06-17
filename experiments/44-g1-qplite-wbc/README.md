# 44-g1-qplite-wbc — G1 one-step QP-lite WBC

## 1. 가설 (Hypothesis)

exp41의 soft WBC가 collapse를 피하려고 blend를 너무 줄여 shallow corridor에 머물렀다면, 매 control step에서 IK blend 후보를 one-step lookahead로 평가하고 pelvis height, foot pose, CoM/support, vertical momentum, foot force balance, inverse torque cost를 함께 최소화하면 visible-depth 후보를 더 안전하게 고를 수 있다.

## 2. 방법 (Method)

### 셋업
- 모델: exp28/36/41/42의 local MuJoCo G1, walking stabilizer policy, foot-fixed IK target.
- 데이터: exp42 contact wrench/inverse dynamics diagnostic, exp43 public/local static squat feasibility.
- 하네스 구성: learning experiment 1개. `run_qplite_wbc.py --sweep` 결과를 `verify/`에 박제한다.

### 외부 근거
- Humanoid WBC 문헌은 pelvis/CoM, foot contact, contact force, joint limits를 하나의 최적화 문제로 같이 다루는 방향을 제시한다. URL: https://arxiv.org/html/2506.14278v1 (accessed 2026-06-18)
- MuJoCo 문서는 inverse dynamics/contact computation이 contact-rich dynamics 진단에 직접 쓰일 수 있음을 설명한다. URL: https://mujoco.readthedocs.io/en/stable/computation/index.html (accessed 2026-06-18)
- contact-implicit inverse-dynamics trajectory optimization은 접촉을 포함한 로봇 제어에서 inverse dynamics 기반의 단순한 예측 최적화가 실시간 제어 후보가 될 수 있음을 보인다. URL: https://arxiv.org/html/2309.01813v3 (accessed 2026-06-18)
- Unitree G1 whole-body tracking 사례는 G1에서 squatting 동작이 whole-body coordination task로 다뤄진다는 점을 보인다. URL: https://arxiv.org/html/2506.08931v1 (accessed 2026-06-18)

### 시나리오
- V0: exp41/42 재사용. soft WBC의 shallow/fall 경계를 baseline으로 둔다.
- V1: `force_strict` QP-lite. support/contact/force/inverse torque penalty를 크게 둔다.
- V2: `depth_biased` QP-lite. height tracking weight를 키워 visible target 접근성을 본다.
- V3: native gate audit. visible drop, fall, return height, contact ratio, foot slip, support margin, inverse torque를 동시에 본다.

### 측정 metric
- M19 native gate: `visible_drop >= 0.08m`, no fall, `final_height >= 0.74m`, contact ratio `>= 0.90`, foot slip `<= 0.15m`, joint violation `<= 0.05`.
- WBC diagnostic: min support margin, max LR normal imbalance, max foot normal force, max lower inverse torque, max inverse-actuator gap, selected blend.

## 3. 결과 (Results)

### 데이터
| Run | Verdict | Drop | Fell at | 비고 |
|-----|---------|-----:|--------:|------|
| qplite-0p08-force-strict | DEPTH_PENDING | 0.0089m | never | force/support를 강하게 지키면 사실상 micro-dip만 선택 |
| qplite-0p08-depth-biased | DEPTH_PENDING | 0.0227m | never | exp41 soft WBC 수준의 안정 corridor |
| qplite-0p12-force-strict | DEPTH_PENDING | 0.0269m | never | contact 0.99, support margin 5.0cm, depth 부족 |
| qplite-0p12-depth-biased | DEPTH_PENDING | 0.0386m | never | 이번 실험의 best no-fall depth. support margin 1.84cm, LR imbalance 1.00 |
| qplite-0p12-depth-aggressive | FAIL_FALL | 1.5186m | 2.34s | visible-depth leverage는 있으나 support collapse/foot slip 0.823m |
| qplite-0p16-depth-aggressive | FAIL_FALL | 1.5090m | 2.14s | 더 깊은 target도 같은 collapse mode |

### 박제 위치
- `verify/qplite-summary.md`
- `verify/attempts/*/qplite-native-eval.json`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- one-step QP-lite는 exp41보다 no-fall corridor를 조금 넓혔다. best no-fall은 `qplite-0p12-depth-biased`의 3.86cm drop으로, exp41 best 2.56cm보다 깊다.
- 하지만 M19 visible gate인 8cm에는 못 갔다. force/support를 크게 보면 선택기가 blend를 줄이고, height를 크게 보면 2.14~2.34초에 fall한다.
- collapse는 exp42와 같은 신호를 보인다. aggressive variant는 support margin이 약 `-0.60m`, foot slip `0.76~0.82m`, normal force `2524~4002`, LR imbalance `1.00`으로 터졌다.
- 따라서 문제는 "blend를 더 잘 고르는 것"만으로는 부족하다. 다음은 action target 자체를 stance-stable manifold로 제한하거나, torque/action-space WBC 또는 학습 policy 안에 contact-force penalty를 넣어야 한다.

### 가설은 통과했나?
- [ ] PASS — native visible squat gate를 닫는 경우
- [x] FAIL — QP-lite selection은 stable depth를 3.86cm까지 늘렸지만 native visible squat gate를 통과하지 못했다.

### 정의에 반영
- M19 완료 기준은 유지한다. native gate가 통과하지 않으면 browser replay를 만들지 않는다.

### 다음 실험 후보
- reference/IK action target을 직접 쓰지 말고 stance-stable lower-body manifold를 먼저 찾는다.
- 또는 contact-force/inverse-torque penalty를 PPO reward에 넣어 visible-depth residual policy를 다시 학습한다.
