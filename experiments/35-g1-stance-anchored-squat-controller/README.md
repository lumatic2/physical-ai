# 35-g1-stance-anchored-squat-controller - stance anchored squat controller

> M19 follow-up after exp34. Guarded descent found a no-fall 8cm drop candidate, but the feet slid and the robot did not return to stand. This experiment tests whether an explicit stance-anchor state machine can reach visible depth and return before foot slip/contact loss dominates.

## 1. 가설 (Hypothesis)

If exp34 failed because descent continued after the support stance was already degrading, then a controller that treats foot slip/contact as a first-class state transition should improve the M19 gate: descend only while stance is healthy, trigger return immediately after visible depth, and abort descent on support loss.

M19 success remains:
- pelvis/base drop from start >= 0.08m
- `fell_at is None`
- foot contact ratio >= 0.90
- final height returns to >= 0.74m
- stance slip remains bounded enough to be visually credible
- browser replay must pass before publishing a showable squat

반증 기준:
- early return prevents visible depth.
- visible depth still causes foot slip/contact loss before return can recover.
- returning to stand works only after micro-dips, not after >=8cm drop.

## 2. 방법 (Method)

planning_gate:
  team_validation_mode: manual-pass
  spec_delta: "M19 controller direction changes from guarded descent to stance-anchored descend/return state machine."
  perspectives:
    product: "보이는 스쿼트는 내려갔다가 제자리에서 다시 서야 한다. 미끄러져 이동한 drop은 showable skill이 아니다."
    architecture: "exp34 native loop를 재사용하되, controller mode를 descend/return/abort로 분리한다."
    security: "secret 없음. local Windows CPU JAX/MuJoCo runtime만 사용한다."
    qa: "variant별 raw JSON, trajectory, summary를 verify/에 보존한다."
    skeptic: "joint-position blend만으로 foot anchoring을 강제할 수 없어서 WBC/IK 없이 한계가 드러날 수 있다."
  dod:
    - "stance-anchor variants preserve raw evidence."
    - "summary identifies whether visible depth + return + contact can be satisfied together."
    - "ROADMAP next step is updated if M19 remains open."

### 외부 근거
- Dynamic Balanced Humanoid Locomotion, accessed 2026-06-18: ZMP inside the foot-ground support polygon is used as a dynamic-balance condition, and the support polygon can be approximated by supporting feet in a learning controller. URL: https://arxiv.org/html/2502.17219v1
- Squat Motion of a Humanoid Robot Using TP-MPC and WBC, accessed 2026-06-18: humanoid squatting is treated as a whole-body control problem involving torso orientation, arm/foot positioning, foot force, and dynamic constraints; TP-MPC plus WBC improves continuous squat tracking. URL: https://www.mdpi.com/1424-8220/25/2/435
- Benchmarking Dynamic Balancing Controllers for Humanoid Robots, accessed 2026-06-18: ZMP should remain inside the support polygon so the robot does not tip about the stance foot, and balance can require ankle/hip strategy transitions. URL: https://www.mdpi.com/2218-6581/11/5/114
- Task-based whole-body control of humanoid robots with ZMP regulation, accessed 2026-06-18: squat-like whole-body control prioritizes relative feet pose, CoM/ZMP regulation, and joint-limit avoidance; foot placement error often leads to falls. URL: https://www.lirmm.fr/krut/pdf/2014_galdeano_ssd-0568454426/2014_galdeano_ssd.pdf

### 셋업
- Base runner/env: `experiments/34-g1-guarded-descent-controller/run_guarded_descent.py`
- New runner: `experiments/35-g1-stance-anchored-squat-controller/run_stance_anchor.py`
- Source params: `experiments/22-g1-squat-depth-finetune/verify/train/params.pkl`
- Target stage: `0.67m`
- Freeze phase: `true`
- Native duration: `6s`

### 시나리오
- A: early-visible-return, trigger at 0.08m drop with assertive descent.
- B: preemptive-return, trigger at 0.07m drop before the exp34 slip cliff.
- C: stance-tight, trigger at 0.075m drop and abort on 2cm slip.

### 측정 metric
- visible drop, fall time, final height
- foot contact ratio, max foot slip
- return trigger reason and trigger time
- time spent in descend/return/abort
- joint limit violation

## 3. 결과 (Results)

