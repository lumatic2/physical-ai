# 56-g1-com-aware-qplite-selector — CoM feedback plus QP-lite selection

> `experiments/56-g1-com-aware-qplite-selector/README.md` — 실험은 가설/방법/결과/통찰 4섹션.

## 1. 가설 (Hypothesis)

exp55의 online CoM feedback은 no-fall depth를 4.73cm까지 늘렸지만, 6cm 이상 schedule에서 delayed support collapse가 났다. 그렇다면 exp44의 one-step QP-lite selector에 CoM feedback scale까지 후보로 넣고, height/support/ZMP/contact force/inverse torque cost를 같이 보면 delayed collapse를 줄이면서 8cm visible gate에 가까워질 수 있다.

근거:
- Whole-body MPC/WBC는 CoM trajectory, contact forces, joint constraints를 함께 최적화하는 구조로 설명된다. URL: https://arxiv.org/html/2506.14278v1, access date: 2026-06-18.
- MuJoCo inverse dynamics는 trajectory/control optimization에서 applied/contact forces를 objective로 쓸 수 있음을 문서화한다. URL: https://mujoco.readthedocs.io/en/stable/computation/index.html, access date: 2026-06-18.
- MuJoCo 기반 whole-body MPC는 whole-body dynamics와 collision/contact reasoning을 forward model로 쓰는 real-time MPC 방향을 제시한다. URL: https://arxiv.org/html/2503.04613v2, access date: 2026-06-18.

## 2. 방법 (Method)

### 셋업
- 모델: local G1 MuJoCo model through exp28/36/37/42/44/55 modules.
- 데이터: exp46 stabilizer policy params, exp36 foot-fixed IK target, exp37 support polygon, exp42 contact wrench/inverse dynamics, exp55 CoM feedback.
- 하네스 구성: learning experiment. Raw evidence는 `verify/com-qplite-selector/`에 저장.

### 시나리오
- 매 control step에서 blend 후보와 CoM feedback scale 후보를 만든다.
- 각 후보 target을 MuJoCo one-step lookahead로 굴리고 cost를 계산한다.
- Cost terms: pelvis height target, support margin, approximate ZMP margin, contact loss, foot slip, LR normal force imbalance, total normal force, inverse torque, inverse-actuator gap, upright, blend jump, feedback magnitude.
- M19 completion gate는 기존 exp29 visible/native/browser 기준을 유지한다.

### 측정 metric
- visible pelvis drop, knee/hip pitch delta, fall time, final height/return, both-feet contact ratio, foot slip, joint-limit violation.
- support/ZMP margin, selected blend, selected feedback scale, contact normal force, lower inverse torque.

## 3. 결과 (Results)

### 데이터

| Run | Verdict | Drop | Knee | Hip | Contact | Slip | CoM min | ZMP min | Fell | 비고 |
|-----|---------|---:|---:|---:|---:|---:|---:|---:|---|------|
| balanced-0p08 | FAIL_FALL | 1.5154m | 0.419 | 0.445 | 0.93 | 0.801m | -0.6163m | -0.6295m | 3.66s | delayed collapse |
| feedback-fixed-0p08 | FAIL_FALL | 1.5199m | 0.520 | 0.317 | 0.93 | 0.853m | -0.5767m | -0.5839m | 3.94s | feedback만 고정해도 collapse |
| depth-0p08 | FAIL_FALL | 1.5141m | 0.400 | 0.463 | 0.96 | 0.850m | -0.6077m | -0.6306m | 3.16s | height-biased fall |
| strict-0p10 | DEPTH_PENDING | 0.0332m | 0.280 | 0.200 | 1.00 | 0.019m | 0.0236m | -0.0166m | never | best no-fall but shallow |
| depth-0p10 | FAIL_FALL | 1.5180m | 0.460 | 0.492 | 0.98 | 0.764m | -0.6140m | -0.6375m | 3.34s | depth-biased fall |
| depth-0p12 | FAIL_FALL | 1.5178m | 0.632 | 0.550 | 0.98 | 0.846m | -0.6120m | -0.6425m | 3.34s | pose leverage but fall |

### 박제 위치
- `verify/com-qplite-selector/result.json`
- `verify/com-qplite-selector/com-qplite-summary.md`
- `verify/com-qplite-selector/*/native-eval.json`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- One-step selector는 delayed collapse를 충분히 예측하지 못했다. depth-biased 후보는 현재 step cost를 낮게 보고 깊게 밀지만 3.16~3.94초에 support/ZMP margin이 크게 음수로 간다.
- Strict cost는 안정적이지만 3.32cm shallow다. exp55의 4.73cm보다 나빠서, short-horizon selector가 단순히 더 좋은 상위 controller가 아니다.
- exp55 best는 CoM feedback뿐 아니라 contact-aware health/adaptive blend schedule이 같이 만든 안정성이다. 다음은 one-step selector보다 multi-step rollout, model predictive schedule, 또는 학습 policy에 CoM/contact-force terms를 넣는 방향이 맞다.

### 가설은 통과했나?
- [ ] PASS
- [x] FAIL — combined selector는 M19 native gate를 닫지 못했고, best no-fall depth도 exp55보다 낮았다.

### 정의에 반영
- M19는 계속 open. 다음 실험은 one-step selector 반복이 아니라 multi-step horizon 또는 policy fine-tuning 쪽으로 넘어간다.

### 다음 실험 후보
- exp55 CoM-feedback controller를 teacher로 삼아 command-conditioned residual policy를 짧게 fine-tune한다.
- 또는 selector lookahead를 1 step에서 0.4~0.8s multi-step rollout으로 늘려 delayed support collapse를 cost에 반영한다.
