# 91-g1-contact-constrained-pose-qfrc-wrapper - Contact-gated knee/hip qfrc assist

## 1. Hypothesis

If exp90 failed because the control layer only kept the feet down but did not directly command the missing knee flexion, adding contact-gated knee/hip qfrc pose assist on top of stance preload should close the exp29 visible squat gate.

## 2. Method

### Setup
- Robot/model: local MuJoCo Playground G1 through the existing exp67/exp87 native evaluation path.
- Baseline: exp90 `preload35-contact`, carried forward as `baseline-exp90-contact`.
- Control change: add `apply_pose_qfrc_assist()`, a generalized-force wrapper that pushes knee/hip joints toward the exp29 pose deltas only while support, ZMP, slip, and foot-contact health remain acceptable.

### External check
- Humanoid squat work frames squatting as a whole-body coordination problem with foot-force and dynamic constraints, not isolated knee tracking. Source: `https://www.mdpi.com/1424-8220/25/2/435`, accessed 2026-06-18.
- Whole-body constrained learning places contact and foot-terrain constraints in a low-level whole-body follower, matching the move from reward-only loops to qfrc/WBC wrappers. Source: `https://arxiv.org/html/2506.05115v1`, accessed 2026-06-18.
- Recent G1 whole-body motion tracking work reports broad Unitree G1 motion tracking but uses unified whole-body policies rather than one-off joint pushes. Source: `https://arxiv.org/html/2507.07356v3`, accessed 2026-06-18.
- General humanoid control work notes that physical consistency includes maintaining foot contact above the ground plane during motion tracking. Source: `https://arxiv.org/html/2602.11929v1`, accessed 2026-06-18.

### Command

```powershell
$env:OPENBLAS_NUM_THREADS='1'; C:\tmp\e34\Scripts\python.exe .\experiments\91-g1-contact-constrained-pose-qfrc-wrapper\run_contact_constrained_pose_qfrc_wrapper.py --seconds 6.0
```

### Metrics
- M19 native visible gate: no fall, pelvis drop >= 0.08m, knee delta >= 0.60rad, hip pitch delta >= 0.35rad, return-to-stand, contact ratio >= 0.90, foot slip <= 0.08m, joint limit violation <= 0.05.
- Raw evidence is under `verify/contact-constrained-pose-qfrc-wrapper/`.

## 3. Results

Verdict: FAIL_VISIBLE_8CM_GATE.

| Rank | Attempt | Gate | Verdict | Drop | Knee | Hip | Contact | Slip | Fell |
|---:|---|---|---|---:|---:|---:|---:|---:|---|
| 1 | poseqfrc-light | FAIL | POSE_GATE_PENDING | 0.0807m | 0.448 | 0.367 | 0.92 | 0.090m | never |
| 2 | baseline-exp90-contact | FAIL | POSE_GATE_PENDING | 0.0980m | 0.427 | 0.436 | 0.93 | 0.097m | never |
| 3 | poseqfrc-braked-8cm | FAIL | FAIL_FALL | 0.4652m | 0.418 | 0.313 | 0.91 | 0.096m | 5.92s |
| 4 | poseqfrc-strong-health | FAIL | FAIL_FALL | 1.5297m | 0.546 | 0.348 | 0.92 | 0.345m | 4.82s |
| 5 | poseqfrc-braked-return | FAIL | FAIL_FALL | 1.5290m | 0.531 | 0.351 | 0.94 | 0.350m | 5.00s |
| 6 | poseqfrc-medium | FAIL | FAIL_FALL | 1.5280m | 0.524 | 0.312 | 0.91 | 0.353m | 4.88s |
| 7 | poseqfrc-recapture-soft | FAIL | FAIL_FALL | 1.5310m | 0.499 | 0.354 | 0.92 | 0.366m | 4.88s |
| 8 | poseqfrc-slip-tight | FAIL | FAIL_FALL | 1.5292m | 0.509 | 0.318 | 0.94 | 0.350m | 5.32s |
| 9 | poseqfrc-braked-knee | FAIL | FAIL_FALL | 1.5257m | 0.392 | 0.435 | 0.91 | 0.400m | 5.50s |

Evidence:
- `verify/contact-constrained-pose-qfrc-wrapper/result.json`
- `verify/contact-constrained-pose-qfrc-wrapper/contact-constrained-pose-qfrc-wrapper-summary.md`
- Per-run `native-eval.json` files under each attempt directory.

## 4. Insights

- The light contact-gated pose assist improved the optimizer score and knee delta relative to exp90, but only from 0.427rad to 0.448rad. It still misses the 0.60rad knee gate.
- Stronger pose qfrc creates the known failure branch: knee approaches 0.50-0.55rad, but the robot over-descends, slips, and falls around 4.8-5.9s.
- This suggests the plateau is not just "no knee torque." The missing piece is a coupled whole-body optimization or learned tracker that constrains pelvis height, foot contact, knee pose, and return as one trajectory.
- Next useful direction: stop adding direct knee pushes and either solve a finite-horizon trajectory optimization problem over target qpos/qfrc, or import a motion-tracking style reference policy into the local G1 gate.

### Hypothesis outcome
- [ ] PASS
- [x] FAIL - contact-gated knee/hip qfrc assist improves the best knee metric slightly but does not close the visible gate.

### Next experiment candidate
- Build a finite-horizon trajectory optimizer around the exp90 contact-safe branch: optimize phase target sequence for 8cm drop, knee >=0.60rad, slip <=0.08m, and terminal stand before rolling it out natively.
