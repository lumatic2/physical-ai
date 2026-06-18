# 104-g1-contact-aware-reference-action-wrapper — G1 접촉 인지 reference action wrapper

> `experiments/104-g1-contact-aware-reference-action-wrapper/README.md` — exp103 explicit-reference 정책을 재학습 없이 native action wrapper로 감싸 접촉/슬립 병목을 분리한다.

## 1. 가설 (Hypothesis)

G1은 관절 범위와 무릎 토크 스펙상 보이는 squat pose 자체는 가능한 편이지만, exp103 실패는 pose command 부족보다 stance contact/slip 제약을 정책 입력과 제어 입력 사이에서 즉시 보정하지 못한 것이 원인일 수 있다.

## 2. 방법 (Method)

### 셋업
- 모델: local MuJoCo G1 + exp103 explicit-reference command PPO checkpoint.
- 데이터: `experiments/103-g1-explicit-reference-command-tracker/verify/target-0p090-slip-0p08/train/params.pkl`.
- 하네스 구성: exp80 native visible gate evaluator를 재사용하고, policy action을 `ctrl`로 넣기 직전에 support margin, both-feet contact, foot slip으로 scale/damp/return wrapper를 적용했다.

### 웹 근거
- Unitree 공식 G1 page는 knee range `0~165°`, hip pitch `±154°`, knee torque `90/120 N.m`를 제시한다. 접근일: 2026-06-18. https://www.unitree.com/g1/
- Disney Research의 humanoid motion tracking paper는 humanoid reference imitation의 핵심 난점을 joint torque만이 아니라 contact force와 friction constraint로 설명한다. 접근일: 2026-06-18. https://la.disneyresearch.com/publication/human-motion-tracking-control-with-strict-contact-force-constraints-for-floating-base-humanoid-robots/
- 최근 heavy-limb humanoid WBC paper는 Unitree G1류 humanoid에서 limb mass/base coupling이 balance를 흔들고, reference motion/contact force를 같이 계획해야 한다고 정리한다. 접근일: 2026-06-18. https://arxiv.org/html/2506.14278v1
- Squat-specific humanoid paper도 squat을 whole-body coordination + WBC/MPC 문제로 다룬다. 접근일: 2026-06-18. https://pmc.ncbi.nlm.nih.gov/articles/PMC11769464/

### 시나리오
- `direct-exp103`: exp103 checkpoint를 그대로 재평가한다.
- `support-slip-scale`: slip/support/contact breach가 보이면 residual action을 줄인다.
- `ankle-damped-support-slip`: 발목 residual을 같이 줄여 foot slip을 낮춘다.
- `early-conservative-scale`: early descent부터 conservative scale을 건다.
- `return-on-contact-breach`: contact/slip breach 시 default standing pose 쪽으로 돌린다.

### 측정 metric
- exp29 visible gate: pelvis drop >= 8cm, knee delta >= 0.60rad, hip delta >= 0.35rad.
- stability gate: no fall, final stand return, both-feet contact ratio >= 0.90, foot slip <= 0.08m, joint violation <= 0.05rad.

## 3. 결과 (Results)

### 데이터
| Run | Verdict | Drop | Knee | Hip | Contact | Slip | Return | Fall |
|-----|---------|---:|---:|---:|---:|---:|---|---|
| direct-exp103 | DEPTH_PENDING_7CM | 0.0572m | 0.583 | 0.492 | 0.39 | 3.090m | True | never |
| support-slip-scale | FAIL_FALL | 1.5358m | 0.609 | 0.242 | 0.91 | 0.985m | False | 2.08s |
| ankle-damped-support-slip | FAIL_FALL | 1.5363m | 0.601 | 0.206 | 0.91 | 0.995m | False | 1.28s |
| early-conservative-scale | FAIL_FALL | 1.5315m | 0.610 | 0.190 | 0.91 | 1.032m | False | 1.22s |
| return-on-contact-breach | FAIL_FALL | 1.5349m | 0.586 | 0.195 | 0.93 | 1.000m | False | 1.26s |

Best variant: `direct-exp103` -> `DEPTH_PENDING_7CM`.

### 박제 위치
- `verify/result.json`
- `verify/contact-aware-wrapper-summary.md`
- `verify/direct-exp103.json`
- `verify/support-slip-scale.json`
- `verify/ankle-damped-support-slip.json`
- `verify/early-conservative-scale.json`
- `verify/return-on-contact-breach.json`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- G1 squat feasibility 자체는 관절/토크 스펙상 부정되지 않는다. 문제는 현재 local policy/control stack이 contact force/friction constraint를 만족시키며 reference pose를 추적하지 못하는 것이다.
- Contact-aware action wrapper는 exp103의 3m급 slip 폭주를 줄일 수 있는지 보는 빠른 sanity gate지만, wrapper만으로 exp29 전체 gate를 닫지 못하면 다음은 wrapper search가 아니라 future-reference tracker 또는 WBC/contact-force planner를 policy loop에 넣어야 한다.
- 이번 best 결과는 drop `0.0572m`, knee `0.583rad`, hip `0.492rad`, contact `0.39`, slip `3.090m`이다.

### 가설은 통과했나?
- [ ] PASS
- [x] FAIL — action wrapper만으로 native exp29 visible gate를 닫지 못했다.

### 정의에 반영
- M19는 계속 open이다. native gate가 실패했으므로 browser replay는 시도하지 않는다.

### 다음 실험 후보
- Future-reference observation을 넣은 tracker env로 exp103을 확장하거나, contact force/friction constraints를 명시적으로 푸는 WBC/MPC planner를 policy action 앞단에 둔다.
