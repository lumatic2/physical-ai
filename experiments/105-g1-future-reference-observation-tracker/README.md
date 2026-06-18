# 105-g1-future-reference-observation-tracker — G1 future-reference observation tracker

> `experiments/105-g1-future-reference-observation-tracker/README.md` — 현재 reference만 보던 exp103 계열 command를 가까운 미래 reference까지 보는 tracker로 바꿔 M19 visible squat gate를 다시 검증한다.

## 1. 가설 (Hypothesis)

Exp103의 knee gap은 거의 닫혔지만 contact/slip이 무너졌다. 정책이 현재 목표만 보고 뒤늦게 큰 residual을 내는 것이 원인이라면, 같은 관측 크기 안에 future reference fraction을 넣고 anticipatory action reward를 주면 stance breach 전에 더 부드럽게 squat trajectory를 따라갈 수 있다.

## 2. 방법 (Method)

### 셋업
- 모델: local MuJoCo G1 + `FutureReferenceCommandSquat`.
- 초기 checkpoint: `experiments/103-g1-explicit-reference-command-tracker/verify/target-0p090-slip-0p08/train/params.pkl`.
- 하네스 구성: obs shape는 유지하고 command 의미를 `[current_fraction, future_fraction, return_phase]`로 바꿨다.
- 학습: restored PPO `20000` steps, lookahead `0.45s`, anticipatory action mix `0.45`.

### 웹 근거
- UniTracker는 future-aware trajectory/reconstruction style의 humanoid tracking이 단일 현재 pose 추적보다 일반화에 유리하다는 방향을 제시한다. 접근일: 2026-06-18. https://arxiv.org/html/2507.07356v2
- GMT 계열 motion tracking work는 humanoid policy가 reference motion context를 조건으로 받아야 high-dynamic motion을 안정적으로 추적할 수 있음을 보여준다. 접근일: 2026-06-18. https://arxiv.org/html/2506.14770v1
- Disney Research의 strict contact force constrained humanoid tracking은 floating-base humanoid tracking에서 contact force/friction constraint가 핵심 제약임을 강조한다. 접근일: 2026-06-18. https://la.disneyresearch.com/publication/human-motion-tracking-control-with-strict-contact-force-constraints-for-floating-base-humanoid-robots/
- Unitree G1 공식 스펙은 knee/hip range와 knee torque가 visible squat pose 자체를 배제하지 않음을 보여준다. 접근일: 2026-06-18. https://www.unitree.com/g1/

### 시나리오
- Compatibility smoke: exp103 checkpoint와 새 env의 obs/action/network shape를 확인한다.
- Rollout smoke: zero action으로 command/future metric이 움직이는지 확인한다.
- Restored PPO finetune: future-reference command semantics에 맞춰 짧게 재학습한다.
- Native gate: exp29 visible gate를 같은 native rollout evaluator로 판정한다.

### 측정 metric
- visible gate: pelvis drop >= 8cm, knee delta >= 0.60rad, hip delta >= 0.35rad.
- stability gate: no fall, final stand return, both-feet contact ratio >= 0.90, foot slip <= 0.08m, joint violation <= 0.05rad.

## 3. 결과 (Results)

### 데이터
| Run | Verdict | Timesteps | Drop | Knee | Hip | Contact | Slip | Final h | Fall |
|-----|---------|---:|---:|---:|---:|---:|---:|---:|---|
| future-reference | DEPTH_PENDING_7CM | 20000 | 0.0283m | 0.549rad | 0.355rad | 0.48 | 3.089m | 0.7308m | never |

Verdict: `DEPTH_PENDING_7CM`.

### 박제 위치
- `verify/result.json`
- `verify/native-eval.json`
- `verify/future-reference-summary.md`
- `verify/train/params.pkl`
- `verify/train/rewards.txt`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- Future-reference command가 exp103의 delayed action/contact failure를 줄이는지 native gate로 직접 확인했다.
- 결과는 drop `0.0283m`, knee `0.549rad`, hip `0.355rad`, contact `0.48`, slip `3.089m`이다.
- Native gate가 PASS하지 않으면 browser replay는 아직 M19 evidence가 아니다.

### 가설은 통과했나?
- [ ] PASS — native exp29 visible gate를 통과했다.
- [x] FAIL — future-reference observation만으로 native exp29 visible gate를 닫지 못했다.

### 정의에 반영
- M19는 native+browser replay가 둘 다 통과해야만 닫힌다.
