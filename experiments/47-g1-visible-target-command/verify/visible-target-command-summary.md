# G1 Visible Target Command Summary

| Attempt | Verdict | Drop | Fell at | Contact | Slip | Support min | Max command |
|---|---|---:|---:|---:|---:|---:|---:|
| additive-0p15 | DEPTH_PENDING | 0.0161m | never | 1.00 | 0.013m | 0.0570m | 0.15 |
| additive-0p25 | DEPTH_PENDING | 0.0232m | never | 1.00 | 0.015m | 0.0360m | 0.25 |
| additive-0p35 | FAIL_FALL | 1.5020m | 4.42s | 0.83 | 0.915m | -0.5634m | 0.35 |
| support-gated-0p35 | FAIL_FALL | 1.5070m | 4.68s | 0.87 | 0.900m | -0.5711m | 0.34 |
| support-slip-gated-0p45 | FAIL_FALL | 1.5103m | 4.04s | 0.87 | 0.866m | -0.5697m | 0.36 |
| support-gated-low-policy-0p45 | FAIL_FALL | 1.5371m | 2.84s | 0.85 | 0.903m | -0.5913m | 0.29 |

M19 closes only when visible depth, no-fall, contact, stance, return, and browser replay gates pass together.
