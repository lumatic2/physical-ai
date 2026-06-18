# 90-g1-qfrc-stance-preload-wrapper - G1 stance preload gate

## 1. Hypothesis

If the remaining M19 blocker is stance contact rather than G1 squat feasibility, adding an explicit foot-down qfrc preload under the exp87 three-phase teacher should improve contact/slip enough to close the exp29 visible squat gate.

## 2. Method

### Setup
- Robot/model: local MuJoCo Playground G1 through the existing exp67/exp87 native evaluation path.
- Baseline: exp87 `sched-8cm-return-heavy`, renamed here as `baseline-exp87-return-heavy`.
- Control change: add `apply_stance_preload()`, a stance-foot Jacobian force wrapper that applies downward qfrc based on foot contact state and stance-site height error.

### External check before experiment
- Unitree G1 has public visual evidence of a deep squat-like posture, so the local question is not pure kinematic impossibility. Source: `https://robotsguide.com/robots/unitree-g1`, accessed 2026-06-18.
- Recent humanoid squat work treats squatting as a whole-body coordination problem that must account for torso, arms, feet, foot force, and dynamic constraints. Source: `https://www.mdpi.com/1424-8220/25/2/435`, accessed 2026-06-18.
- Whole-body constrained learning motivates moving contact/foot-terrain constraints into a low-level follower instead of relying only on reward shaping. Source: `https://arxiv.org/html/2506.05115v1`, accessed 2026-06-18.
- MuJoCo whole-body MPC work supports using simulator dynamics/contact modeling for whole-body control probes. Source: `https://arxiv.org/html/2503.04613v2`, accessed 2026-06-18.

### Command

```powershell
$env:OPENBLAS_NUM_THREADS='1'; C:\tmp\e34\Scripts\python.exe .\experiments\90-g1-qfrc-stance-preload-wrapper\run_qfrc_stance_preload_wrapper.py --seconds 6.0
```

### Metrics
- M19 native visible gate: no fall, pelvis drop >= 0.08m, knee delta >= 0.60rad, hip pitch delta >= 0.35rad, return-to-stand, contact ratio >= 0.90, foot slip <= 0.08m, joint limit violation <= 0.05.
- Raw evidence is under `verify/qfrc-stance-preload-wrapper/`.

## 3. Results

Verdict: FAIL_VISIBLE_8CM_GATE.

| Rank | Attempt | Gate | Verdict | Drop | Knee | Hip | Contact | Slip | Fell |
|---:|---|---|---|---:|---:|---:|---:|---:|---|
| 1 | preload35-contact | FAIL | POSE_GATE_PENDING | 0.0980m | 0.427 | 0.436 | 0.93 | 0.097m | never |
| 2 | preload35-knee09 | FAIL | DEPTH_PENDING_8CM | 0.0764m | 0.430 | 0.387 | 0.91 | 0.105m | never |
| 3 | baseline-exp87-return-heavy | FAIL | POSE_GATE_PENDING | 0.0947m | 0.430 | 0.370 | 0.87 | 0.106m | never |
| 4 | preload20-return-heavy | FAIL | POSE_GATE_PENDING | 0.1102m | 0.435 | 0.387 | 0.89 | 0.122m | never |
| 5 | preload50-soft-depth | FAIL | POSE_GATE_PENDING | 0.2656m | 0.422 | 0.295 | 0.96 | 0.080m | never |
| 6 | preload20-xy-strong | FAIL | FAIL_FALL | 1.0449m | 0.432 | 0.339 | 0.89 | 0.343m | 5.72s |

Evidence:
- `verify/qfrc-stance-preload-wrapper/result.json`
- `verify/qfrc-stance-preload-wrapper/qfrc-stance-preload-wrapper-summary.md`
- Per-run `native-eval.json` files under each attempt directory.

## 4. Insights

- The robot-level answer is still "plausible": public G1 posture evidence plus humanoid squat WBC literature justify continuing experiments.
- The local gate did not close. Downward qfrc preload improved the baseline contact ratio from 0.87 to 0.93 on `preload35-contact`, while keeping fall-free 9.8cm drop and hip PASS.
- The blocker moved but did not disappear: knee flexion stays near 0.43rad, below the 0.60rad visible gate, and slip remains slightly above the 0.08m limit.
- Pure foot preload is too low-level to generate the missing knee posture. The next useful experiment should put knee/hip pose into a contact-constrained action/WBC wrapper, not just add more reward or more downward force.

### Hypothesis outcome
- [ ] PASS
- [x] FAIL - stance preload improves contact but does not close knee/slip/visible gate.

### Next experiment candidate
- Use the exp86/87 teacher inside a WBC/qfrc action wrapper where stance foot contact and knee/hip pose are optimized together before stepping MuJoCo.
