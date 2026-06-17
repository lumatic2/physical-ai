# G1 Reference-Offset Action Probe Summary

| Attempt | Verdict | Drop | Fell at | Contact | Final height | Support min | Slip |
|---|---|---:|---:|---:|---:|---:|---:|
| default-stage-0p74 | DEPTH_PENDING | 0.0052m | never | 1.00 | 0.7498m | 0.0737m | 0.012m |
| ramp-stage-0p74-gain-0p25 | DEPTH_PENDING | 0.0075m | never | 1.00 | 0.7496m | 0.0686m | 0.012m |
| ramp-stage-0p74-gain-0p50 | DEPTH_PENDING | 0.0105m | never | 1.00 | 0.7497m | 0.0602m | 0.012m |
| ramp-stage-0p67-gain-0p50 | DEPTH_PENDING | 0.0105m | never | 1.00 | 0.7497m | 0.0602m | 0.012m |
| ref-stage-0p74-resid-0p25 | FAIL_FALL | 1.5316m | 1.40s | 0.91 | -0.7545m | -0.6302m | 0.987m |
| ref-stage-0p67-reference-only | FAIL_FALL | 1.5211m | 1.24s | 0.92 | -0.7488m | -0.6489m | 0.993m |

M19 closes only when visible depth, no-fall, contact, stance, return, and browser replay gates pass together.
