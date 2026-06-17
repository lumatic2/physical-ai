# 40-g1-reference-base-finetune — G1 reference-base action finetune

## 1. 가설 (Hypothesis)

exp39에서 post-hoc reference-offset action은 direct mode에서는 collapse, ramp mode에서는 micro-dip으로 갈렸다. 원인이 "이미 default-offset에서 학습된 policy를 사후 재해석"한 데 있다면, training env의 motor target 자체를 `moving_reference_pose + residual_action`으로 바꿔 fine-tune할 때 visible squat depth와 balance가 동시에 개선된다.

## 2. 방법 (Method)

### 셋업
- 모델: local MuJoCo Playground G1 runtime (`C:\tmp\e34`).
- Source policy: exp22 depth-finetune policy if present, else exp21 stabilizer policy.
- Env: exp38 support-aware reward + reference-base motor target override.
- 하네스: learning experiment 4-section README + raw evidence in `verify/`.

### 근거
- MuJoCo Playground joystick task는 absolute joint position target을 default offset으로 둔다. URL: https://arxiv.org/html/2502.08844v1 (accessed 2026-06-18)
- Humanoid motion tracking/residual policy 계열은 motion/reference prior와 task residual을 함께 학습시키는 방향이 일반적이다. URLs: https://arxiv.org/html/2506.08840v1, https://resmimic.github.io/file/ResMimic_paper.pdf (accessed 2026-06-18)
- Whole-body squat/transition은 CoM/support/momentum 안정성이 같이 닫혀야 한다. URLs: https://arxiv.org/html/2502.17219v1, https://pmc.ncbi.nlm.nih.gov/articles/PMC11048354/ (accessed 2026-06-18)

### 시나리오
- `smoke`: reference-base env compatibility, zero-action rollout, source policy native eval.
- `train`: short PPO restore fine-tune with reference gain ramp.
- `native`: visible squat gate 재평가.

### 측정 metric
- `visible_drop >= 0.08m`
- `fell_at is None`
- `hold_duration_at_or_below_stage >= 0.5s`
- `final_height >= 0.74m`
- `foot_contact_ratio >= 0.90`
- `foot_slip_distance <= 0.15m`
- `max_joint_limit_violation <= 0.05`

## 3. 결과 (Results)

### 데이터
| Run | Verdict | Timesteps | Drop | Fell at | Contact | Slip | 비고 |
|-----|---------|----------:|------|---------|---------|------|------|
| source-gain-0p35 | DEPTH_PENDING | 0 | 0.0049m | never | 1.00 | 0.027m | reference-base baseline 안정, visible depth 미달 |
| finetune-gain-0p35 | DEPTH_PENDING | 20000 | 0.0056m | never | 1.00 | 0.026m | reward 139.92 -> 141.79, depth는 micro-dip 유지 |
| source-gain-0p70 | DEPTH_PENDING | 0 | 0.0057m | never | 1.00 | 0.027m | gain을 키워도 기존 policy residual은 얕게 유지 |

### 박제 위치
- `verify/stage-0p74-gain-0p35-resid-1p00/result.json`
- `verify/stage-0p74-gain-0p35-resid-1p00/train/rewards.txt`
- `verify/stage-0p74-gain-0p70-resid-1p00/result.json`
- `verify/*/reference-base-summary.md`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- Training env의 motor target을 `moving_reference_pose + residual_action`으로 바꿔도, 기존 stabilizer prior는 20k fine-tune 안에서 visible depth로 이동하지 않았다.
- reward는 `139.92 -> 141.79`로 상승했지만 visible drop은 `0.49cm -> 0.56cm`에 그쳤다. 이는 exp38과 같은 "reward improves, standing attractor remains" 패턴이다.
- reference gain을 `0.35 -> 0.70`으로 키운 source baseline도 fall 없이 안정적이지만 drop은 `0.57cm` 수준이다. 따라서 reference-base action origin만으로는 M19 visible squat gate를 닫기 어렵다.
- 다음 병목은 action origin보다 lower-body operational objective와 balance constraint의 동시 만족이다. foot-fixed IK, CoM/support margin, vertical momentum을 하나의 controller/training target으로 묶어야 한다.

### 가설은 통과했나?
- [ ] PASS
- [x] FAIL

### 정의에 반영
- M19 ROADMAP 상태에 반영한다. 다음 시도는 reward/action-base 조정보다 torque-level 또는 operational-space WBC prototype으로 좁힌다.

### 다음 실험 후보
- exp36 foot-fixed IK target을 operational-space controller objective로 재사용한다.
- CoM support margin과 vertical velocity를 hard guard가 아니라 optimization cost로 넣는다.
- native gate가 먼저 통과할 때만 browser replay를 만든다.
