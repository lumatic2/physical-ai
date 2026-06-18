# 100-g1-upstream-motor-xml-squat-policy-probe — upstream motor XML squat policy probe

> `experiments/100-g1-upstream-motor-xml-squat-policy-probe/README.md` — G1이 스쿼트 가능한 로봇인지 공개 근거로 확인하고, local position-actuator scene 대신 public motor-actuated G1 XML에서 G1 Moves ONNX 정책을 native rollout한다.

## 1. 가설 (Hypothesis)

Unitree G1 자체는 visible/deep squat에 필요한 관절 범위와 공개 연구 근거가 있다. 따라서 exp99 실패가 local position-actuator XML mismatch 때문이라면, public motor-actuated G1 XML 후보에서 같은 G1 Moves policy가 최소한 더 안정적인 native squat rollout을 만들 수 있다.

## 2. 방법 (Method)

### 셋업
- 모델: public G1 29DoF motor-actuated XML 후보 2개.
- 정책/데이터: G1 Moves `J_Dance4_Broadway_policy.onnx` + `J_Dance4_Broadway.npz`.
- 실행: upstream-style pelvis anchor, 6D orientation flatten, zero default pose, PD torque equation.
- Mesh: local G1 STL assets를 transient temp workspace의 `meshes/`에 복사해 XML compile만 수행했다. XML/ONNX/NPZ는 레포에 vendoring하지 않고 hash만 `verify/`에 남겼다.

### 웹 근거
- Unitree 공식 G1 spec은 knee joint range `0~165°`, hip pitch `P±154°`, knee maximum torque `90N.m`/`120N.m`를 제시한다. https://www.unitree.com/g1/ (accessed 2026-06-18)
- IEEE Robots Guide는 G1의 deep squat/flexibility 사진 설명과 90 N.m knee actuator spec을 싣고 있다. https://robotsguide.com/robots/unitree-g1 (accessed 2026-06-18)
- HuB project는 Unitree G1에서 `Deep Squat`을 비교 task로 제시하고, G1에서 extreme quasi-static balance tasks를 검증했다고 밝힌다. https://hub-robot.github.io/ (accessed 2026-06-18)
- HuB arXiv는 reference refinement + balance-aware policy + sim-to-real robustness가 필요하다고 설명한다. https://arxiv.org/html/2505.07294v1 (accessed 2026-06-18)

### 시나리오
- `unitree_ros_g1_29dof`: Unitree ROS raw `g1_29dof_rev_1_0.xml`.
- `roboJudo_g1_29dof`: RoboJuDo release `g1_29dof_rev_1_0.xml`.

### 측정 metric
- Compile success, actuator type/count, sensor count.
- Native rollout: fall time, pelvis drop, knee/hip pitch delta, foot-body XY slip, action range, obs absolute max.
- M19 gate: native visible pass가 없으면 browser replay는 실행하지 않는다.

## 3. 결과 (Results)

### 데이터
| Candidate | Compile | Verdict | Drop | Knee | Hip | Fell | Action range | Obs max | Sensors |
|---|---|---|---:|---:|---:|---|---|---:|---:|
| unitree_ros_g1_29dof | PASS | FAIL_FALL | 728.600m | 43462.198 | 42483.788 | 0.08s | -2508445.25..2239065.00 | 47303700.00 | 4 |
| roboJudo_g1_29dof | PASS | FAIL_FALL | 0.722m | 3.173 | 6.660 | 0.14s | -166.07..194.67 | 3278.66 | 4 |

Verdict: `FAIL_VISIBLE_NATIVE`.

### 박제 위치
- Runner: `run_g1_upstream_motor_xml_squat_policy_probe.py`
- Raw result: `verify/g1-upstream-motor-xml-squat-policy-probe/result.json`
- Summary: `verify/g1-upstream-motor-xml-squat-policy-probe/g1-upstream-motor-xml-squat-policy-summary.md`
- Per-candidate evals: `verify/g1-upstream-motor-xml-squat-policy-probe/*/native-eval.json`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- G1 로봇 자체의 squat feasibility는 공개 spec/research 기준으로 부정할 이유가 없다. 관절 범위와 HuB deep-squat task 근거는 M19 목표가 물리적으로 터무니없는 목표가 아님을 지지한다.
- Public motor XML로 바꾸면 local position actuator mismatch 일부는 줄어든다. `roboJudo_g1_29dof`는 exp99의 million-scale action/obs 폭주보다 훨씬 작지만, 그래도 0.14초 fall이다.
- 남은 병목은 “스쿼트 불가능”이 아니라 exact policy training scene parity다. G1 Moves가 기대한 `g1_mode15_square.xml`/sensor/order/default/dynamics 계약이 아직 맞지 않는다.
- Browser replay는 native visible gate가 없어서 계속 보류한다.

### 가설은 통과했나?
- [ ] PASS
- [x] FAIL — public motor XML 후보만으로 G1 Moves policy가 native visible squat을 만들지는 못했다.

### 정의에 반영
- M19의 다음 분기는 scalar controller 재시도가 아니라 exact training-scene parity 확보 또는 공개 HuB식 balance-aware motion tracking route다.

### 다음 실험 후보
- G1 Moves가 실제 사용한 `g1_mode15_square.xml`을 찾거나 재구성해 sensor/order/dynamics parity를 먼저 닫는다.
- HuB 논문 흐름처럼 reference refinement + balance-aware policy로 deep squat 전용 tracker를 학습하는 쪽으로 전환한다.
