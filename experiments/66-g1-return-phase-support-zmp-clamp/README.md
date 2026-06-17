# Experiment 66 - G1 return phase support/ZMP clamp

## Hypothesis

exp65 showed that the current qfrc corridor can enter 7cm+ crouch depth, but the return phase breaks support/ZMP before the robot comes back to stand. If the return phase is rate-limited by support margin, ZMP margin, slip, and vertical velocity, the controller may preserve stance while closing the intermediate 7cm recoverable gate.

The public control literature points in the same direction: humanoid squat is usually framed as trajectory optimization plus whole-body control, with contact and ZMP constraints handled explicitly. This experiment stays narrower than a real WBC/QP solver: it only replaces exp62's abrupt `return_phase -> blend=0` transition with an online support/ZMP-aware return schedule.

Sources accessed 2026-06-18:
- Chen, Zhang, Zhao, "Squat Motion of a Humanoid Robot Using Three-Particle Model Predictive Control and Whole-Body Control", Sensors 2025: https://www.mdpi.com/1424-8220/25/2/435
- Kim, Lee, Park, "Real-time Whole-body Model Predictive Control for Bipedal Locomotion with a Novel Kino-dynamic Model and Warm-start Method": https://arxiv.org/html/2505.19540v1
- "Safe Whole-body Task-space Control for Humanoid Robots": https://par.nsf.gov/servlets/purl/10579190

## Method

`run_return_phase_support_zmp_clamp.py` adapts the exp62 native qfrc evaluator and changes only the return schedule:

- descend phase: keep the same target blend ramp.
- healthy return: release blend toward standing at `return_rate`.
- marginal return: release more slowly at `clamped_rate`.
- bad support/ZMP: force a faster `panic_release` toward standing rather than holding the crouch.

The gate is the same intermediate exp65 gate:

```text
fell_at is None
visible_drop >= 0.07
return_to_stand is true
foot_contact_ratio >= 0.90
foot_slip_distance <= 0.08
max_joint_limit_violation <= 0.05
```

Verification command:

```powershell
$env:OPENBLAS_NUM_THREADS='1'; C:\tmp\e34\Scripts\python.exe .\experiments\66-g1-return-phase-support-zmp-clamp\run_return_phase_support_zmp_clamp.py --seconds 8
```

Raw evidence:
- `verify/return-phase-support-zmp-clamp/result.json`
- `verify/return-phase-support-zmp-clamp/return-phase-support-zmp-clamp-summary.md`
- `verify/return-phase-support-zmp-clamp/*/native-eval.json`

## Results

Result: `FAIL_RECOVERABLE_7CM_GATE`.

The 8s stress run rules out the simplest "not enough time to return" explanation. Every candidate eventually fell around 5.36-6.02s, with large support/ZMP collapse and foot slip.

| Attempt | Verdict | Drop | Contact | Slip | CoM min | ZMP min | Final h | Fell |
|---|---|---:|---:|---:|---:|---:|---:|---|
| `release-8p5cm-r0p068-t26-rate0p72` | `FAIL_FALL` | 1.5130m | 0.90 | 0.938m | -0.5715m | -0.5721m | -0.7292m | 6.02s |
| `release-8p5cm-r0p070-t28-rate0p90` | `FAIL_FALL` | 1.5132m | 0.89 | 0.922m | -0.5711m | -0.5735m | -0.7567m | 5.74s |
| `release-8p3cm-r0p070-t28-rate0p90` | `FAIL_FALL` | 1.5136m | 0.90 | 0.928m | -0.5732m | -0.5745m | -0.7406m | 5.58s |
| `release-8p2cm-r0p068-t26-rate1p10` | `FAIL_FALL` | 1.5130m | 0.90 | 0.920m | -0.5724m | -0.5722m | -0.7259m | 6.02s |
| `release-8p0cm-r0p070-t28-rate1p20` | `FAIL_FALL` | 1.5117m | 0.90 | 0.906m | -0.5756m | -0.5759m | -0.7177m | 5.36s |

An earlier internal 6s sweep with hold-style panic clamp also failed: holding the crouch when support went negative removed qfrc assistance and deepened collapse. The final script therefore records the better diagnostic variant, panic release, but it still does not close the gate.

## Insights

Return scheduling alone is not enough. The failure is not just an abrupt blend discontinuity; once the robot enters the 7cm+ corridor, support/ZMP collapse becomes a coupled whole-body problem. A heuristic clamp can choose when to release, but it cannot replan a feasible CoM/contact wrench path.

The next M19 step should move from scalar return clamps to a small WBC/QP return selector or trajectory replan: choose among hold, partial return, and stand targets with explicit support/ZMP/contact costs before applying qfrc, instead of deciding blend rate after the state is already unsafe.
