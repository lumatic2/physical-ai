# G1 CoM/ZMP Feedback Probe Summary

| Attempt | Verdict | Source | Drop | Knee | Hip | Contact | Slip | CoM min | ZMP min | Final h | Fell |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| baseline-no-feedback | FAIL_FALL | com | 1.5072m | 0.616 | 0.550 | 0.83 | 0.885m | -0.5699m | -0.5721m | -0.7522m | 4.56s |
| com-feedback-a | DEPTH_PENDING | com | 0.0278m | 0.250 | 0.076 | 1.00 | 0.015m | 0.0604m | 0.0525m | 0.7484m | never |
| com-feedback-a-blend0p50 | DEPTH_PENDING | com | 0.0473m | 0.368 | 0.096 | 1.00 | 0.017m | 0.0292m | 0.0184m | 0.7491m | never |
| com-feedback-a-blend0p60-slow | FAIL_FALL | com | 1.5068m | 0.590 | 0.342 | 0.91 | 0.945m | -0.5718m | -0.5733m | -0.7310m | 5.44s |
| com-feedback-a-blend0p70-slow | FAIL_FALL | com | 1.4952m | 0.618 | 0.431 | 0.91 | 0.938m | -0.5803m | -0.5799m | -0.6146m | 5.34s |
| com-feedback-a-blend0p85-slow | FAIL_FALL | com | 1.1582m | 0.582 | 0.362 | 0.93 | 0.425m | -0.5693m | -0.5693m | -0.4032m | 5.72s |
| com-feedback-b | FAIL_FALL | com | 1.5238m | 0.553 | 0.668 | 0.87 | 0.828m | -0.5950m | -0.5957m | -0.7540m | 2.84s |
| zmp-feedback-a | DEPTH_PENDING | zmp | 0.0224m | 0.213 | 0.061 | 1.00 | 0.015m | 0.0664m | 0.0437m | 0.7485m | never |
| zmp-feedback-b | FAIL_FALL | zmp | 1.5231m | 0.638 | 0.709 | 0.80 | 0.922m | -0.5910m | -0.5921m | -0.7604m | 3.14s |

Best no-fall run: {'attempt': 'com-feedback-a-blend0p50', 'visible_drop': 0.0472941287992521, 'min_support_margin': 0.029162485318111164, 'min_zmp_margin': 0.01844650046763841, 'return_to_stand': True}
Best depth run: {'attempt': 'com-feedback-b', 'visible_drop': 1.5237628637609513, 'fell_at': 2.84, 'min_support_margin': -0.5949978182586321, 'min_zmp_margin': -0.595725712663862}

M19 closes only when visible depth, knee/hip pose, no-fall, contact, stance, return, and browser replay gates pass together.
