# Experiment 68 - G1 CoM/ZMP trajectory replan

## Hypothesis

exp67 showed that a one-step qfrc WBC selector can either keep a shallow return stable or push into fall, but it cannot close the 7cm recoverable gate. The next plausible blocker is the trajectory itself: descend and return timing must be planned as a short horizon CoM/ZMP problem before the WBC layer applies targets and qfrc.

This experiment does not implement a full continuous MPC solver. It tests the smallest planning-layer change: sweep multi-step descend/return timing and CoM/ZMP-heavy selector costs around the exp67 safety boundary, looking for a recoverable 7cm corridor.

Sources accessed 2026-06-18:
- Chen, Zhang, Zhao, "Squat Motion of a Humanoid Robot Using Three-Particle Model Predictive Control and Whole-Body Control", Sensors 2025: https://www.mdpi.com/1424-8220/25/2/435
- Kim, Lee, Park, "Real-time Whole-body Model Predictive Control for Bipedal Locomotion with a Novel Kino-dynamic Model and Warm-start Method": https://arxiv.org/html/2505.19540v1
- Russ Tedrake, "Highly-articulated Legged Robots", Underactuated Robotics: https://underactuated.mit.edu/humanoids.html

## Method

`run_com_zmp_trajectory_replan.py` reuses the exp67 qfrc WBC selector, but treats trajectory timing and costs as the planning layer:

- early-return plans start return sooner and give the controller more time to recover height.
- fine plans sweep the narrow 8.25-8.35cm target corridor that sits between stable 6cm and fall.
- mid-return/support-heavy plans test whether more depth can be recovered by shifting height/support/ZMP cost balance.

The intermediate gate remains:

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
$env:OPENBLAS_NUM_THREADS='1'; C:\tmp\e34\Scripts\python.exe .\experiments\68-g1-com-zmp-trajectory-replan\run_com_zmp_trajectory_replan.py
```

Raw evidence:
- `verify/com-zmp-trajectory-replan/result.json`
- `verify/com-zmp-trajectory-replan/com-zmp-trajectory-replan-summary.md`
- `verify/com-zmp-trajectory-replan/*/native-eval.json`

## Results

Result: `FAIL_RECOVERABLE_7CM_GATE`.

| Attempt | Verdict | Drop | Contact | Slip | CoM min | ZMP min | qfrc | Final h | Fell |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| `plan-8cm-early-return` | `DEPTH_PENDING_7CM` | 0.0599m | 0.98 | 0.058m | 0.0263m | -0.0103m | 32.1 | 0.7401m | never |
| `plan-8p2cm-early-return` | `DEPTH_PENDING_7CM` | 0.0641m | 0.99 | 0.046m | 0.0150m | -0.0070m | 14.1 | 0.7437m | never |
| `plan-8p25cm-fine` | `DEPTH_PENDING_7CM` | 0.0651m | 1.00 | 0.045m | 0.0129m | -0.0041m | 15.3 | 0.7466m | never |
| `plan-8p3cm-fine` | `FAIL_FALL` | 1.4371m | 0.93 | 0.590m | -0.5776m | -0.5775m | 9.6 | -0.6821m | 5.64s |
| `plan-8p35cm-fine` | `FAIL_FALL` | 1.4961m | 0.93 | 0.904m | -0.5855m | -0.5852m | 11.5 | -0.5942m | 5.34s |
| `plan-8p4cm-early-return` | `FAIL_FALL` | 1.4979m | 0.92 | 0.915m | -0.5956m | -0.5955m | 18.8 | -0.5436m | 5.24s |
| `plan-8p2cm-mid-return` | `FAIL_FALL` | 1.2080m | 0.94 | 0.398m | -0.5805m | -0.5804m | 9.2 | -0.4530m | 5.70s |
| `plan-8p5cm-mid-return` | `FAIL_FALL` | 1.4954m | 0.91 | 0.970m | -0.6037m | -0.6039m | 19.1 | -0.5886m | 5.30s |
| `plan-9cm-support-heavy` | `FAIL_FALL` | 1.4969m | 0.89 | 0.939m | -0.6051m | -0.6051m | 13.2 | -0.5456m | 5.20s |

Best stable return improved from exp67's 6.26cm to 6.51cm, but the 7cm recoverable gate still did not close. The cliff is sharp: `plan-8p25cm-fine` returns cleanly at 6.51cm, while `plan-8p3cm-fine` falls.

## Insights

Trajectory timing is part of the blocker, but not enough by itself. The stable corridor can be nudged upward to about 6.5cm with early return and stronger stand/upright costs, yet the next small increase enters a qualitatively different collapse mode with large slip and support/ZMP failure.

The next experiment should stop treating the planning layer as a parameter sweep. It needs an actual continuous or discrete horizon optimizer over planned CoM height/velocity and return target, with an explicit terminal stand constraint and support/ZMP constraints at each preview step.
