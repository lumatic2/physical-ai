# G1 CoM-Feasible Trajectory Probe Summary

| Attempt | Verdict | Drop | Planned | Knee | Hip | Contact | Slip | CoM min | ZMP min | Final h | Fell |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| com-envelope-slow | FAIL_FALL | 1.5390m | 0.0496m | 0.618 | 0.368 | 0.86 | 0.916m | -0.6031m | -0.6063m | -0.7586m | 2.22s |
| com-envelope-torque | DEPTH_PENDING | 0.0424m | 0.0800m | 0.246 | 0.168 | 1.00 | 0.016m | -0.1696m | -0.0479m | 0.7126m | never |
| com-envelope-fast-torque | FAIL_FALL | 1.4982m | 0.0800m | 0.434 | 0.373 | 0.94 | 0.851m | -0.6124m | -0.6118m | -0.6543m | 5.36s |
| com-strong-center-torque | DEPTH_PENDING | 0.0551m | 0.0800m | 0.253 | 0.168 | 1.00 | 0.016m | -0.1807m | -0.0522m | 0.6999m | never |
| com-strong-stabilizer-torque | DEPTH_PENDING | 0.0167m | 0.0800m | 0.157 | 0.114 | 1.00 | 0.012m | 0.0474m | 0.0418m | 0.7456m | never |

Best no-fall run: {'attempt': 'com-strong-center-torque', 'visible_drop': 0.055083369700206, 'max_planned_drop': 0.08, 'max_knee_delta_rad': 0.25296419935573566, 'max_hip_pitch_delta_rad': 0.1679690540356058, 'min_support_margin': -0.1807200219646039, 'min_zmp_margin': -0.052209537958924426}
Best depth run: {'attempt': 'com-envelope-slow', 'visible_drop': 1.539006035062127, 'fell_at': 2.22, 'min_support_margin': -0.6030803929724344, 'min_zmp_margin': -0.6062925179819479}

M19 closes only when visible depth, knee/hip pose, no-fall, contact, stance, return, and browser replay gates pass together.
