# G1 QP-lite WBC Summary

| Attempt | Verdict | Drop | Fell at | Final height | Support min | Contact | Slip | Blend max | Normal max | LR imbalance | Inv torque |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| qplite-0p08-force-strict | DEPTH_PENDING | 0.0089m | never | 0.7489m | 0.0689m | 1.00 | 0.012m | 0.07 | 454.30 | 0.21 | 24.20 |
| qplite-0p08-depth-biased | DEPTH_PENDING | 0.0227m | never | 0.7499m | 0.0409m | 1.00 | 0.017m | 0.54 | 632.82 | 0.34 | 43.93 |
| qplite-0p12-force-strict | DEPTH_PENDING | 0.0269m | never | 0.7482m | 0.0500m | 0.99 | 0.029m | 0.63 | 856.93 | 1.00 | 43.25 |
| qplite-0p12-depth-biased | DEPTH_PENDING | 0.0386m | never | 0.7471m | 0.0184m | 1.00 | 0.021m | 0.64 | 798.36 | 1.00 | 55.83 |
| qplite-0p12-depth-aggressive | FAIL_FALL | 1.5186m | 2.34s | -0.6827m | -0.5986m | 0.98 | 0.823m | 1.00 | 4002.49 | 1.00 | 76.15 |
| qplite-0p16-depth-aggressive | FAIL_FALL | 1.5090m | 2.14s | -0.6448m | -0.5996m | 0.98 | 0.763m | 1.00 | 2523.93 | 1.00 | 78.10 |

M19 closes only when visible depth, no-fall, contact, stance, return, and browser replay gates pass together.
