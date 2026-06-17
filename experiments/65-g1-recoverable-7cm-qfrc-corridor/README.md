# Experiment 65 - G1 recoverable 7cm qfrc corridor

## Hypothesis

exp64 opened a narrow recoverable 6cm stance transition with `qfrc_applied` lower-body torque assistance. If that corridor can be extended smoothly, a 7cm native transition should pass before attempting the full exp29 8cm visible-squat/browser gate again.

The literature suggests this should ultimately be handled as a trajectory plus whole-body control problem, not as scalar torque tuning. The 2025 TP-MPC/WBC squat paper uses MPC to optimize a reference trajectory and WBC to follow it with torso, feet, contact wrench, and torque constraints. WB-MPC work also treats ZMP tracking relative to the support polygon as a core balance term. This experiment stays deliberately narrower: it tests whether the current qfrc heuristic has enough margin to reach a 7cm recoverable corridor before implementing a real return-stabilized WBC layer.

Sources accessed 2026-06-18:
- Chen, Zhang, Zhao, "Squat Motion of a Humanoid Robot Using Three-Particle Model Predictive Control and Whole-Body Control", Sensors 2025: https://www.mdpi.com/1424-8220/25/2/435
- Kim, Lee, Park, "Real-time Whole-body Model Predictive Control for Bipedal Locomotion with a Novel Kino-dynamic Model and Warm-start Method": https://arxiv.org/html/2505.19540v1
- Galdeano et al., "Task-based whole body motion generation with ZMP planning": https://www.lirmm.fr/krut/pdf/2014_galdeano_ssd-0568454426/2014_galdeano_ssd.pdf

## Method

`run_recoverable_7cm_qfrc_corridor.py` calls the exp62 actuator-qfrc native evaluator directly and sweeps only target/drop/blend/residual/torque timing around the exp64 passing point.

The new intermediate gate is:

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
$env:OPENBLAS_NUM_THREADS='1'; C:\tmp\e34\Scripts\python.exe .\experiments\65-g1-recoverable-7cm-qfrc-corridor\run_recoverable_7cm_qfrc_corridor.py
```

Raw evidence:
- `verify/recoverable-7cm/result.json`
- `verify/recoverable-7cm/recoverable-7cm-summary.md`
- `verify/recoverable-7cm/*/native-eval.json`

## Results

Result: `FAIL_RECOVERABLE_7CM_GATE`.

| Attempt | 7cm gate | Verdict | Drop | Knee | Hip | Contact | Slip | CoM min | ZMP min | Final h | Fell |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `qfrc-8cm-r0p065-t24-baseline` | FAIL | `DEPTH_PENDING_7CM` | 0.0600m | 0.428 | 0.201 | 1.00 | 0.026m | 0.0199m | -0.0311m | 0.7524m | never |
| `qfrc-8cm-r0p070-t24` | FAIL | `DEPTH_PENDING_7CM` | 0.0632m | 0.443 | 0.263 | 1.00 | 0.030m | 0.0098m | -0.0359m | 0.7512m | never |
| `qfrc-8p5cm-r0p068-t26` | FAIL | `RETURN_PENDING` | 0.0742m | 0.458 | 0.249 | 1.00 | 0.049m | -0.2703m | -0.1353m | 0.6808m | never |
| `qfrc-8p5cm-r0p070-t28` | FAIL | `RETURN_PENDING` | 0.1938m | 0.466 | 0.220 | 0.99 | 0.049m | -0.3960m | -0.3068m | 0.5612m | never |
| `qfrc-8p5cm-r0p068-t26-early-return` | FAIL | `FAIL_FALL` | 0.9871m | 0.563 | 0.354 | 0.94 | 0.354m | -0.5696m | -0.5696m | -0.2321m | 5.76s |

Best no-fall run by depth was `qfrc-8p5cm-r0p070-t28`, but it ended at final height `0.5612m`, so it did not return to stand. Early-return variants made the rebound/stance problem worse and fell.

## Insights

The corridor did not extend cleanly from 6cm to 7cm. The system can enter a deeper crouch without triggering the current fall detector, but the return phase breaks support/ZMP and final height. This is a qualitatively different blocker from exp64: depth is available, recovery is not.

The next experiment should stop increasing residual/torque and instead add return-specific stabilization: either a return-phase support/ZMP clamp that delays stand-up when margins go negative, or a small WBC/QP return selector that chooses between holding depth, partial return, and full return using support/ZMP/slip forecasts.
