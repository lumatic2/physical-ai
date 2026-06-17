# 53-g1-contact-envelope-curriculum — contact envelope residual curriculum gate

## 1. 가설 (Hypothesis)

exp52는 contact-aware controller가 contact 1.00/slip 0.014m/return을 지키는 stable corridor를 만들지만 depth가 2.64cm에 머문다는 것을 보였다. pelvis-height/phase residual만 허용하는 curriculum을 2.5cm부터 확장하면, 전신 action을 직접 학습하기 전에 M19 visible depth로 가는 실패 경계를 더 정확히 찾을 수 있다.

근거:
- Residual RL은 fixed controller 위에 task-specific residual을 더해 안전성과 sample efficiency를 높이는 접근이다. https://www.emergentmind.com/topics/residual-reinforcement-learning-rl (accessed 2026-06-18)
- Multi-Gait Learning for Humanoid Robots는 squat depth를 curriculum으로 점진 증가시키는 구성을 사용한다. https://arxiv.org/html/2604.19102v1 (accessed 2026-06-18)
- Residual Policy Learning for Shared Autonomy는 continuous control에서 goal-agnostic constraints를 만족시키도록 residual agent를 학습한다. https://roboticsconference.org/2020/program/papers/72.html (accessed 2026-06-18)
- Agility Robotics는 humanoid whole-body controller를 상위 신호와 하위 안정 실행 계층으로 나누어 설명한다. https://www.agilityrobotics.com/content/training-a-whole-body-control-foundation-model (accessed 2026-06-18)

## 2. 방법 (Method)

### 셋업
- 모델: local MuJoCo Playground G1 env.
- controller: exp52 `native_eval` 재사용.
- curriculum: target drop을 2.5cm -> 4cm -> 6cm -> 8cm로 키우며, 각 단계에서 contact/slip/return/no-fall gate를 본다.

### 측정 metric
- visible pelvis drop, knee/hip pitch delta, fall time, final height/return, both-feet contact ratio, foot slip, support margin.
- M19 PASS는 exp29 visible gate와 native/browser replay가 동시에 통과해야 한다.

## 3. 결과 (Results)

### 데이터
| Level | Verdict | Configured drop | Actual drop | Knee | Hip | Contact | Slip | 비고 |
|---|---|---:|---:|---:|---:|---:|---:|---|
| level-0p025 | STABLE_BUT_SHALLOW | 0.025m | 0.0123m | 0.138 | 0.045 | 1.00 | 0.013m | stance/return pass |
| level-0p040 | STABLE_BUT_SHALLOW | 0.040m | 0.0165m | 0.168 | 0.075 | 1.00 | 0.012m | stance/return pass |
| level-0p060 | STABLE_BUT_SHALLOW | 0.060m | 0.0222m | 0.208 | 0.117 | 1.00 | 0.012m | stable boundary |
| level-0p080 | STANCE_ENVELOPE_BROKEN | 0.080m | 1.5054m | 0.614 | 0.550 | 0.81 | 0.909m | fall at 4.54s |

### 박제 위치
- `verify/envelope-curriculum/result.json`
- `verify/envelope-curriculum/envelope-curriculum-summary.md`
- per-level raw JSON under `verify/envelope-curriculum/*/native-eval.json`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- curriculum target을 6cm까지 올려도 contact-aware controller가 실제 pelvis drop을 2.2cm로 제한한다. stance는 좋지만 visible depth로 가지 않는다.
- 8cm level에서는 pose leverage가 나오지만, contact ratio 0.81, slip 0.909m, fall 4.54s로 stance envelope가 깨진다.
- 따라서 다음 병목은 policy action dimensionality만이 아니라 actuator/torque/CoM authority다. 발을 지키는 envelope 안에서는 motor target이 높이를 충분히 낮추지 못하고, visible target으로 밀면 support가 깨진다.

### 가설은 통과했나?
- [ ] PASS — residual curriculum이 8cm visible gate까지 안정적으로 확장된다.
- [x] FAIL — stable boundary는 actual 2.2cm이며 8cm level은 stance cliff로 실패한다.

### 정의에 반영
- M19는 여전히 native visible gate 전에는 browser replay로 넘어가지 않는다.

### 다음 실험 후보
- contact-aware envelope 안에서 actuator authority를 높이는 torque/PD gain or inverse-dynamics assisted target을 먼저 probe한다.
- 또는 CoM/ZMP target을 explicit하게 넣어 height command가 support polygon 안에서 내려가도록 만든다.
