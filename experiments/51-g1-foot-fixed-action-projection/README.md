# 51-g1-foot-fixed-action-projection — stance-aware action projection probe

## 1. 가설 (Hypothesis)

exp50은 support/slip termination을 학습에 넣어도 native rollout에서 foot slip 3.276m를 막지 못했다. policy 출력과 motor target 사이에 foot-fixed residual/action projection을 넣어 slip limit에 가까워질수록 residual action을 줄이면, reward-only 방식보다 stance/contact gate를 더 직접적으로 보호할 수 있다.

근거:
- Constrained Whole-Body Tracking은 배포 중 새 안전 제약을 enforce하는 framework가 필요하다고 본다. https://arxiv.org/html/2606.00374v1 (accessed 2026-06-18)
- Not Only Rewards But Also Constraints는 legged RL에서 foot slippage를 reward term으로 다루되, 제목 그대로 reward 외 constraint 관점을 강조한다. https://arxiv.org/html/2308.12517v2 (accessed 2026-06-18)
- Versatile Locomotion Planning and Control for Humanoid Robots는 contact phase에서 contact wrench cone/terrain constraints를 enforce한다. https://www.frontiersin.org/journals/robotics-and-ai/articles/10.3389/frobt.2021.712239/full (accessed 2026-06-18)
- Stanford whole-body control primitives는 constraints, operational tasks, postures를 분리한다. https://khatib.stanford.edu/publications/pdfs/Sentis_2006_ICRA.pdf (accessed 2026-06-18)

## 2. 방법 (Method)

### 셋업
- 모델: local MuJoCo Playground G1 env.
- 정책: exp50 stance-constrained PPO checkpoint와 exp46 force/torque residual checkpoint.
- 하네스 구성: one experiment = one commit, raw evidence under `verify/`.

### projection modes
- `none`: policy action을 그대로 motor target으로 변환한다.
- `default-brake`: slip/support health가 나빠질수록 action을 0(default pose)으로 투영한다.
- `residual-clamp`: command target action + clipped policy residual로 투영하고, slip/support health가 낮으면 default pose로 되돌린다.
- `ankle-lock`: residual-clamp 위에 ankle pitch/roll residual을 더 강하게 제한한다.
- `soft-brake`: 완전 0으로 보내지 않고 최소 35% action은 남겨 급격한 collapse를 피한다.
- `residual-clamp-only` / `ankle-lock-only`: slip/support health brake 없이 residual 크기만 제한한다.

### 측정 metric
- visible pelvis drop, knee/hip pitch delta, fall time, final height/return, both-feet contact ratio, foot slip, support margin.
- M19 PASS는 exp29 visible gate와 native/browser replay가 동시에 통과해야 한다.

## 3. 결과 (Results)

### 데이터
| Source | Best/Mode | Verdict | Drop | Knee | Hip | Contact | Slip | 비고 |
|---|---|---|---:|---:|---:|---:|---:|---|
| exp50 | none | POSE_GATE_PENDING | 0.1047m | 0.589 | 0.565 | 0.37 | 3.205m | no fall, but knee just misses gate and slip/contact/return fail |
| exp50 | ankle-lock-only | FAIL_FALL | 1.5195m | 0.516 | 0.281 | 0.90 | 0.934m | slip lower than none, but falls at 1.22s |
| exp46 | none | POSE_GATE_PENDING | 0.1506m | 0.588 | 0.556 | 0.36 | 3.126m | no fall, but slip/contact/return fail |
| exp46 | ankle-lock-only | FAIL_FALL | 1.5145m | 0.578 | 0.278 | 0.92 | 0.945m | slip lower than none, but falls at 1.22s |

### 박제 위치
- `verify/target-0p08-residual-0p08/result.json`
- `verify/target-0p08-residual-0p08/projection-summary.md`
- per-mode raw JSON under `verify/target-0p08-residual-0p08/{exp50,exp46}/`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- action projection can reduce gross slip from about 3.2m to about 0.93-1.02m, but this is still far above the 0.15m stance gate.
- Hard or soft braking toward default pose is dynamically unsafe: contact ratio improves numerically, but the robot collapses around 1.2-2.0s.
- The no-projection runs show enough pelvis/hip movement for a visible-looking transition, but knee delta barely misses 0.60rad and contact/slip/return remain broken.

### 가설은 통과했나?
- [ ] PASS — projection protects stance while preserving visible depth, no-fall, knee/hip pose, contact, and return.
- [x] FAIL — projection reduced slip only partially and converted the failure mode into early fall.

### 정의에 반영
- M19 still cannot close from native-only evidence, and browser replay is not attempted until native gate passes.

### 다음 실험 후보
- Move from output projection to a foot-contact-aware controller: solve a per-step motor target with foot XY/contact constraints, then let the policy command only pelvis height/phase residuals.
