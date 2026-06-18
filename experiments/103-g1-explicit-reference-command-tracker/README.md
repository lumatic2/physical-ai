# 103-g1-explicit-reference-command-tracker — explicit visible reference command tracker

> M19. exp102 ruled out scalar knee over-targeting inside the hand-written reference injection path. This experiment switches the training target itself: keep the existing checkpoint-compatible observation/action shape, but make the command-conditioned PPO target an explicit foot-fixed visible squat reference.

## 1. 가설 (Hypothesis)

If M19 is blocked because the learned command-conditioned policy has been trained against the wrong lower-body target family, then replacing `_command_target_pose` with the exp94 foot-fixed visible reference should let a short restored PPO finetune increase achieved knee flexion while preserving the exp80 visible-depth signal.

If the policy still retreats to shallow/unsafe stance or falls, then the blocker is not just reference target definition. The next step should use a larger motion-tracking stack with future reference observations or external G1 Moves/UniTracker-style policy ingestion.

## 2. 방법 (Method)

### 셋업
- Base training/evaluator: exp80 `run_corridor_curriculum.py`.
- New env: `g1_explicit_reference_command_env.py`, preserving exp80 observation/action shape.
- Source checkpoint: exp80 visible-geometry checkpoint if present, otherwise exp50 stance-constrained checkpoint.
- Runtime: local MuJoCo/JAX environment `C:\tmp\e34`.

### 웹 근거
- UniTracker trains a single policy to track thousands of motions on a 29-DoF Unitree G1, including real-world motion tracking. URL: https://arxiv.org/html/2507.07356v2 accessed 2026-06-18.
- GMT frames humanoid whole-body control as a scalable reference-motion tracking policy problem. URL: https://arxiv.org/html/2506.14770v1 accessed 2026-06-18.
- ASAP uses phase-based motion tracking training for Unitree G1 skills in HumanoidVerse. URL: https://github.com/LeCAR-Lab/ASAP accessed 2026-06-18.
- Humanoid squat control literature treats squat as coordinated CoM/ZMP/feet/joint trajectory tracking. URL: https://www.mdpi.com/1424-8220/25/2/435 accessed 2026-06-18.

### 측정 metric
- exp29 visible native gate: no fall, pelvis drop >=8cm, knee >=0.60rad, hip >=0.35rad, return to stand, both-foot contact >=0.90, slip <=0.08m, joint limit violation <=0.05.
- Browser replay is attempted only if native gate passes.

## 3. 결과 (Results)

### 데이터
| Run | Verdict | Timesteps | Drop | Knee | Hip | Contact | Slip | Final h | Fall |
|-----|---------|---:|---:|---:|---:|---:|---:|---:|---|
| explicit-reference-command | DEPTH_PENDING_7CM | 20000 | 0.0572m | 0.583rad | 0.492rad | 0.39 | 3.090m | 0.7408m | never |

Verdict: `DEPTH_PENDING_7CM`.

### 박제 위치
- `verify/target-0p090-slip-0p08/result.json`
- `verify/target-0p090-slip-0p08/native-eval.json`
- `verify/target-0p090-slip-0p08/explicit-reference-command-summary.md`
- `verify/target-0p090-slip-0p08/train/params.pkl`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- Explicit foot-fixed visible reference command training did not close M19 in this short finetune.
- Native rollout reached drop `0.0572m`, knee `0.583rad`, hip `0.492rad`, contact `0.39`, slip `3.090m`.
- The result tells us whether changing the supervised command target alone is enough before moving to larger future-reference observations or external tracker ingestion.

### 가설은 통과했나?
- [ ] PASS
- [x] FAIL — explicit reference-command PPO did not produce a native visible gate pass.

### 정의에 반영
- M19 remains open. Browser replay is not attempted until the native gate passes.
