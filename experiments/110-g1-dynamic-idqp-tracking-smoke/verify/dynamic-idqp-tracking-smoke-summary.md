# G1 Dynamic ID-QP Tracking Smoke Summary

| Rank | Attempt | Score | Verdict | Drop | Knee | Hip | Contact | Slip | Return | Fall |
|---:|---|---:|---|---:|---:|---:|---:|---:|---|---|
| 1 | static-full-contact-heavy | 2612.9 | FAIL_FALL | 1.5104m | 0.650 | 0.484 | 0.92 | 0.527m | False | 1.48s |
| 2 | static-full-joint-heavy | 2770.5 | FAIL_FALL | 1.5105m | 0.600 | 0.479 | 0.91 | 0.576m | False | 1.60s |
| 3 | static-full-slow-balanced | 2814.3 | FAIL_FALL | 1.5096m | 0.602 | 0.482 | 0.94 | 0.589m | False | 1.46s |
| 4 | static-min-conservative | 2936.4 | FAIL_FALL | 1.5096m | 0.530 | 0.446 | 0.91 | 0.617m | False | 1.42s |
| 5 | static-full-very-slow | 3024.9 | FAIL_FALL | 1.5104m | 0.573 | 0.398 | 0.93 | 0.650m | False | 1.44s |

Best dynamic ID-QP smoke run: {'attempt': 'static-full-contact-heavy', 'visible_verdict': 'FAIL_FALL', 'visible_drop': 1.5103823488809955, 'max_knee_delta_rad': 0.6501981696635879, 'max_hip_pitch_delta_rad': 0.4841602414395883, 'foot_contact_ratio': 0.92, 'foot_slip_distance': 0.5270367619527427, 'return_to_stand': False, 'fell_at': 1.48, 'dynamic_idqp_score': 2612.8694763464136}
Best no-fall run: None
Best visible geometry run: {'attempt': 'static-full-contact-heavy', 'visible_verdict': 'FAIL_FALL', 'visible_drop': 1.5103823488809955, 'max_knee_delta_rad': 0.6501981696635879, 'max_hip_pitch_delta_rad': 0.4841602414395883, 'foot_contact_ratio': 0.92, 'foot_slip_distance': 0.5270367619527427, 'return_to_stand': False, 'fell_at': 1.48, 'dynamic_idqp_score': 2612.8694763464136}

M19 closes only if native exp29 visible gate and browser replay both pass.