### 데이터
| Run | Verdict | Cost | Retries | 비고 |
|-----|---------|------|---------|------|
| smoke | DEPTH_PENDING | local Windows CPU JAX/MuJoCo 0.2s | 0 | import/env/params smoke passed |
| early-visible-return | FAIL_FALL | local Windows CPU JAX/MuJoCo 6s | 0 | visible threshold triggered return at 2.16s, but fall at 2.48s |
| preemptive-return | FAIL_FALL | local Windows CPU JAX/MuJoCo 6s | 0 | trigger at 2.16s, fall at 2.54s |
| stance-tight | FAIL_FALL | local Windows CPU JAX/MuJoCo 6s | 0 | slip abort at 2.28s, fall at 2.62s |
| slow-visible-return-9s | FAIL_FALL | local Windows CPU JAX/MuJoCo 9s | 0 | slow descent hit contact loss at 4.30s, fall at 4.88s |
| slow-preemptive-9s | FAIL_FALL | local Windows CPU JAX/MuJoCo 9s | 0 | contact loss at 3.58s, fall at 4.14s |
| no-policy-visible-return | FAIL_FALL | local Windows CPU JAX/MuJoCo 6s | 0 | learned residual disabled; fall worsened to 1.24s |
| no-policy-preemptive | FAIL_FALL | local Windows CPU JAX/MuJoCo 6s | 0 | learned residual disabled; fall at 1.24s |

| Variant | Policy weight | Trigger | Drop | Fell at | Contact | Final height | Foot slip | Verdict |
|---|---:|---|---:|---:|---:|---:|---:|---|
| early-visible-return | 1.0 | visible_then_abort @ 2.16s | 1.5264m | 2.48s | 0.95 | -0.6518m | 1.004m | FAIL_FALL |
| preemptive-return | 1.0 | visible_then_abort @ 2.16s | 1.5341m | 2.54s | 0.90 | -0.6596m | 0.977m | FAIL_FALL |
| stance-tight | 1.0 | slip_abort @ 2.28s | 1.5303m | 2.62s | 0.89 | -0.6665m | 0.961m | FAIL_FALL |
| slow-visible-return-9s | 1.0 | contact_loss @ 4.30s | 1.5286m | 4.88s | 0.89 | -0.7242m | 1.162m | FAIL_FALL |
| slow-preemptive-9s | 1.0 | contact_loss @ 3.58s | 1.5281m | 4.14s | 0.91 | -0.7204m | 1.158m | FAIL_FALL |
| no-policy-visible-return | 0.0 | visible_then_abort @ 0.96s | 1.5333m | 1.24s | 0.91 | -0.7490m | 1.005m | FAIL_FALL |
| no-policy-preemptive | 0.0 | visible_then_abort @ 0.92s | 1.5330m | 1.24s | 0.92 | -0.7505m | 0.988m | FAIL_FALL |

### 박제 위치
- `verify/attempts/*/stance-anchor-native-eval.json`
- `verify/stance-anchor-summary.md`
- `verify/stance-anchor-trajectory-*.json`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- Stance-anchor state transitions did not close M19. Early return after visible depth still falls because downward momentum and support degradation are already too large.
- Slower descent delays the fall but does not solve support. The slow 9s variants trigger on contact loss before a valid visible squat-return cycle can complete.
- Disabling the learned policy residual makes the result worse: no-policy variants fall at 1.24s, close to the old scripted baseline failure. The stabilizer is helping, but it is not sufficient for deep squat recovery.
- The bottleneck is no longer just controller scheduling. Position-target blend lacks an explicit whole-body constraint for foot placement, CoM/ZMP/support polygon, and return momentum.
- The next M19 attempt should stop treating this as a hand-written blend controller. It needs either a stance/CoM-aware WBC or a training run with stance/ZMP-style rewards and return-to-stand from visible depth.

### 가설은 통과했나?
- [ ] PASS — stance-anchor early return closes visible squat.
- [x] FAIL — every stance-anchor variant failed fall/return/stance gates.

### 정의에 반영
- M19 remains open. A visible-drop-only or early-return-only controller is not enough.
- Position blend controllers should be considered exhausted unless they add explicit whole-body constraints.

### 다음 실험 후보
- `g1-stance-reward-finetune`: train from the stabilizer prior with explicit stance slip, support-center, visible-depth, and return-to-stand rewards.
- `g1-wbc-squat-prototype`: prototype a low-rate IK/WBC target that keeps foot pose fixed while moving pelvis/CoM, before another PPO run.
