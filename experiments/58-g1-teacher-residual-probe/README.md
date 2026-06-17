# 58-g1-teacher-residual-probe - exp55 teacher residual capacity probe

> `experiments/58-g1-teacher-residual-probe/README.md` - M19 residual fine-tune 전 native capacity probe. 접근일: 2026-06-18.

## 1. 가설 (Hypothesis)

exp55 CoM-feedback teacher가 4.73cm no-fall corridor까지 만들었으므로, support-health-gated residual을 작은 joint target correction으로 더하면 8cm visible squat 방향으로 안정 corridor가 조금 더 깊어질 수 있다.

외부 근거:
- Residual RL은 conventional controller가 잘 푸는 부분과 RL residual이 맡는 부분을 분해해 contact/friction 문제를 다루는 접근이다. URL: https://arxiv.org/abs/1812.03201, access date: 2026-06-18.
- Residual Policy Learning은 imperfect controller가 있을 때 residual을 학습해 복잡한 robot task를 개선하는 방법으로 제안됐다. URL: https://github.com/k-r-allen/residual-policy-learning, access date: 2026-06-18.
- ResMimic은 humanoid whole-body control에서 general motion tracking 위에 residual learning을 얹는 2-stage framework를 제안한다. URL: https://arxiv.org/html/2510.05070v1, access date: 2026-06-18.
- Humanoid squat 논문은 squatting이 whole-body coordination, foot force, dynamic constraints를 함께 요구하며 TP-MPC+WBC가 WBC 단독보다 tracking과 torque spike를 개선한다고 보고한다. URL: https://www.mdpi.com/1424-8220/25/2/435, access date: 2026-06-18.

## 2. 방법 (Method)

### 셋업
- 모델: local G1 MuJoCo model.
- teacher: exp55 best no-fall controller `com-feedback-a-blend0p50`.
- 코드: `run_teacher_residual_probe.py`.
- raw evidence: `verify/teacher-residual/`.

### 시나리오
- V0: `teacher-best`를 재실행해 exp55 baseline을 같은 harness에서 확인한다.
- V1: teacher target 위에 support-health-gated residual pattern을 더한다.
- Residual patterns:
  - `knee_only`
  - `hip_knee`
  - `counter_ankle`
  - `ankle_recenter`

### 측정 metric
- M19 native gate: fall 없음, visible drop >=0.08m, knee >=0.60rad, hip pitch >=0.35rad, return, contact >=0.90, slip <=0.15m.
- 추가 metric: support margin, ZMP margin, foot slip, contact ratio, return height.

## 3. 결과 (Results)

### 데이터
| Run | Verdict | Drop | Knee | Hip | Contact | Slip | CoM min | ZMP min | Fell |
|-----|---------|-----:|-----:|----:|--------:|-----:|--------:|--------:|------|
| teacher-best | DEPTH_PENDING | 0.0473m | 0.368 | 0.096 | 1.00 | 0.017m | 0.0292m | 0.0184m | never |
| teacher-knee-r0p04 | FAIL_FALL | 1.5082m | 0.586 | 0.360 | 0.91 | 0.910m | -0.5715m | -0.5713m | 5.14s |
| teacher-hip-knee-r0p06 | FAIL_FALL | 1.5092m | 0.587 | 0.350 | 0.87 | 0.892m | -0.5707m | -0.5728m | 4.68s |
| teacher-counter-ankle-r0p06 | FAIL_FALL | 1.5081m | 0.597 | 0.370 | 0.87 | 0.950m | -0.5683m | -0.5677m | 4.86s |
| teacher-ankle-recenter-r0p05 | DEPTH_PENDING | 0.0464m | 0.366 | 0.108 | 1.00 | 0.016m | 0.0410m | 0.0307m | never |

Best no-fall remains `teacher-best`: 4.73cm drop, contact 1.00, slip 0.017m, return true.

### 박제 위치
- `verify/teacher-residual/result.json`
- `verify/teacher-residual/com-zmp-feedback-summary.md`
- `verify/teacher-residual/*/native-eval.json`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- teacher 위 residual capacity 자체는 depth 방향으로 큰 leverage를 만든다. 하지만 knee/hip residual은 visible gate로 가기 전에 support/ZMP margin을 약 -0.57m까지 깨고 fall한다.
- ankle-only recenter residual은 support/ZMP margin을 teacher보다 조금 개선하지만 depth를 늘리지 못한다.
- 따라서 다음 residual fine-tune은 더 큰 residual amplitude가 아니라, action space를 stance/contact-safe manifold 안으로 제한하거나 support/ZMP/slip을 critic/termination으로 강하게 넣어야 한다.

### 가설은 통과했나?
- [ ] PASS
- [x] FAIL - bounded hand-designed residual은 M19 native gate를 닫지 못했고, depth residual은 바로 collapse mode를 만든다.

### 정의에 반영
- M19 완료 조건은 유지한다. browser replay 없이 native-only로 완료 처리하지 않는다.
- 다음 작업은 residual policy를 teacher 위에 얹되, foot slip/contact/support constraint를 residual action projection 또는 training termination으로 직접 제한해야 한다.

### 다음 실험 후보
- exp58 결과를 기반으로 residual action을 `ankle_recenter + shallow knee` 같은 safe basis로 제한하고 PPO/BC를 짧게 돌린다.
- torque/contact-aware WBC prototype에서 stance foot constraint를 hard cost에 가깝게 두고, residual policy는 pelvis height phase만 조정하게 한다.
