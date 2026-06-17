# 62-g1-actuator-contact-wbc-probe — Actuator-space contact WBC probe

## 1. 가설 (Hypothesis)

exp61의 한 스텝 position-target selector가 실패한 이유는 실제 dynamics input을 바꾸지 못했기 때문이다. MuJoCo `qfrc_applied`에 lower-body joint PD torque와 stance-foot Jacobian transpose force를 넣으면, stance foot constraint를 더 직접 닫아 8cm visible squat 안정 corridor를 넓힐 수 있다.

MuJoCo 문서는 applied force가 `qfrc_passive + qfrc_actuator + qfrc_applied`로 구성되며, inverse dynamics가 position/velocity/acceleration에서 applied/contact force를 회복하는 데 쓰인다고 설명한다. 접근일: 2026-06-18. <https://mujoco.readthedocs.io/en/stable/computation/index.html>

IHWBC 계열 humanoid WBC는 원하는 task acceleration과 reaction wrench를 함께 풀고 joint torque command를 계산한다. 접근일: 2026-06-18. <https://www.frontiersin.org/journals/robotics-and-ai/articles/10.3389/frobt.2021.712239/full>

position-controlled humanoid에서도 contact force를 직접 만들기 어렵다는 문제가 별도로 연구되어, SEIKO처럼 force/admittance를 position command에 우회적으로 반영하는 접근이 제안됐다. 접근일: 2026-06-18. <https://arxiv.org/html/2312.16465v3>

Unitree G1을 포함한 FALCON 연구도 force curriculum을 joint torque feasibility와 함께 다룬다. 접근일: 2026-06-18. <https://arxiv.org/html/2505.06776v1>

## 2. 방법 (Method)

### 셋업
- 모델: local Unitree G1 MuJoCo policy sandbox.
- 시작점: exp60 `safe_combo` residual, exp42 contact/inverse-force diagnostics.
- 실행: `run_actuator_contact_wbc_probe.py`.
- raw evidence: `verify/actuator-contact-wbc/`.

### controller
- 기존 position target은 policy target, IK target, CoM feedback, `safe_combo` residual로 만든다.
- `data.qfrc_applied`에 두 보조항을 더한다.
- lower-body joint PD torque: selected lower joint qpos error를 generalized torque로 직접 보조한다.
- stance-foot force: foot site displacement/velocity를 Jacobian transpose로 generalized force에 투영한다.
- pass gate는 M19 native gate 그대로 유지한다: pelvis drop >=8cm, knee >=0.60rad, hip >=0.35rad, no-fall, return, contact, slip, joint limit.

### variants
- torque-only: stance-foot force 없이 lower-body torque만 추가한다.
- foot-light / stance-torque: foot Jacobian stance force를 약하게/중간으로 추가한다.
- balanced / pose / slow: 더 큰 torque와 depth를 시도한다.

## 3. 결과 (Results)

### 데이터
| Run | Verdict | Drop | Knee | Hip | Contact | Slip | Support/ZMP min | 비고 |
|---|---|---:|---:|---:|---:|---:|---:|---|
| torque-only-0p08-t20 | DEPTH_PENDING | 0.0580m | 0.419 | 0.184 | 1.00 | 0.023m | 0.0225 / -0.0281m | best no-fall, exp60보다 +0.07cm |
| torque-only-0p08-r0p07-t20 | FAIL_FALL | 1.5091m | 0.564 | 0.349 | 0.92 | 0.930m | -0.5702 / -0.5757m | residual 0.07부터 collapse |
| torque-only-0p08-r0p08-t20 | FAIL_FALL | 1.5080m | 0.569 | 0.362 | 0.87 | 0.938m | -0.5710 / -0.5707m | pose는 가까우나 fall |
| torque-only-0p08-t40 | DEPTH_PENDING | 0.0541m | 0.397 | 0.260 | 0.99 | 0.110m | -0.0575 / -0.0308m | torque를 키우면 stance margin 악화 |
| foot-light-0p08-t30 | DEPTH_PENDING | 0.0557m | 0.406 | 0.196 | 0.99 | 0.031m | 0.0277 / -0.0284m | foot force는 depth 개선 없음 |
| stance-torque-0p08-t30 | DEPTH_PENDING | 0.0512m | 0.384 | 0.149 | 1.00 | 0.036m | 0.0345 / -0.0227m | stance force는 더 보수적 |
| balanced/pose/slow | FAIL_FALL | 1.5078~1.5179m | 0.566~0.583 | 0.351~0.353 | 0.83~0.87 | 0.407~0.444m | about -0.55 / -0.58m | visible pose 근처에서 collapse |

### 박제 위치
- Summary: `verify/actuator-contact-wbc/actuator-contact-wbc-summary.md`
- Aggregate JSON: `verify/actuator-contact-wbc/result.json`
- Per-run JSON: `verify/actuator-contact-wbc/*/native-eval.json`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- lower-body generalized torque는 exp60의 5.73cm no-fall 경계를 5.80cm로 아주 조금 넓혔다.
- 하지만 residual을 0.07로 올리는 순간 곧바로 support/ZMP collapse가 재현된다. knee/hip pose는 visible gate 근처까지 가지만 stance가 버티지 못한다.
- foot Jacobian transpose stance force는 기대와 달리 안정 corridor를 넓히지 못했다. qfrc가 커질수록 ZMP/support가 악화되어 “발을 붙잡는 힘”이 실제 contact wrench distribution을 잘 닫지 못했다.
- M19의 다음 병목은 외부 qfrc 보조가 아니라 contact wrench distribution/CoM trajectory 자체를 함께 최적화하는 planner 또는 torque-feasible reference trajectory다.

### 가설은 통과했나?
- [ ] PASS
- [x] FAIL — actuator-space 보조는 stable drop을 5.80cm까지 조금 늘렸지만 8cm visible squat gate에는 실패했다.

### 정의에 반영
- ROADMAP M19에 exp62를 추가하고, 다음 실험은 “더 센 torque”가 아니라 contact-wrench/CoM trajectory co-design으로 좁힌다.

### 다음 실험 후보
- exp63: TP-MPC식으로 CoM height trajectory를 먼저 제한하고, knee/hip pose target은 해당 CoM/ZMP feasible envelope 안에서만 생성한다.
