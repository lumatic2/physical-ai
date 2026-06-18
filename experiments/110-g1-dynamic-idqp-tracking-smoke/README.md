# 110-g1-dynamic-idqp-tracking-smoke — G1 dynamic ID-QP tracking smoke

> `experiments/110-g1-dynamic-idqp-tracking-smoke/README.md` — exp109에서 static ID-QP plausible로 나온 visible squat target을 실제 6초 native rollout에서 추종해 본다.

## 1. 가설 (Hypothesis)

Exp109는 exp29 visible-min과 9cm full visible pose가 static inverse-dynamics contact QP에서는 plausible하다고 보였다. 같은 target을 dynamic rollout에서 joint PD torque + foot contact-force QP로 추종하면, qfrc wrapper보다 exp29 visible gate에 더 가까워지거나 native/browser gate를 닫을 수 있다.

## 2. 방법 (Method)

### 셋업
- 모델: local MuJoCo G1 + exp67 native evaluator.
- target: exp109 `visible-full-pose` 또는 `exp29-visible-min`.
- controller: 매 control step마다 lower-body joint target을 phase schedule로 만들고, lower-body PD torque와 foot anchoring/contact-force QP를 `qfrc_applied`로 합산했다.
- 판정: exp29 visible gate가 native에서 통과할 때만 browser replay를 시도한다.

### 웹 근거
- MuJoCo inverse dynamics/contact 모델은 contact force가 generalized force로 들어가는 구조를 제공한다. 접근일: 2026-06-18. https://mujoco.readthedocs.io/en/stable/computation/index.html
- Multi-contact force control 문헌은 position-controlled robot에서는 접촉력을 직접 제어하기 어렵고 force/admittance layer가 필요하다고 설명한다. 접근일: 2026-06-18. https://arxiv.org/html/2312.16465v3
- Contact-force constrained humanoid tracking은 floating-base humanoid imitation에서 contact forces와 friction constraints를 함께 계산해야 함을 보인다. 접근일: 2026-06-18. https://la.disneyresearch.com/wp-content/uploads/PROJECT_Humanoids-mocap_IEEE-RAS-ICHR-2013_PAPER1.pdf
- Contact-implicit inverse dynamics trajectory optimization은 접촉을 포함한 실시간 MPC/trajectory optimization 방향을 제시한다. 접근일: 2026-06-18. https://arxiv.org/html/2309.01813v3

## 3. 결과 (Results)

### 데이터
| Run | Verdict | Drop | Knee | Hip | Contact | Slip | Return | Fall |
|---|---|---:|---:|---:|---:|---:|---|---|
| static-full-contact-heavy | FAIL_FALL | 1.5104m | 0.650 | 0.484 | 0.92 | 0.527m | False | 1.48s |
| static-full-joint-heavy | FAIL_FALL | 1.5105m | 0.600 | 0.479 | 0.91 | 0.576m | False | 1.60s |
| static-full-slow-balanced | FAIL_FALL | 1.5096m | 0.602 | 0.482 | 0.94 | 0.589m | False | 1.46s |
| static-min-conservative | FAIL_FALL | 1.5096m | 0.530 | 0.446 | 0.91 | 0.617m | False | 1.42s |
| static-full-very-slow | FAIL_FALL | 1.5104m | 0.573 | 0.398 | 0.93 | 0.650m | False | 1.44s |

Best dynamic ID-QP smoke run: `static-full-contact-heavy` -> `FAIL_FALL`.

### 박제 위치
- `verify/result.json`
- `verify/dynamic-idqp-tracking-smoke-summary.md`
- `verify/<attempt>/native-eval.json`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- 이 실험은 static feasible visible target을 실제 dynamic rollout에 넣은 첫 smoke다.
- Best score run도 `1.48s`에 fall했고, drop `1.5104m`는 controlled squat depth가 아니라 collapse 이후 최저 높이다.
- 전 후보가 1.42~1.60초에 fall했으므로 static feasible pose를 stepwise qfrc/PD로 직접 추종하는 route는 M19 native gate 후보가 아니다.
- 다음은 단일 step qfrc assist가 아니라 horizon-level full ID-QP/MPC 또는 contact-aware policy retrain이다.

### 가설은 통과했나?
- [ ] PASS — native exp29 visible gate를 통과했다.
- [x] FAIL — dynamic ID-QP-style smoke만으로 native exp29 visible gate를 닫지 못했다.

### 정의에 반영
- M19 완료 조건은 그대로 native exp29 visible gate + browser replay다. 본 실험은 static feasibility 이후 dynamic tracking gap을 직접 재는 중간 증거다.
