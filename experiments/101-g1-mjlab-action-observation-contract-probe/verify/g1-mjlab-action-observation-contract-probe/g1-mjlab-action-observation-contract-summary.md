# G1 mjlab Action/Observation Contract Probe Summary

| Attempt | Verdict | Drop | Knee | Hip | Slip | Fell | Action range | Target range | Obs max |
|---|---|---:|---:|---:|---:|---|---|---|---:|
| run-policy-baseline | FAIL_FALL | 4867.261m | 6124.635 | 63684.124 | 22.843m | 0.24s | -2332887.25..1569893.62 | -2332887.25..1569893.62 | 47811868.00 |
| mjlab-obs-direct-zero | FAIL_FALL | 122.707m | 815.000 | 1319.120 | 2.875m | 0.32s | -153986.00..122235.44 | -153986.00..122235.44 | 5347656.50 |
| mjlab-obs-scaled-zero | FAIL_FALL | 1.565m | 6.447 | 52.135 | 1.072m | 0.46s | -2290.23..1531.73 | -1004.44..453.34 | 34666.80 |
| mjlab-obs-scaled-knees-bent | FAIL_FALL | 1.576m | 10797.212 | 1212.632 | 20.393m | 0.36s | -587944.69..439764.66 | -257859.00..192870.61 | 18065534.00 |

Verdict: **FAIL_VISIBLE_NATIVE**
