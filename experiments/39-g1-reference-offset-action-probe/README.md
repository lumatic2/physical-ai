# 39-g1-reference-offset-action-probe — G1 reference-offset action target probe

## 1. 가설 (Hypothesis)

M19가 reward-only finetune에서 standing attractor를 못 깨는 이유가 `default_pose + action` action architecture 때문이라면, 같은 stabilizer policy action을 `reference_pose + residual_action`으로 해석할 때 native rollout에서 squat depth leverage가 커진다.

## 2. 방법 (Method)

### 셋업
- 모델: local MuJoCo Playground G1 runtime (`C:\tmp\e34`).
- 데이터: exp22 stabilizer/depth policy, exp25/28 staged reference target.
- 하네스 구성: learning experiment 4-section README + raw evidence in `verify/`.

### 근거
- MuJoCo Playground G1 joystick policy uses position targets around the default pose, so the policy must actively leave its stabilizing attractor to squat. Source: local installed `mujoco_playground` and exp21-38 native evidence (accessed 2026-06-18).
- Humanoid motion tracking systems commonly track reference joint targets with residual correction rather than relying on a standing-default residual alone. URLs: https://arxiv.org/html/2502.17219v1, https://hub-robot.github.io/ (accessed 2026-06-18)

### 시나리오
- V0: `default-offset`: current architecture, `default_pose + policy_action`.
- V1: `reference-offset`: `reference_pose + residual_scale * policy_action`.
- V2: `reference-ramp`: slowly blend from default pose toward reference pose, then add residual policy action.

### 측정 metric
- `visible_drop >= 0.08m`
- `fell_at is None`
- `foot_contact_ratio >= 0.90`
- `foot_slip_distance <= 0.15m`
- `final_height >= 0.74m`
- support margin and downward velocity diagnostics.

## 3. 결과 (Results)

### 데이터
| Run | Verdict | Drop | Fell at | Contact | Slip | 비고 |
|-----|---------|------|---------|---------|------|------|
| default-stage-0p74 | DEPTH_PENDING | 0.0052m | never | 1.00 | 0.012m | 기존 default-offset standing attractor 재현 |
| ramp-stage-0p74-gain-0p25 | DEPTH_PENDING | 0.0075m | never | 1.00 | 0.012m | ramp 안정, visible depth 미달 |
| ramp-stage-0p74-gain-0p50 | DEPTH_PENDING | 0.0105m | never | 1.00 | 0.012m | ramp 안정, support margin 0.0602m |
| ramp-stage-0p67-gain-0p50 | DEPTH_PENDING | 0.0105m | never | 1.00 | 0.012m | deeper stage도 ramp gain이 얕은 target으로 수렴 |
| ref-stage-0p74-resid-0p25 | FAIL_FALL | 1.5316m | 1.40s | 0.91 | 0.987m | direct reference-offset은 visible leverage 대신 collapse |
| ref-stage-0p67-reference-only | FAIL_FALL | 1.5211m | 1.24s | 0.92 | 0.993m | pure reference target도 collapse |

### 박제 위치
- `verify/reference-offset-summary.md`
- `verify/attempts/*/native-eval.json`
- `verify/attempts/*/result.json`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- Direct `reference_pose + residual_action` 해석은 squat depth leverage를 만든다. 그러나 이는 제어된 squat가 아니라 1.24~1.40초 collapse로 나타났다.
- Reference target을 3초 ramp로 천천히 섞으면 fall/contact/slip은 안정적이지만 drop은 최대 1.05cm로 exp28/38과 같은 micro-dip 영역에 머문다.
- 따라서 M19의 병목은 단순 action target origin만이 아니다. standing stabilizer policy를 사후에 reference-offset으로 재해석하는 방식은 안정성과 visible depth를 동시에 만족하지 못한다.

### 가설은 통과했나?
- [ ] PASS
- [x] FAIL

### 정의에 반영
- M19 ROADMAP 상태에 반영한다. 다음 시도는 이미 학습된 default-offset policy를 사후 재해석하는 것이 아니라, reference-offset action base를 학습 시작부터 넣거나 torque-level/operational-space WBC에서 CoM, support margin, vertical momentum을 닫아야 한다.

### 다음 실험 후보
- Reference-offset action architecture를 env에 정식으로 넣고 stabilizer prior를 fine-tune한다.
- 또는 foot-fixed IK target을 operational-space/WBC cost로 두고 support polygon + vertical momentum constraint를 동시에 최적화한다.
