# G1 Safe-basis Residual Filter Summary

| Attempt | Verdict | Source | Filter | Drop | Knee | Hip | Contact | Slip | CoM min | ZMP min | Final h | Fell |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| teacher-best | DEPTH_PENDING | com+none | none | 0.0473m | 0.368 | 0.096 | 1.00 | 0.017m | 0.0292m | 0.0184m | 0.7491m | never |
| unfiltered-safe-combo-r0p06 | DEPTH_PENDING | com+safe_combo | none | 0.0573m | 0.426 | 0.123 | 1.00 | 0.019m | 0.0182m | 0.0078m | 0.7520m | never |
| soft-safe-combo-r0p06 | DEPTH_PENDING | com+safe_combo | soft | 0.0550m | 0.413 | 0.117 | 1.00 | 0.018m | 0.0207m | 0.0090m | 0.7515m | never |
| zmp-hold-safe-combo-r0p08 | DEPTH_PENDING | com+safe_combo | zmp_hold | 0.0518m | 0.398 | 0.124 | 1.00 | 0.016m | 0.0307m | 0.0196m | 0.7483m | never |
| zmp-hold-counter-ankle-r0p08 | DEPTH_PENDING | com+counter_ankle | zmp_hold | 0.0489m | 0.378 | 0.120 | 1.00 | 0.017m | 0.0255m | 0.0155m | 0.7488m | never |
| soft-ankle-recenter-r0p08 | DEPTH_PENDING | com+ankle_recenter | soft | 0.0459m | 0.364 | 0.112 | 1.00 | 0.015m | 0.0443m | 0.0344m | 0.7482m | never |

Best no-fall run: {'attempt': 'unfiltered-safe-combo-r0p06', 'visible_drop': 0.05733169862327969, 'min_support_margin': 0.018221812540051507, 'min_zmp_margin': 0.007790800765338682, 'return_to_stand': True}
Best depth run: {'attempt': 'unfiltered-safe-combo-r0p06', 'visible_drop': 0.05733169862327969, 'fell_at': None, 'min_support_margin': 0.018221812540051507, 'min_zmp_margin': 0.007790800765338682}

M19 closes only when visible depth, knee/hip pose, no-fall, contact, stance, return, and browser replay gates pass together.
