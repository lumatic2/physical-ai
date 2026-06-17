# 42-g1-contact-inverse-force-probe — G1 contact and inverse dynamics force probe

## 1. 가설 (Hypothesis)

exp41의 soft WBC proxy가 shallow corridor를 넓혔지만 visible depth를 닫지 못한 이유가 접촉력/역동역학 제약을 직접 보지 않았기 때문이라면, MuJoCo contact wrench와 inverse dynamics torque 신호에서 shallow-stable, soft-stable, collapse rollout이 분리된다.

## 2. 방법 (Method)

### 셋업
- 모델: local MuJoCo Playground G1 runtime (`C:\tmp\e34`).
- 입력: exp36 foot-fixed IK target, exp37 support polygon, exp41 soft-WBC blend variants.
- 하네스: learning experiment 4-section README + raw evidence in `verify/`.

### 근거
- MuJoCo 공식 문서는 contact force를 `mj_contactForce`로 3D force + 3D torque wrench로 변환할 수 있다고 설명한다. URL: https://mujoco.readthedocs.io/en/stable/APIreference/APIfunctions.html (accessed 2026-06-18)
- MuJoCo computation 문서는 inverse dynamics가 positions/velocities/accelerations에서 applied/contact forces 기반 objective를 만들 수 있게 한다고 설명한다. URL: https://mujoco.readthedocs.io/en/stable/computation/index.html (accessed 2026-06-18)
- MuJoCo programming notes는 `mj_inverse`가 `qfrc_inverse`를 쓰며 contact force 해석에 `mj_contactForce`를 쓰라고 설명한다. URL: https://roboti.us/book/programming.html (accessed 2026-06-18)

### 시나리오
- `fixed-0p25`: shallow stable baseline.
- `support-velocity-0p60`: best no-fall soft-WBC corridor.
- `support-velocity-0p80`: visible-collapse boundary.

### 측정 metric
- foot contact normal/tangent wrench summary
- left/right normal force balance
- `qfrc_inverse`, `qfrc_actuator`, `qfrc_inverse_minus_actuator`
- support margin, vertical velocity, slip, fall time

## 3. 결과 (Results)

### 데이터
| Run | Verdict | Drop | Fell at | Normal force max | LR imbalance max | Inv torque max | 비고 |
|-----|---------|------|---------|------------------|------------------|----------------|------|
| fixed-0p25 | DEPTH_PENDING | 0.0225m | never | 455.60 | 0.46 | 1663.40 | shallow stable baseline |
| support-velocity-0p60 | DEPTH_PENDING | 0.0253m | never | 453.99 | 0.34 | 1328.38 | best no-fall corridor, lower imbalance/torque |
| support-velocity-0p80 | FAIL_FALL | 1.5034m | 4.72s | 2747.66 | 1.00 | 6558.33 | collapse boundary, single-foot load spike |

### 박제 위치
- `verify/force-probe-summary.md`
- `verify/attempts/*/force-native-eval.json`
- `verify/attempts/*/result.json`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- MuJoCo `mj_contactForce`와 `mj_inverse` 신호는 M19 실패면을 분리한다. collapse variant는 stable variants보다 max foot normal force가 약 6배 크고, 좌우 normal imbalance가 `1.00`까지 간다.
- best no-fall soft corridor인 `support-velocity-0p60`은 fixed shallow baseline보다 `max_lr_normal_imbalance`가 `0.46 -> 0.34`, `max_lower_inverse_torque`가 `1663 -> 1328`로 낮다. soft WBC proxy가 단지 blend를 줄인 것이 아니라 force balance 쪽으로도 더 좋은 corridor를 만든다.
- collapse boundary `support-velocity-0p80`은 `max_total_foot_normal_force 2747.66`, `max_lower_inverse_torque 6558.33`, `max_inverse_minus_actuator 23227.16`으로 튄다. 다음 QP-lite WBC는 이 세 신호를 penalty/constraint로 직접 써야 한다.
- 단, stable variants의 inverse-actuator gap도 절대값은 크다. 현재 inverse summary는 controller 설계용 relative diagnostic으로 쓰고, absolute torque feasibility는 별도 calibration이 필요하다.

### 가설은 통과했나?
- [x] PASS
- [ ] FAIL

### 정의에 반영
- M19 ROADMAP 상태에 반영한다. 다음 단계는 force-aware QP-lite WBC로 좁힌다.

### 다음 실험 후보
- QP-lite: pelvis height acceleration, foot pose equality, support margin, foot normal force balance, inverse torque penalty를 하나의 solve로 묶는다.
- collapse boundary에서 `lr_normal_imbalance`와 inverse torque spike를 낮추는지 먼저 본다.
- native visible gate가 통과할 때까지 browser replay는 만들지 않는다.
