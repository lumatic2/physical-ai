# Experiment 64 - G1 recoverable 6cm stance transition

## Hypothesis

exp63 confirmed that static 8cm CoM-feasible targets are solvable, but dynamic native rollout still splits into shallow no-fall or support/ZMP collapse. The next useful gate is therefore not another direct 8cm push, but a smaller recoverable transition: at least 6cm pelvis drop, no fall, both feet in contact, low slip, and return to stand.

This follows the external control literature: humanoid squat work uses TP-MPC to generate a reference trajectory and WBC to track it, with torso, feet, contact wrench, and torque constraints handled together. ZMP/support planning also appears repeatedly in humanoid whole-body squat and push-recovery work. Our current stack is still a heuristic position-control and `qfrc_applied` probe, so 6cm is treated as an intermediate native gate, not as the M19 visible-squat gate.

Sources accessed 2026-06-18:
- Chen, Zhang, Zhao, "Squat Motion of a Humanoid Robot Using Three-Particle Model Predictive Control and Whole-Body Control", Sensors 2025: https://www.mdpi.com/1424-8220/25/2/435
- Kim, Lee, Park, "Real-time Whole-body Model Predictive Control for Bipedal Locomotion with a Novel Kino-dynamic Model and Warm-start Method": https://arxiv.org/html/2505.19540v1
- Galdeano et al., "Task-based whole body motion generation with ZMP planning": https://www.lirmm.fr/krut/pdf/2014_galdeano_ssd-0568454426/2014_galdeano_ssd.pdf

## Method

`run_recoverable_6cm_stance_transition.py` reuses two prior controller families without changing shared code:

1. exp60 `safe_combo` adaptive blend/residual controller.
2. exp62 lower-body actuator-space `qfrc_applied` torque controller.

The new gate is explicit:

```text
fell_at is None
visible_drop >= 0.06
return_to_stand is true
foot_contact_ratio >= 0.90
foot_slip_distance <= 0.08
max_joint_limit_violation <= 0.05
```

Verification command:

```powershell
$env:OPENBLAS_NUM_THREADS='1'; C:\tmp\e34\Scripts\python.exe .\experiments\64-g1-recoverable-6cm-stance-transition\run_recoverable_6cm_stance_transition.py
```

Raw evidence:
- `verify/recoverable-6cm/result.json`
- `verify/recoverable-6cm/recoverable-6cm-summary.md`
- `verify/recoverable-6cm/*/native-eval.json`

## Results

Result: `PASS_RECOVERABLE_6CM_GATE`.

| Attempt | Family | 6cm gate | Drop | Knee | Hip | Contact | Slip | CoM min | ZMP min | Final h | Fell |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `torque-8cm-r0p065-t24-6gate` | actuator_qfrc | PASS | 0.0600m | 0.428 | 0.201 | 1.00 | 0.026m | 0.0199m | -0.0311m | 0.7524m | never |
| `torque-8cm-r0p060-t20-6gate` | actuator_qfrc | FAIL | 0.0581m | 0.419 | 0.187 | 1.00 | 0.024m | 0.0221m | -0.0288m | 0.7499m | never |
| `safe-6cm-r0p070` | safe_combo | FAIL | 0.0493m | 0.384 | 0.108 | 1.00 | 0.015m | 0.0430m | 0.0343m | 0.7486m | never |
| `safe-8cm-r0p060-6gate` | safe_combo | FAIL | 1.5095m | 0.585 | 0.352 | 0.92 | 0.885m | -0.5682m | -0.5677m | -0.6467m | 5.36s |
| `torque-8p5cm-r0p065-t24-6gate` | actuator_qfrc | FAIL | 0.3118m | 0.459 | 0.257 | 0.98 | 0.054m | -0.5115m | -0.4949m | 0.4432m | 5.98s |

The passing run barely clears the intermediate depth target: visible drop is `0.060024889m`. It is not an M19 pass because the exp29 gate still requires 8cm visible drop, 0.60rad knee delta, 0.35rad hip delta, native no-fall, and browser replay together.

## Insights

The stable corridor moved from exp63's 5.51cm no-fall to a recoverable 6.00cm transition, but the margin is extremely thin. The best passing variant needed the 8cm target plus slightly stronger residual/torque (`r0p065`, `t24`) while still keeping stance slip low.

The next failure boundary is also clear. More aggressive safe_combo variants reach pose-like movement but collapse with large slip and support/ZMP breach. A slightly larger qfrc target (`8.5cm`) delayed collapse until 5.98s but still failed. So M19 should proceed by extending the qfrc recoverable corridor from 6cm toward 7cm before another 8cm visible-gate/browser attempt.
