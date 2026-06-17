# G1 CoM-aware QP-lite Selector Summary

| Attempt | Verdict | Drop | Knee | Hip | Contact | Slip | CoM min | ZMP min | Blend | Fdbk | Force | Inv torque | Fell |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| balanced-0p08 | FAIL_FALL | 1.5154m | 0.419 | 0.445 | 0.93 | 0.801m | -0.6163m | -0.6295m | 0.70 | 1.00 | 3034.0 | 65.9 | 3.66s |
| feedback-fixed-0p08 | FAIL_FALL | 1.5199m | 0.520 | 0.317 | 0.93 | 0.853m | -0.5767m | -0.5839m | 0.55 | 1.00 | 2140.1 | 64.7 | 3.94s |
| depth-0p08 | FAIL_FALL | 1.5141m | 0.400 | 0.463 | 0.96 | 0.850m | -0.6077m | -0.6306m | 0.75 | 1.00 | 2638.6 | 205.3 | 3.16s |
| strict-0p10 | DEPTH_PENDING | 0.0332m | 0.280 | 0.200 | 1.00 | 0.019m | 0.0236m | -0.0166m | 0.70 | 1.00 | 859.4 | 36.0 | never |
| depth-0p10 | FAIL_FALL | 1.5180m | 0.460 | 0.492 | 0.98 | 0.764m | -0.6140m | -0.6375m | 0.85 | 1.30 | 2710.1 | 89.0 | 3.34s |
| depth-0p12 | FAIL_FALL | 1.5178m | 0.632 | 0.550 | 0.98 | 0.846m | -0.6120m | -0.6425m | 0.90 | 1.30 | 2441.2 | 214.1 | 3.34s |

Best no-fall run: {'attempt': 'strict-0p10', 'visible_drop': 0.03324879428712324, 'max_knee_delta_rad': 0.2803699957462443, 'max_hip_pitch_delta_rad': 0.20038883613175856, 'return_to_stand': True, 'foot_slip_distance': 0.019178062568727186}
Best depth run: {'attempt': 'feedback-fixed-0p08', 'visible_drop': 1.5198556640767256, 'fell_at': 3.94, 'foot_slip_distance': 0.8533600842066558}

M19 closes only when visible depth, knee/hip pose, no-fall, contact, stance, return, and browser replay gates pass together.
