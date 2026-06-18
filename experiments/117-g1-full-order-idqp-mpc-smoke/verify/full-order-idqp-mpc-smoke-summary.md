# G1 Full-Order ID-QP/MPC Smoke Summary

| Rank | Attempt | Score | Verdict | Drop | Knee | Hip | Contact | Slip | Final h | Fall |
|---:|---|---:|---|---:|---:|---:|---:|---:|---:|---|
| 1 | full-order-pose-push | 3157.2 | FAIL_FALL | 1.5064m | 0.644 | 0.446 | 0.95 | 0.594m | -0.7514m | 1.46s |
| 2 | full-order-balanced-visible | 3165.1 | FAIL_FALL | 1.5103m | 0.596 | 0.454 | 0.96 | 0.595m | -0.7553m | 1.40s |
| 3 | full-order-safety-first | 3473.3 | FAIL_FALL | 1.5105m | 0.605 | 0.402 | 0.95 | 0.691m | -0.7552m | 1.40s |

Best full-order MPC smoke run: {'attempt': 'full-order-pose-push', 'visible_verdict': 'FAIL_FALL', 'visible_drop': 1.50642528087277, 'max_knee_delta_rad': 0.6441427775942614, 'max_hip_pitch_delta_rad': 0.4463390320601787, 'foot_contact_ratio': 0.9533333333333334, 'foot_slip_distance': 0.5935716557555455, 'return_to_stand': False, 'fell_at': 1.46, 'full_order_mpc_score': 3157.2214429975324}
Best no-fall run: None

Browser replay is attempted only after native exp29 visible gate passes.
