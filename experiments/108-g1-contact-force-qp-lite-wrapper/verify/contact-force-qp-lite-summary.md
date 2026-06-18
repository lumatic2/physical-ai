# G1 Contact-Force QP-Lite Wrapper Summary

| Rank | Attempt | Score | Verdict | Drop | Knee | Hip | Contact | Slip | qfrc | Fall |
|---:|---|---:|---|---:|---:|---:|---:|---:|---:|---|
| 1 | qp-lite-friction-medium-braked | 195.4 | DEPTH_PENDING_8CM | 0.0749m | 0.382 | 0.210 | 1.00 | 0.042m | 84.9 | never |
| 2 | qp-lite-braked-knee-conservative | 224.2 | DEPTH_PENDING_8CM | 0.0592m | 0.420 | 0.218 | 1.00 | 0.026m | 102.8 | never |
| 3 | qp-lite-braked-8cm-balanced | 226.2 | DEPTH_PENDING_8CM | 0.0597m | 0.421 | 0.209 | 0.99 | 0.026m | 127.1 | never |
| 4 | qp-lite-friction-minimal-depth-push | 262.2 | DEPTH_PENDING_8CM | 0.0513m | 0.380 | 0.237 | 0.99 | 0.015m | 108.0 | never |
| 5 | qp-lite-friction-medium-visible-push | 1896.4 | FAIL_FALL | 1.5303m | 0.501 | 0.286 | 0.95 | 0.279m | 336.1 | 5.18s |
| 6 | qp-lite-friction-medium-depth-push | 1954.2 | FAIL_FALL | 1.5288m | 0.478 | 0.283 | 0.94 | 0.288m | 327.5 | 4.76s |
| 7 | qp-lite-braked-knee-pose-push | 1970.7 | FAIL_FALL | 1.5294m | 0.459 | 0.287 | 0.93 | 0.287m | 326.4 | 4.72s |

Best QP-lite run: {'attempt': 'qp-lite-friction-medium-braked', 'visible_drop': 0.07487052473343714, 'max_knee_delta_rad': 0.3818848890657591, 'max_hip_pitch_delta_rad': 0.2097819560622463, 'foot_contact_ratio': 0.9966666666666667, 'foot_slip_distance': 0.04192686619617468, 'visible_verdict': 'DEPTH_PENDING_8CM', 'fell_at': None}
Best visible run: {'attempt': 'qp-lite-friction-medium-visible-push', 'visible_drop': 1.5303346002036964, 'max_knee_delta_rad': 0.5014684292614597, 'max_hip_pitch_delta_rad': 0.28559122684829014, 'visible_verdict': 'FAIL_FALL', 'fell_at': 5.18}

M19 closes only with native exp29 visible gate plus browser replay.
