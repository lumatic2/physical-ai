# 45-g1-stance-stable-manifold — G1 stance-stable lower-body target search

## 1. 가설 (Hypothesis)

exp44가 visible-depth에서 fall한 이유가 IK target 자체가 stance-stable manifold 밖에 있기 때문이라면, foot-fixed IK에 CoM/support-center residual을 추가해 더 깊지만 정적으로 안정적인 lower-body target을 찾을 수 있고 native rollout의 no-fall depth도 늘어난다.

## 2. 방법 (Method)

### 셋업
- 모델: local MuJoCo G1, exp36 foot-fixed IK, exp37 support polygon metric, exp42 contact/inverse diagnostics.
- 데이터: exp44 QP-lite sweep의 shallow/fall trade-off, exp43 public/static squat feasibility.
- 하네스 구성: learning experiment 1개. `run_stance_manifold.py --sweep` 결과를 `verify/`에 박제한다.

### 외부 근거
- HuB는 Unitree G1 extreme-balance task에서 CoM projection을 support polygon 안에 두는 reward와 foot contact mismatch penalty를 사용한다. URL: https://arxiv.org/html/2505.07294v2 (accessed 2026-06-18)
- humanoid balance에서는 CoM/ZMP 또는 CoP가 support polygon 안에 있어야 안정성이 유지된다는 설명이 반복된다. URL: https://arxiv.org/html/2502.17219v1 (accessed 2026-06-18)
- stable foot contact는 foot support polygon과 friction/contact constraints를 동시에 만족해야 한다. URL: https://www.mdpi.com/2072-666X/13/9/1458 (accessed 2026-06-18)

### 시나리오
- V0: static target search. pelvis drop, foot-fixed error, CoM center error, support margin, knee/hip visible pose gate를 측정한다.
- V1: native tracking. stance target을 stabilizer policy + blend로 추적해 visible drop, fall, contact, foot slip, support margin을 평가한다.
- V2: M19 gate audit. native visible gate가 통과하지 않으면 browser replay는 만들지 않는다.

### 측정 metric
- Static: max foot error `<=0.002m`, support margin `>=0`, visible pose gate.
- Native: visible drop `>=0.08m`, no fall, final height `>=0.74m`, contact ratio `>=0.90`, foot slip `<=0.15m`, joint violation `<=0.05`.

## 3. 결과 (Results)

### 데이터
| Run | Static pose | Native verdict | Drop | Fell at | 비고 |
|-----|-------------|----------------|-----:|--------:|------|
| drop-0p08-com4-posture1 | PENDING | FAIL_FALL | 1.5146m | 3.52s | knee/hip visible pose gate 미달, support min -0.6166m |
| drop-0p12-com4-posture1 | PASS | FAIL_FALL | 1.5134m | 3.16s | static support margin 0.0589m, native slip 0.721m |
| drop-0p12-com8-posture0p6 | PASS | FAIL_FALL | 1.5151m | 3.38s | static support margin 0.0703m, native slip 0.731m |
| drop-0p16-com8-posture0p6 | PASS | FAIL_FALL | 1.5049m | 3.18s | static support margin 0.0640m, native slip 0.695m |
| drop-0p12-com12-posture0p3 | PASS | FAIL_FALL | 1.5148m | 3.72s | best static support margin 0.0755m, native slip 0.719m |

### 박제 위치
- `verify/stance-manifold-summary.md`
- `verify/attempts/*/stance-native-eval.json`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- CoM/support-center residual은 static target search에는 효과가 있었다. 0.12m/0.16m variants 4개는 foot error 0.7mm 이하, positive support margin, exp29 visible pose gate를 동시에 만족했다.
- 하지만 static support margin은 native stability로 이어지지 않았다. 모든 native tracking attempt가 visible-depth 진입 후 support margin 음수, LR force imbalance spike, large slip으로 collapse했다.
- exp43/45를 합치면 "G1 geometry로 visible squat pose는 가능"하지만 "position/blend controller가 그 manifold를 동역학적으로 따라갈 수 있음"은 거짓이다. stance-aware target search만으로는 M19를 닫지 못한다.

### 가설은 통과했나?
- [ ] PASS — native visible squat gate까지 통과
- [x] FAIL — static manifold는 찾았지만 native visible squat gate는 전부 fall로 실패했다.

### 정의에 반영
- M19 완료 기준은 유지한다. native gate가 통과하지 않으면 browser replay를 만들지 않는다.

### 다음 실험 후보
- contact-force/inverse-torque reward를 PPO 안에 넣는 residual 학습으로 이동한다. exp42/45 지표상 collapse는 support breach와 force/torque spike로 분리되므로, 다음 실험은 target search보다 policy가 이 신호를 피하도록 학습시키는 쪽이 맞다.
