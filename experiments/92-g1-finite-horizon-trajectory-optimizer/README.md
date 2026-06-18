# 92-g1-finite-horizon-trajectory-optimizer - Full-rollout squat plan search

## 1. Hypothesis

If exp90/91 failed because online one-step target selection could not see the whole down-recapture-stand path, a finite-horizon trajectory plan search over timing, depth cap, pose bias, stance preload, slip/contact costs, and terminal stand should find a native rollout that satisfies the exp29 visible squat gate.

## 2. Method

### Setup
- Robot/model: local MuJoCo Playground G1 through the existing exp67/exp87/exp91 native evaluation path.
- Baseline: exp90 `preload35-contact`, carried forward as `baseline-exp90-contact`.
- Control change: evaluate full-rollout trajectory plan candidates instead of only adding direct knee torque. Candidate plans vary descent/recapture/return timing, depth cap, stance preload, foot XY stiffness, knee/hip pose bias, and terminal stand weighting.

### External check
- Humanoid squat research uses TP-MPC to optimize rough squat trajectories and WBC to follow them, so this experiment mirrors that structure at a small local scale. Source: `https://www.mdpi.com/1424-8220/25/2/435`, accessed 2026-06-18.
- MuJoCo whole-body MPC work reports that finite-horizon simulation with MuJoCo dynamics is a practical baseline for legged whole-body control. Source: `https://arxiv.org/html/2503.04613v2`, accessed 2026-06-18.
- MuJoCo MPC supports multiple-shooting and predictive-sampling style planners, motivating native rollout search before another reward-only loop. Source: `https://github.com/google-deepmind/mujoco_mpc`, accessed 2026-06-18.
- Whole-body constrained learning motivates low-level contact and foot-terrain constraints rather than pure policy reward shaping. Source: `https://arxiv.org/html/2506.05115v1`, accessed 2026-06-18.

### Command

```powershell
$env:OPENBLAS_NUM_THREADS='1'; C:\tmp\e34\Scripts\python.exe .\experiments\92-g1-finite-horizon-trajectory-optimizer\run_finite_horizon_trajectory_optimizer.py --seconds 6.0
```

### Metrics
- M19 native visible gate: no fall, pelvis drop >= 0.08m, knee delta >= 0.60rad, hip pitch delta >= 0.35rad, return-to-stand, contact ratio >= 0.90, foot slip <= 0.08m, joint limit violation <= 0.05.
- Raw evidence is under `verify/finite-horizon-trajectory-optimizer/`.

## 3. Results

Verdict: FAIL_VISIBLE_8CM_GATE.

| Rank | Attempt | Gate | Verdict | Drop | Knee | Hip | Contact | Slip | Fell |
|---:|---|---|---|---:|---:|---:|---:|---:|---|
| 1 | plan-8cm-knee-bias | FAIL | DEPTH_PENDING_8CM | 0.0514m | 0.378 | 0.204 | 1.00 | 0.018m | never |
| 2 | plan-8cm-slip-tight | FAIL | DEPTH_PENDING_8CM | 0.0512m | 0.376 | 0.202 | 0.99 | 0.022m | never |
| 3 | plan-9cm-terminal | FAIL | POSE_GATE_PENDING | 0.0930m | 0.421 | 0.368 | 0.93 | 0.085m | never |
| 4 | baseline-exp90-contact | FAIL | POSE_GATE_PENDING | 0.1721m | 0.427 | 0.436 | 0.91 | 0.096m | never |
| 5 | plan-terminal-micro-qfrc | FAIL | DEPTH_PENDING_8CM | 0.0541m | 0.395 | 0.181 | 0.99 | 0.025m | never |
| 6 | plan-terminal-narrow-qfrc | FAIL | DEPTH_PENDING_8CM | 0.0505m | 0.380 | 0.192 | 1.00 | 0.017m | never |
| 7 | plan-low-residual-long-horizon | FAIL | DEPTH_PENDING_8CM | 0.0511m | 0.378 | 0.179 | 1.00 | 0.025m | never |
| 8 | plan-light-pose-qfrc | FAIL | FAIL_FALL | 1.5301m | 0.660 | 0.344 | 0.94 | 0.340m | 4.88s |

Evidence:
- `verify/finite-horizon-trajectory-optimizer/result.json`
- `verify/finite-horizon-trajectory-optimizer/finite-horizon-trajectory-optimizer-summary.md`
- Per-run `native-eval.json` files under each attempt directory.

## 4. Insights

- The plan search exposes the same trade-off more cleanly: safe contact plans become shallow, and knee-success plans become fall trajectories.
- `plan-9cm-terminal` is the closest non-fall visible candidate: drop, hip, contact all pass, but knee stays at 0.421rad and slip is 0.085m.
- `plan-light-pose-qfrc` proves the simulated body can hit knee 0.660rad under this control surface, but it does so by entering the collapse branch.
- Hand-built finite-horizon grids are now exhausted. The next useful step is either a real optimizer over trajectory variables, not hand-tuned variants, or importing a motion-tracking/reference-policy method that can learn the coupled whole-body transition.

### Hypothesis outcome
- [ ] PASS
- [x] FAIL - full-rollout hand-built trajectory plans still cannot satisfy knee, slip, and terminal stand together.

### Next experiment candidate
- Use derivative-free predictive sampling or CMA-style search over trajectory parameters, with objective terms for knee >=0.60rad, slip <=0.08m, return-to-stand, and fall rejection.
