# G1 Foot-Contact-Aware Height Controller Summary

| Attempt | Verdict | Drop | Knee | Hip | Contact | Slip | Final h | Max blend | Fell |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| drop0p08-blend0p25-adapt0p08-policy1p0 | DEPTH_PENDING | 0.0212m | 0.201 | 0.119 | 1.00 | 0.013m | 0.7483m | 0.230 | never |
| drop0p08-blend0p35-adapt0p10-policy1p0 | DEPTH_PENDING | 0.0264m | 0.222 | 0.136 | 1.00 | 0.014m | 0.7485m | 0.286 | never |
| drop0p10-blend0p35-adapt0p10-policy1p0 | FAIL_FALL | 1.5049m | 0.614 | 0.549 | 0.84 | 0.896m | -0.7347m | 0.262 | 4.38s |
| drop0p12-blend0p45-adapt0p14-policy1p0 | FAIL_FALL | 1.5094m | 0.600 | 0.530 | 0.87 | 0.911m | -0.7441m | 0.270 | 3.32s |
| drop0p08-blend0p45-adapt0p16-policy0p15 | FAIL_FALL | 1.5353m | 0.601 | 0.198 | 0.92 | 1.017m | -0.7572m | 0.084 | 1.32s |

M19 closes only when visible depth, knee/hip pose, no-fall, contact, stance, return, and browser replay gates pass together.
