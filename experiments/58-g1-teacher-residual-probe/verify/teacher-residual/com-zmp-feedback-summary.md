# G1 CoM/ZMP Feedback Probe Summary

| Attempt | Verdict | Source | Drop | Knee | Hip | Contact | Slip | CoM min | ZMP min | Final h | Fell |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| teacher-best | DEPTH_PENDING | com+none | 0.0473m | 0.368 | 0.096 | 1.00 | 0.017m | 0.0292m | 0.0184m | 0.7491m | never |
| teacher-knee-r0p04 | FAIL_FALL | com+knee_only | 1.5082m | 0.586 | 0.360 | 0.91 | 0.910m | -0.5715m | -0.5713m | -0.4977m | 5.14s |
| teacher-hip-knee-r0p06 | FAIL_FALL | com+hip_knee | 1.5092m | 0.587 | 0.350 | 0.87 | 0.892m | -0.5707m | -0.5728m | -0.7542m | 4.68s |
| teacher-counter-ankle-r0p06 | FAIL_FALL | com+counter_ankle | 1.5081m | 0.597 | 0.370 | 0.87 | 0.950m | -0.5683m | -0.5677m | -0.7058m | 4.86s |
| teacher-ankle-recenter-r0p05 | DEPTH_PENDING | com+ankle_recenter | 0.0464m | 0.366 | 0.108 | 1.00 | 0.016m | 0.0410m | 0.0307m | 0.7482m | never |

Best no-fall run: {'attempt': 'teacher-best', 'visible_drop': 0.0472941287992521, 'min_support_margin': 0.029162485318111164, 'min_zmp_margin': 0.01844650046763841, 'return_to_stand': True}
Best depth run: {'attempt': 'teacher-hip-knee-r0p06', 'visible_drop': 1.509167779306735, 'fell_at': 4.68, 'min_support_margin': -0.5707210456729427, 'min_zmp_margin': -0.5727708977346715}

M19 closes only when visible depth, knee/hip pose, no-fall, contact, stance, return, and browser replay gates pass together.
