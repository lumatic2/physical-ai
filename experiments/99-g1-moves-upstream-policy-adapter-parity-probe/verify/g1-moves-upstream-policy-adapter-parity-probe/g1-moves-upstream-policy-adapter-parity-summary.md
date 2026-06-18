# G1 Moves Upstream Policy Adapter Parity Probe Summary

| Attempt | Gate | Verdict | Drop | Knee | Hip | Contact | Slip | Fell | Action range | Obs max |
|---|---|---|---:|---:|---:|---:|---:|---|---|---:|
| upstream-exact-position | FAIL | FAIL_FALL | 117.892m | 666.114 | 3418.244 | 0.08 | 7.924m | 0.24s | -585051.88..1169843.12 | 18343466.00 |
| upstream-exact-position-smooth0p25 | FAIL | FAIL_FALL | 5.739m | 71.730 | 101.567 | 0.14 | 1.208m | 0.30s | -5426.99..5304.48 | 203755.59 |
| upstream-exact-torque-pd | FAIL | FAIL_FALL | 2082.724m | 1617.031 | 4125.482 | 0.07 | 6.237m | 0.26s | -1772875.00..1150729.25 | 27135424.00 |
| named-vel-position | FAIL | FAIL_FALL | 28.896m | 31.907 | 233.054 | 0.06 | 4.579m | 0.24s | -43531.12..42912.03 | 701410.25 |
| rowmajor-ablation | FAIL | FAIL_FALL | 626.332m | 885.538 | 5529.811 | 0.08 | 4.867m | 0.58s | -133480.81..118367.23 | 5800519.00 |
| torso-anchor-ablation | FAIL | FAIL_FALL | 438.134m | 1302.180 | 6688.976 | 0.06 | 4.042m | 0.24s | -129668.98..83949.15 | 2225772.75 |
| keyframe-default-position | FAIL | FAIL_FALL | 1.106m | 881.924 | 4001.699 | 0.09 | 1.877m | 0.60s | -284964.06..511987.56 | 8339152.00 |

Verdict: **FAIL_VISIBLE_NATIVE**

Browser replay is skipped unless a native visible gate passes.
