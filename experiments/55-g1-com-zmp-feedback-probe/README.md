# 55-g1-com-zmp-feedback-probe — online CoM/ZMP feedback for G1 squat

> `experiments/55-g1-com-zmp-feedback-probe/README.md` — 실험은 가설/방법/결과/통찰 4섹션.

## 1. 가설 (Hypothesis)

exp54에서 단순 actuator authority 증폭은 M19 visible squat gate를 닫지 못했다. 그렇다면 다음 병목은 target을 더 세게 추적하는 힘이 아니라, 하강 중 CoM/ZMP projection을 foot support 안에 유지하는 whole-body balance 문제일 수 있다. 온라인 CoM/ZMP recentering이 맞다면, exp52 contact-aware controller보다 안정적인 no-fall depth corridor가 깊어져야 한다.

근거:
- Humanoid squat 연구는 squat motion을 torso/feet/contact-force constraints가 얽힌 whole-body coordination 문제로 보고, TP-MPC와 WBC를 결합한다. URL: https://pmc.ncbi.nlm.nih.gov/articles/PMC11769464/, access date: 2026-06-18.
- Task-based WBC with ZMP regulation은 CoM position과 relative foot pose를 stable motion의 기본 task로 둔다. URL: https://www.lirmm.fr/krut/pdf/2014_galdeano_ssd-0568454426/2014_galdeano_ssd.pdf, access date: 2026-06-18.
- Underactuated Robotics는 CoP/ZMP와 CoM dynamics의 관계를 설명하고, CoP location이 CoM acceleration과 연결된다고 정리한다. URL: https://underactuated.mit.edu/humanoids.html, access date: 2026-06-18.

## 2. 방법 (Method)

### 셋업
- 모델: local G1 MuJoCo model through exp52 `ContactAwareSquat`.
- 데이터: exp52 contact-aware height controller, exp46 stabilizer policy params, exp36 foot-fixed IK target, exp37 support polygon metric.
- 하네스 구성: learning experiment. Raw evidence는 `verify/com-zmp-feedback/`에 저장.

### 시나리오
- Baseline: exp52/53 style 8cm target without feedback.
- CoM feedback: support rectangle center minus current CoM projection을 hip/ankle pitch/roll target에 작은 correction으로 더한다.
- ZMP feedback: approximate LIPM-style `zmp_xy = com_xy - z/g * com_acc_xy`를 support center로 recenter한다.
- Sign sweep: pitch sign A/B와 blend schedule을 비교한다. M19 completion은 기존 visible/native/browser gate를 그대로 유지한다.

### 측정 metric
- visible pelvis drop, knee/hip pitch delta, fall time, final height/return, both-feet contact ratio, foot slip, joint-limit violation.
- support margin and approximate ZMP margin.

## 3. 결과 (Results)

### 데이터

| Run | Verdict | Source | Drop | CoM min | ZMP min | Contact | Slip | Fell | 비고 |
|-----|---------|--------|---:|---:|---:|---:|---:|---|------|
| baseline-no-feedback | FAIL_FALL | com | 1.5072m | -0.5699m | -0.5721m | 0.83 | 0.885m | 4.56s | exp53 stance cliff 재현 |
| com-feedback-a | DEPTH_PENDING | com | 0.0278m | 0.0604m | 0.0525m | 1.00 | 0.015m | never | 안정적이지만 shallow |
| com-feedback-a-blend0p50 | DEPTH_PENDING | com | 0.0473m | 0.0292m | 0.0184m | 1.00 | 0.017m | never | best no-fall |
| com-feedback-a-blend0p60-slow | FAIL_FALL | com | 1.5068m | -0.5718m | -0.5733m | 0.91 | 0.945m | 5.44s | 6cm 이상 시 cliff |
| com-feedback-a-blend0p70-slow | FAIL_FALL | com | 1.4952m | -0.5803m | -0.5799m | 0.91 | 0.938m | 5.34s | deep schedule fail |
| com-feedback-a-blend0p85-slow | FAIL_FALL | com | 1.1582m | -0.5693m | -0.5693m | 0.93 | 0.425m | 5.72s | deep schedule fail |
| com-feedback-b | FAIL_FALL | com | 1.5238m | -0.5950m | -0.5957m | 0.87 | 0.828m | 2.84s | wrong sign |
| zmp-feedback-a | DEPTH_PENDING | zmp | 0.0224m | 0.0664m | 0.0437m | 1.00 | 0.015m | never | stable but shallower |
| zmp-feedback-b | FAIL_FALL | zmp | 1.5231m | -0.5910m | -0.5921m | 0.80 | 0.922m | 3.14s | wrong sign |

### 박제 위치
- `verify/com-zmp-feedback/result.json`
- `verify/com-zmp-feedback/com-zmp-feedback-summary.md`
- `verify/com-zmp-feedback/*/native-eval.json`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- CoM recentering sign A는 실제 개선이다. exp52 stable best가 2.64cm, exp54 authority best no-fall이 1.9cm였는데, exp55는 no-fall/contact 1.00/slip 0.017m로 4.73cm까지 깊어졌다.
- 하지만 M19 visible gate인 8cm에는 아직 못 갔다. 6cm 이상 schedule로 밀면 support/ZMP margin이 다시 크게 음수로 가고 fall한다.
- ZMP approximation은 acceleration noise에 민감해서 이번 heuristic에서는 CoM feedback보다 보수적으로 작동했다.

### 가설은 통과했나?
- [ ] PASS
- [x] PARTIAL — CoM feedback이 안정 corridor를 깊게 만들었지만 native visible gate는 실패했다.

### 정의에 반영
- M19는 계속 open. 다음은 heuristic target offset보다 contact force distribution을 직접 고르는 centroidal/QP-lite selector 또는 짧은-horizon MPC가 맞다.

### 다음 실험 후보
- exp44 QP-lite selector에 CoM feedback target을 결합하고, height objective와 support/ZMP/contact-force objective를 같이 최적화한다.
