# 93-g1-predictive-sampling-trajectory-search - Seeded rollout sampling

## 1. Hypothesis

If exp92 failed because the hand-built plan grid was too coarse, a seeded predictive-sampling search around the closest non-fall visible branch should find a parameter set that satisfies the exp29 visible squat gate.

## 2. Method

### Setup
- Robot/model: local MuJoCo Playground G1 through the existing exp67/exp87/exp92 native evaluation path.
- Search seed: exp92 `plan-9cm-terminal`, then a second batch seeded from the best visible-depth sample found in the first batch.
- Search variables: blend, residual scale, depth cap, slip/contact/stand/knee/hip weights, foot XY stiffness, stance preload, knee/hip pose bias, timing, recapture drop, and small pose-qfrc terms.

### External check
- MuJoCo MPC supports derivative-free Predictive Sampling in addition to iLQG and gradient descent. Source: `https://github.com/google-deepmind/mujoco_mpc`, accessed 2026-06-18.
- The Predictive Sampling paper frames this as a simple but competitive derivative-free shooting planner over MuJoCo rollouts. Source: `https://arxiv.org/abs/2212.00541`, accessed 2026-06-18.
- MuJoCo whole-body MPC work supports using MuJoCo dynamics and contact modeling for humanoid whole-body control. Source: `https://arxiv.org/html/2503.04613v2`, accessed 2026-06-18.
- Humanoid squat research uses trajectory optimization plus WBC, matching this experiment's shift away from one-step hand tuning. Source: `https://www.mdpi.com/1424-8220/25/2/435`, accessed 2026-06-18.

### Command

```powershell
$env:OPENBLAS_NUM_THREADS='1'; C:\tmp\e34\Scripts\python.exe .\experiments\93-g1-predictive-sampling-trajectory-search\run_predictive_sampling_trajectory_search.py --seconds 6.0
```

### Metrics
- M19 native visible gate: no fall, pelvis drop >= 0.08m, knee delta >= 0.60rad, hip pitch delta >= 0.35rad, return-to-stand, contact ratio >= 0.90, foot slip <= 0.08m, joint limit violation <= 0.05.
- Raw evidence is under `verify/predictive-sampling-trajectory-search/`.

## 3. Results

Verdict: FAIL_VISIBLE_8CM_GATE.

| Rank | Attempt | Gate | Verdict | Drop | Knee | Hip | Contact | Slip | Fell |
|---:|---|---|---|---:|---:|---:|---:|---:|---|
| 1 | baseline-plan9-terminal | FAIL | POSE_GATE_PENDING | 0.0871m | 0.421 | 0.403 | 0.94 | 0.075m | never |
| 2 | sample-09 | FAIL | DEPTH_PENDING_8CM | 0.0519m | 0.378 | 0.196 | 0.99 | 0.027m | never |
| 3 | sample-12 | FAIL | DEPTH_PENDING_8CM | 0.0522m | 0.380 | 0.189 | 0.99 | 0.026m | never |
| 4 | sample-08 | FAIL | DEPTH_PENDING_8CM | 0.0502m | 0.372 | 0.208 | 1.00 | 0.018m | never |
| 5 | seed-sample15-visible-branch | FAIL | POSE_GATE_PENDING | 0.1073m | 0.423 | 0.395 | 0.94 | 0.094m | never |
| 6 | sample-07 | FAIL | DEPTH_PENDING_8CM | 0.0617m | 0.425 | 0.256 | 0.97 | 0.075m | never |
| 7 | sample-10 | FAIL | DEPTH_PENDING_8CM | 0.0629m | 0.420 | 0.384 | 0.95 | 0.090m | never |
| 8 | sample-04 | FAIL | FAIL_FALL | 1.5307m | 0.540 | 0.318 | 0.96 | 0.321m | 5.44s |

Evidence:
- `verify/predictive-sampling-trajectory-search/result.json`
- `verify/predictive-sampling-trajectory-search/predictive-sampling-trajectory-search-summary.md`
- Per-run `native-eval.json` files under each attempt directory.

## 4. Insights

- Predictive sampling improved coverage but did not find a gate-passing point.
- The best non-fall gate candidate is still effectively the exp92 terminal branch: drop, hip, contact, slip all pass, but knee remains around 0.421rad.
- The sampled visible-depth branch can reach 10.7cm drop with hip/contact pass, but slip rises to 9.4cm and knee remains 0.423rad.
- The knee-improving branch still collapses: the top knee sample reaches 0.540rad but falls with 32cm slip.
- This is now strong evidence that the current local controller/action-wrapper family cannot create the visible squat knee posture while preserving stance. The next step should switch representation: either motion-tracking/reference-policy learning, or an optimizer that controls full qpos targets at multiple shooting knots rather than tuning this controller's scalar parameters.

### Hypothesis outcome
- [ ] PASS
- [x] FAIL - seeded predictive sampling over the current controller parameters still misses the knee gate or falls.

### Next experiment candidate
- Try a motion-tracking reference-policy route: compile a visible squat reference with explicit knee posture and train or evaluate a stabilizer-conditioned tracker, rather than continuing scalar controller search.
