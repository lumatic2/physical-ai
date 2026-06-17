# Experiment 67 - G1 qfrc WBC return selector

## Hypothesis

exp66 showed that scalar return clamps do not close the 7cm recoverable squat gate. A better approximation of WBC/QP should choose the next target by scoring candidate rollouts over support margin, ZMP margin, stance slip, contact, uprightness, qfrc effort, and return height before applying control.

This experiment combines exp62's qfrc-assisted lower-body controller with a one-step candidate selector. It is still not a full WBC/QP solver, but it is a closer proxy than scalar release rates because each candidate is stepped in MuJoCo before selection.

Sources accessed 2026-06-18:
- Chen, Zhang, Zhao, "Squat Motion of a Humanoid Robot Using Three-Particle Model Predictive Control and Whole-Body Control", Sensors 2025: https://www.mdpi.com/1424-8220/25/2/435
- Kim, Lee, Park, "Real-time Whole-body Model Predictive Control for Bipedal Locomotion with a Novel Kino-dynamic Model and Warm-start Method": https://arxiv.org/html/2505.19540v1
- Galdeano et al., "Task-based whole-body control of humanoid robots with ZMP regulation": https://www.lirmm.fr/krut/pdf/2014_galdeano_ssd-0568454426/2014_galdeano_ssd.pdf

## Method

`run_qfrc_wbc_return_selector.py` evaluates a small set of candidate blends each control step:

- descend: choose among shallow, partial, desired, and rate-limited deeper target blends.
- return: choose among stand release, slow release, fast release, and short hold.
- for each candidate: build the exp62 target, apply lower-body qfrc PD and stance force, step one control interval in MuJoCo, then score the candidate.
- score terms: target height, stand height, height floor, uprightness, support margin, ZMP margin, slip, contact, downward velocity, qfrc effort, and blend smoothness.

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
$env:OPENBLAS_NUM_THREADS='1'; C:\tmp\e34\Scripts\python.exe .\experiments\67-g1-qfrc-wbc-return-selector\run_qfrc_wbc_return_selector.py
```

Raw evidence:
- `verify/qfrc-wbc-return-selector/result.json`
- `verify/qfrc-wbc-return-selector/qfrc-wbc-return-selector-summary.md`
- `verify/qfrc-wbc-return-selector/*/native-eval.json`

## Results

Result: `FAIL_RECOVERABLE_7CM_GATE`.

| Attempt | Verdict | Drop | Contact | Slip | CoM min | ZMP min | qfrc | Final h | Fell |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| `selector-8cm-r0p065-t24` | `DEPTH_PENDING_7CM` | 0.0601m | 1.00 | 0.022m | -0.0032m | -0.0042m | 7.9 | 0.7430m | never |
| `selector-8p2cm-r0p068-t26` | `FAIL_FALL` | 0.5450m | 0.97 | 0.105m | -0.6011m | -0.6008m | 8.2 | 0.2100m | 5.86s |
| `selector-8p5cm-r0p068-t26` | `FAIL_FALL` | 0.5623m | 0.97 | 0.103m | -0.6011m | -0.6009m | 8.2 | 0.1927m | 5.86s |
| `selector-8p5cm-r0p070-t28` | `FAIL_FALL` | 0.9352m | 0.95 | 0.359m | -0.6025m | -0.6026m | 8.5 | -0.1802m | 5.74s |
| `selector-8p2cm-return-biased` | `RETURN_PENDING` | 0.1548m | 1.00 | 0.033m | -0.3195m | -0.1475m | 8.2 | 0.6002m | never |
| `selector-8cm-early-strong-return` | `DEPTH_PENDING_7CM` | 0.0586m | 1.00 | 0.049m | 0.0268m | -0.0127m | 14.7 | 0.7403m | never |
| `selector-8p2cm-early-strong-return` | `DEPTH_PENDING_7CM` | 0.0626m | 1.00 | 0.034m | 0.0163m | -0.0118m | 13.5 | 0.7433m | never |

The selector finds a clear trade-off:

- safety/return-biased variants keep contact and return, but actual depth stays around 5.9-6.3cm.
- depth-biased variants exceed 7cm, but support/ZMP collapse and fall.
- the best no-fall deeper candidate reaches 15.5cm but stops at final height 0.6002m, so it is not recoverable.

## Insights

The one-step WBC/QP-lite selector is useful diagnostically but still insufficient. It can choose stable shallow return, and it can choose deeper targets, but it cannot produce a dynamically feasible 7cm down-and-back trajectory. The missing piece is no longer a scalar gain or target selector; it is a multi-step trajectory/control problem with explicit CoM and contact-wrench planning.

The next M19 step should either use a longer-horizon rollout selector over the return phase or implement a reduced CoM/ZMP trajectory optimizer that plans the whole descent-hold-return path before qfrc execution. Another single-step heuristic is unlikely to close the gate.
