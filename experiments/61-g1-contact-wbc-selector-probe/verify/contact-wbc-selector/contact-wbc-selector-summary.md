# G1 Contact-WBC Selector Probe Summary

| Attempt | Verdict | Drop | Knee | Hip | Contact | Slip | CoM min | ZMP min | Blend | Residual | Inv torque | Final h | Fell |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| stance-ultra-0p08-r0p06 | DEPTH_PENDING | 0.0082m | 0.104 | 0.022 | 1.00 | 0.015m | 0.0795m | 0.0525m | 0.02 | 0.060 | 44.3 | 0.7485m | never |
| stance-strict-0p08-r0p08 | FAIL_FALL | 1.5107m | 0.575 | 0.344 | 0.88 | 0.930m | -0.5697m | -0.5716m | 0.52 | 0.080 | 52.4 | -0.7138m | 4.12s |
| pose-balanced-0p08-r0p09 | FAIL_FALL | 1.5117m | 0.576 | 0.343 | 0.88 | 0.943m | -0.5697m | -0.5708m | 0.56 | 0.090 | 63.3 | -0.7340m | 4.00s |
| pose-push-0p08-r0p10 | FAIL_FALL | 1.5180m | 0.615 | 0.390 | 0.86 | 0.820m | -0.5723m | -0.5729m | 0.55 | 0.100 | 138.3 | -0.7520m | 3.84s |
| pose-balanced-0p10-r0p09 | FAIL_FALL | 1.5099m | 0.699 | 0.470 | 0.84 | 0.890m | -0.6058m | -0.6053m | 0.58 | 0.090 | 88.2 | -0.7460m | 3.48s |

Best no-fall run: {'attempt': 'stance-ultra-0p08-r0p06', 'visible_drop': 0.008181582433224421, 'max_knee_delta_rad': 0.10406176155732028, 'max_hip_pitch_delta_rad': 0.022351546142355405, 'min_support_margin': 0.07949920336105426, 'min_zmp_margin': 0.052479730116096295, 'return_to_stand': True}
Best depth run: {'attempt': 'pose-push-0p08-r0p10', 'visible_drop': 1.518034386147725, 'fell_at': 3.84, 'min_support_margin': -0.5723175264358684, 'min_zmp_margin': -0.5728982427238714}

M19 closes only when visible depth, knee/hip pose, no-fall, contact, stance, return, and browser replay gates pass together.
