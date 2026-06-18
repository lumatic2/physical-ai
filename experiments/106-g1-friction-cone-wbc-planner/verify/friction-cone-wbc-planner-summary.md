# G1 Friction-Cone-Aware WBC Planner Summary

| Rank | Attempt | Score | Gate | Verdict | Drop | Knee | Hip | Contact | Slip | Final h | Joint viol | Fell |
|---:|---|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | friction-knee-minimal-depth | 268.0 | FAIL | DEPTH_PENDING_8CM | 0.0520m | 0.383 | 0.204 | 1.00 | 0.016m | 0.7262m | 0.000 | never |
| 2 | friction-tight-light | 3049.0 | FAIL | FAIL_FALL | 1.2235m | 0.463 | 0.324 | 0.94 | 0.277m | -0.4685m | 0.255 | 5.66s |
| 3 | friction-braked-knee-low-slip | 3739.0 | FAIL | FAIL_FALL | 1.5241m | 0.414 | 0.374 | 0.88 | 0.377m | -0.7119m | 0.190 | 5.38s |
| 4 | friction-tight-medium | 3742.3 | FAIL | FAIL_FALL | 1.5221m | 0.414 | 0.417 | 0.90 | 0.375m | -0.7212m | 0.203 | 5.40s |
| 5 | friction-braked-knee-return | 3824.0 | FAIL | FAIL_FALL | 1.5305m | 0.478 | 0.427 | 0.88 | 0.394m | -0.7121m | 0.180 | 5.38s |

Best friction run: {'attempt': 'friction-knee-minimal-depth', 'friction_score': 267.9614072414299, 'visible_drop': 0.05198772714581834, 'max_knee_delta_rad': 0.38281909097765765, 'max_hip_pitch_delta_rad': 0.2044383814544241, 'foot_contact_ratio': 1.0, 'foot_slip_distance': 0.01588244065608925, 'final_height': 0.7262067579482496, 'visible_gap': {'drop_shortfall_m': 0.02801227285418166, 'knee_shortfall_rad': 0.21718090902234233, 'hip_shortfall_rad': 0.14556161854557587, 'slip_excess_m': 0.0}, 'visible_verdict': 'DEPTH_PENDING_8CM', 'fell_at': None}
Best visible run: None
Best no-fall run: {'attempt': 'friction-knee-minimal-depth', 'visible_drop': 0.05198772714581834, 'max_knee_delta_rad': 0.38281909097765765, 'max_hip_pitch_delta_rad': 0.2044383814544241, 'visible_gap': {'drop_shortfall_m': 0.02801227285418166, 'knee_shortfall_rad': 0.21718090902234233, 'hip_shortfall_rad': 0.14556161854557587, 'slip_excess_m': 0.0}, 'visible_verdict': 'DEPTH_PENDING_8CM'}

M19 closes only when native exp29 visible gate and browser replay both pass.
