# G1 WBC/MPC In-Loop Reference Tracker Summary

| Rank | Attempt | Score | Verdict | Drop | Knee | Hip | Contact | Slip | Final h | Fall |
|---:|---|---:|---|---:|---:|---:|---:|---:|---:|---|
| 1 | mpc-return-biased-visible | 202.2 | POSE_GATE_PENDING | 0.2609m | 0.442 | 0.216 | 1.00 | 0.040m | 0.4941m | never |
| 2 | mpc-knee-contact-return | 1193.9 | FAIL_FALL | 0.3760m | 0.413 | 0.401 | 0.92 | 0.091m | 0.3790m | 5.96s |
| 3 | mpc-braked-8cm-three-primitive | 2251.2 | FAIL_FALL | 1.5287m | 0.552 | 0.349 | 0.95 | 0.357m | -0.3224m | 4.96s |

Best MPC run: {'attempt': 'mpc-return-biased-visible', 'mpc_visible_score': 202.16015803930662, 'visible_drop': 0.26093882075602765, 'max_knee_delta_rad': 0.4421186367752237, 'max_hip_pitch_delta_rad': 0.21602445327539038, 'foot_contact_ratio': 0.9966666666666667, 'foot_slip_distance': 0.040374875058744035, 'visible_verdict': 'POSE_GATE_PENDING', 'fell_at': None}
Best visible run: {'attempt': 'mpc-braked-8cm-three-primitive', 'visible_drop': 1.5287358980702233, 'max_knee_delta_rad': 0.5523352423342043, 'max_hip_pitch_delta_rad': 0.34926747447487433, 'foot_contact_ratio': 0.9533333333333334, 'foot_slip_distance': 0.35661455231830447, 'visible_verdict': 'FAIL_FALL', 'fell_at': 4.96}

Browser replay is attempted only after native exp29 visible gate passes.
