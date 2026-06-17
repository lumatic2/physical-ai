# G1 Safe-combo Residual Curriculum Summary

| Attempt | Verdict | Source | Filter | Drop | Knee | Hip | Contact | Slip | CoM min | ZMP min | Final h | Fell |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| teacher-0p08 | DEPTH_PENDING | com+none | none | 0.0473m | 0.368 | 0.096 | 1.00 | 0.017m | 0.0292m | 0.0184m | 0.7491m | never |
| safe-combo-0p08-r0p06 | DEPTH_PENDING | com+safe_combo | none | 0.0573m | 0.426 | 0.123 | 1.00 | 0.019m | 0.0182m | 0.0078m | 0.7520m | never |
| safe-combo-0p08-r0p09 | FAIL_FALL | com+safe_combo | none | 0.6454m | 0.532 | 0.346 | 0.95 | 0.160m | -0.5740m | -0.5739m | 0.1096m | 5.86s |
| safe-combo-0p10-r0p06 | FAIL_FALL | com+safe_combo | none | 1.5021m | 0.619 | 0.450 | 0.83 | 0.961m | -0.5809m | -0.5799m | -0.7321m | 4.54s |
| safe-combo-0p10-r0p09 | FAIL_FALL | com+safe_combo | none | 1.5077m | 0.617 | 0.425 | 0.87 | 0.949m | -0.5814m | -0.5810m | -0.7320m | 4.48s |
| soft-combo-0p10-r0p09 | FAIL_FALL | com+safe_combo | soft | 1.5027m | 0.617 | 0.447 | 0.82 | 0.975m | -0.5814m | -0.5809m | -0.7428m | 4.52s |
| zmp-hold-combo-0p12-r0p10 | FAIL_FALL | com+safe_combo | zmp_hold | 1.4968m | 0.598 | 0.409 | 0.86 | 0.916m | -0.5808m | -0.5803m | -0.7161m | 4.82s |

Best no-fall run: {'attempt': 'safe-combo-0p08-r0p06', 'visible_drop': 0.05733169862327969, 'min_support_margin': 0.018221812540051507, 'min_zmp_margin': 0.007790800765338682, 'return_to_stand': True}
Best depth run: {'attempt': 'safe-combo-0p10-r0p09', 'visible_drop': 1.5076803416165303, 'fell_at': 4.48, 'min_support_margin': -0.5814047292516835, 'min_zmp_margin': -0.5809723442942187}

M19 closes only when visible depth, knee/hip pose, no-fall, contact, stance, return, and browser replay gates pass together.
