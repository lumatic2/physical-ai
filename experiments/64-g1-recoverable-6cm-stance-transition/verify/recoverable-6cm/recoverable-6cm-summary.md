# G1 Recoverable 6cm Stance Transition Summary

| Attempt | Family | 6cm gate | Verdict | Drop | Knee | Hip | Contact | Slip | CoM min | ZMP min | Final h | Fell |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| safe-6cm-r0p060 | safe_combo | FAIL | DEPTH_PENDING_6CM | 0.0455m | 0.362 | 0.104 | 1.00 | 0.015m | 0.0475m | 0.0393m | 0.7484m | never |
| safe-6cm-r0p070 | safe_combo | FAIL | DEPTH_PENDING_6CM | 0.0493m | 0.384 | 0.108 | 1.00 | 0.015m | 0.0430m | 0.0343m | 0.7486m | never |
| safe-6p5cm-r0p060 | safe_combo | FAIL | DEPTH_PENDING_6CM | 0.0474m | 0.372 | 0.108 | 1.00 | 0.016m | 0.0435m | 0.0351m | 0.7488m | never |
| soft-6p5cm-r0p075 | safe_combo | FAIL | DEPTH_PENDING_6CM | 0.0472m | 0.371 | 0.107 | 1.00 | 0.016m | 0.0435m | 0.0351m | 0.7488m | never |
| safe-8cm-r0p060-6gate | safe_combo | FAIL | FAIL_FALL | 1.5095m | 0.585 | 0.352 | 0.92 | 0.885m | -0.5682m | -0.5677m | -0.6467m | 5.36s |
| safe-8cm-r0p075-6gate | safe_combo | FAIL | FAIL_FALL | 1.4916m | 0.592 | 0.407 | 0.91 | 0.949m | -0.5864m | -0.5860m | -0.5527m | 5.24s |
| soft-8cm-r0p080-6gate | safe_combo | FAIL | FAIL_FALL | 1.5044m | 0.599 | 0.349 | 0.91 | 0.961m | -0.5834m | -0.5831m | -0.5963m | 5.30s |
| torque-6cm-r0p060-t20 | actuator_qfrc | FAIL | DEPTH_PENDING_6CM | 0.0432m | 0.340 | 0.097 | 1.00 | 0.032m | 0.0462m | -0.0164m | 0.7499m | never |
| torque-6p5cm-r0p060-t20 | actuator_qfrc | FAIL | DEPTH_PENDING_6CM | 0.0483m | 0.368 | 0.102 | 1.00 | 0.030m | 0.0395m | -0.0183m | 0.7495m | never |
| torque-6cm-r0p070-t30 | actuator_qfrc | FAIL | DEPTH_PENDING_6CM | 0.0425m | 0.337 | 0.099 | 1.00 | 0.038m | 0.0484m | -0.0067m | 0.7496m | never |
| torque-8cm-r0p060-t20-6gate | actuator_qfrc | FAIL | DEPTH_PENDING_6CM | 0.0581m | 0.419 | 0.187 | 1.00 | 0.024m | 0.0221m | -0.0288m | 0.7499m | never |
| torque-8cm-r0p065-t24-6gate | actuator_qfrc | PASS | PASS_RECOVERABLE_6CM_GATE | 0.0600m | 0.428 | 0.201 | 1.00 | 0.026m | 0.0199m | -0.0311m | 0.7524m | never |
| torque-8p5cm-r0p065-t24-6gate | actuator_qfrc | FAIL | FAIL_FALL | 0.3118m | 0.459 | 0.257 | 0.98 | 0.054m | -0.5115m | -0.4949m | 0.4432m | 5.98s |

Best recoverable run: {'attempt': 'torque-8cm-r0p065-t24-6gate', 'visible_drop': 0.060024889375652535, 'foot_contact_ratio': 1.0, 'foot_slip_distance': 0.02638058978508051, 'return_to_stand': True}
Best no-fall run: {'attempt': 'torque-8cm-r0p065-t24-6gate', 'visible_drop': 0.060024889375652535, 'transition_verdict': 'PASS_RECOVERABLE_6CM_GATE'}
Best depth run: {'attempt': 'safe-8cm-r0p060-6gate', 'visible_drop': 1.5095282598523339, 'fell_at': 5.36, 'transition_verdict': 'FAIL_FALL'}

This is an intermediate gate. M19 still requires exp29 8cm visible depth, knee/hip pose, native no-fall, browser replay, contact, stance, and return together.
