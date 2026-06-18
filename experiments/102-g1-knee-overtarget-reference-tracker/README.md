# 102-g1-knee-overtarget-reference-tracker — G1 knee overtarget reference tracker

> M19. exp94 showed that a visible squat reference exists, but the best no-fall stabilizer-conditioned tracker reached depth/contact/slip while actual knee flexion stayed at 0.401rad. This experiment tests whether explicitly over-targeting knee flexion in that reference family can close the exp29 knee gate.

## 1. 가설 (Hypothesis)

If the exp94 failure is mostly target under-commanding, then raising the reference knee target from 0.64rad to 0.85-1.10rad should increase achieved knee flexion toward the exp29 0.60rad gate while preserving the already-promising depth/contact/slip corridor.

If achieved knee remains pinned below the gate or enters fall/slip, then the blocker is not reference target magnitude but the stabilizer/controller representation. In that case M19 should move to a dedicated motion-tracking/reference-policy training route instead of more hand-authored reference injection.

## 2. 방법 (Method)

### 셋업
- Base evaluator: exp94 `run_visible_reference_motion_tracking_probe.py`.
- Model/runtime: local MuJoCo G1 through exp67/exp94 native metrics.
- Source checkpoint/controller family: exp94 stabilizer-conditioned reference injection.
- Raw evidence: `verify/knee-overtarget-reference-tracker/`.

### 웹 근거
- UniTracker reports whole-body motion tracking on a 29-DoF Unitree G1, including squatting among tracked real-world motions. URL: https://arxiv.org/html/2507.07356v2 accessed 2026-06-18.
- G1 Moves provides retargeted Unitree G1 trajectories, RL training data, and trained policies, supporting the reference-motion route. URL: https://huggingface.co/datasets/exptech/g1-moves accessed 2026-06-18.
- Humanoid squat control literature frames squat as CoM/ZMP/feet/joint trajectory coordination, not a single joint target. URL: https://www.mdpi.com/1424-8220/25/2/435 accessed 2026-06-18.
- MuJoCo Predictive Sampling motivates using native rollout evidence rather than accepting a planned reference target as proof. URL: https://arxiv.org/abs/2212.00541 accessed 2026-06-18.

### 시나리오
- Re-run exp94 best stabilizer-reference family with larger target knee deltas: 0.85, 0.95, 1.05, 1.10rad.
- Sweep moderate vs strong reference weights and health release floors.
- Keep M19 gate unchanged: no fall, drop >=8cm, knee >=0.60rad, hip >=0.35rad, return to stand, contact >=0.90, slip <=0.08m, joint limit violation <=0.05.

## 3. 결과 (Results)

### 데이터
| Attempt | Verdict | Drop | Knee | Hip | Contact | Slip | Fall | 비고 |
|-----|---------|------|------|-----|---------|------|------|------|
| baseline-exp94-k0p64 | POSE_GATE_PENDING | 0.2581m | 0.404rad | 0.372rad | 1.00 | 0.046m | never | gap d/k/h 0.0000/0.196/0.000 |
| k0p85-balanced | DEPTH_PENDING_8CM | 0.0448m | 0.353rad | 0.238rad | 1.00 | 0.026m | never | gap d/k/h 0.0352/0.247/0.112 |
| k1p05-cautious | DEPTH_PENDING_8CM | 0.0389m | 0.305rad | 0.162rad | 1.00 | 0.016m | never | gap d/k/h 0.0411/0.295/0.188 |
| k1p05-strong | FAIL_FALL | 0.6769m | 0.521rad | 0.456rad | 0.98 | 0.091m | 5.86s | gap d/k/h 0.0000/0.079/0.000 |
| k1p10-hip0p42 | FAIL_FALL | 1.5278m | 0.527rad | 0.438rad | 0.96 | 0.309m | 4.76s | gap d/k/h 0.0000/0.073/0.000 |
| k0p95-balanced | FAIL_FALL | 1.5280m | 0.512rad | 0.423rad | 0.96 | 0.316m | 5.02s | gap d/k/h 0.0000/0.088/0.000 |
| k0p95-fast-return | FAIL_FALL | 1.5288m | 0.488rad | 0.406rad | 0.94 | 0.321m | 4.42s | gap d/k/h 0.0000/0.112/0.000 |
| k1p10-fast-return | FAIL_FALL | 1.5289m | 0.473rad | 0.389rad | 0.96 | 0.322m | 4.66s | gap d/k/h 0.0000/0.127/0.000 |
| k1p05-fast-return | FAIL_FALL | 1.5280m | 0.485rad | 0.397rad | 0.95 | 0.328m | 4.48s | gap d/k/h 0.0000/0.115/0.000 |

Verdict: `FAIL_VISIBLE_8CM_GATE`.

### 박제 위치
- `verify/knee-overtarget-reference-tracker/result.json`
- `verify/knee-overtarget-reference-tracker/knee-overtarget-reference-summary.md`
- Per-variant native rollouts under `verify/knee-overtarget-reference-tracker/*/native-eval.json`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- Knee over-targeting did not close the exp29 visible gate.
- Best optimizer run `baseline-exp94-k0p64` reached drop `0.2581m`, knee `0.404rad`, hip `0.372rad`, contact `1.00`, slip `0.046m`.
- Best no-fall candidate `baseline-exp94-k0p64` still leaves knee shortfall `0.196rad`.
- Increasing target knee magnitude mostly exposes the same representation limit: the stabilizer-conditioned reference injection either keeps stance while under-flexing the knee, or moves toward the collapse/fall branch.

### 가설은 통과했나?
- [ ] PASS
- [x] FAIL — over-targeting the reference knee does not produce a native visible squat gate pass.

### 정의에 반영
- M19 should not spend more experiments on scalar reference injection. The next route is a dedicated reference-conditioned tracker policy or a true trajectory optimizer over full qpos/action knots.
