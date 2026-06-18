# G1 Contact-Constrained Pose Qfrc Wrapper Summary

| Rank | Attempt | Score | Visible gate | Verdict | Drop | Knee | Hip | Contact | Slip | Final h | Fell |
|---:|---|---:|---|---|---:|---:|---:|---:|---:|---:|---|
| 1 | poseqfrc-light | 221.0 | FAIL | POSE_GATE_PENDING | 0.0807m | 0.448 | 0.367 | 0.92 | 0.090m | 0.6743m | never |
| 2 | baseline-exp90-contact | 252.4 | FAIL | POSE_GATE_PENDING | 0.0980m | 0.427 | 0.436 | 0.93 | 0.097m | 0.6570m | never |
| 3 | poseqfrc-braked-8cm | 1403.8 | FAIL | FAIL_FALL | 0.4652m | 0.418 | 0.313 | 0.91 | 0.096m | 0.2898m | 5.92s |
| 4 | poseqfrc-strong-health | 2084.9 | FAIL | FAIL_FALL | 1.5297m | 0.546 | 0.348 | 0.92 | 0.345m | -0.4106m | 4.82s |
| 5 | poseqfrc-braked-return | 2088.2 | FAIL | FAIL_FALL | 1.5290m | 0.531 | 0.351 | 0.94 | 0.350m | -0.3467m | 5.00s |
| 6 | poseqfrc-medium | 2121.3 | FAIL | FAIL_FALL | 1.5280m | 0.524 | 0.312 | 0.91 | 0.353m | -0.3959m | 4.88s |
| 7 | poseqfrc-recapture-soft | 2137.8 | FAIL | FAIL_FALL | 1.5310m | 0.499 | 0.354 | 0.92 | 0.366m | -0.3858m | 4.88s |
| 8 | poseqfrc-slip-tight | 2162.6 | FAIL | FAIL_FALL | 1.5292m | 0.509 | 0.318 | 0.94 | 0.350m | -0.6019m | 5.32s |
| 9 | poseqfrc-braked-knee | 2316.0 | FAIL | FAIL_FALL | 1.5257m | 0.392 | 0.435 | 0.91 | 0.400m | -0.7663m | 5.50s |

Best optimizer run: {'attempt': 'poseqfrc-light', 'optimizer_score': 221.0036951339554, 'visible_drop': 0.0807139373360033, 'max_knee_delta_rad': 0.44832930803277593, 'max_hip_pitch_delta_rad': 0.36707892515260004, 'visible_gap': {'drop_shortfall_m': 0.0, 'knee_shortfall_rad': 0.15167069196722405, 'hip_shortfall_rad': 0.0, 'slip_excess_m': 0.009858566994359788}, 'visible_verdict': 'POSE_GATE_PENDING', 'fell_at': None}
Best visible run: None
Best no-fall run: {'attempt': 'baseline-exp90-contact', 'visible_drop': 0.09803401695952385, 'max_knee_delta_rad': 0.42745255955664185, 'max_hip_pitch_delta_rad': 0.4358402481263364, 'visible_gap': {'drop_shortfall_m': 0.0, 'knee_shortfall_rad': 0.17254744044335812, 'hip_shortfall_rad': 0.0, 'slip_excess_m': 0.017190036859767596}, 'visible_verdict': 'POSE_GATE_PENDING'}
Best depth run: {'attempt': 'poseqfrc-recapture-soft', 'visible_drop': 1.5309902931861363, 'fell_at': 4.88, 'visible_verdict': 'FAIL_FALL'}

M19 closes only when visible native and browser replay both pass.
