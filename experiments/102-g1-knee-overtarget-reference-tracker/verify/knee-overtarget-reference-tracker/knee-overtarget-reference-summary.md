# G1 Knee Overtarget Reference Tracker Summary

| Rank | Attempt | Score | Gate | Verdict | Drop | Knee | Hip | Contact | Slip | Final h | Fell |
|---:|---|---:|---|---|---:|---:|---:|---:|---:|---:|---|
| 1 | baseline-exp94-k0p64 | 432.8 | FAIL | POSE_GATE_PENDING | 0.2581m | 0.404 | 0.372 | 1.00 | 0.046m | 0.4969m | never |
| 2 | k0p85-balanced | 530.7 | FAIL | DEPTH_PENDING_8CM | 0.0448m | 0.353 | 0.238 | 1.00 | 0.026m | 0.7503m | never |
| 3 | k1p05-cautious | 672.2 | FAIL | DEPTH_PENDING_8CM | 0.0389m | 0.305 | 0.162 | 1.00 | 0.016m | 0.7477m | never |
| 4 | k1p05-strong | 1879.2 | FAIL | FAIL_FALL | 0.6769m | 0.521 | 0.456 | 0.98 | 0.091m | 0.0781m | 5.86s |
| 5 | k1p10-hip0p42 | 3019.1 | FAIL | FAIL_FALL | 1.5278m | 0.527 | 0.438 | 0.96 | 0.309m | -0.5021m | 4.76s |
| 6 | k0p95-balanced | 3070.6 | FAIL | FAIL_FALL | 1.5280m | 0.512 | 0.423 | 0.96 | 0.316m | -0.2869m | 5.02s |
| 7 | k0p95-fast-return | 3118.4 | FAIL | FAIL_FALL | 1.5288m | 0.488 | 0.406 | 0.94 | 0.321m | -0.7323m | 4.42s |
| 8 | k1p10-fast-return | 3141.6 | FAIL | FAIL_FALL | 1.5289m | 0.473 | 0.389 | 0.96 | 0.322m | -0.6656m | 4.66s |
| 9 | k1p05-fast-return | 3157.8 | FAIL | FAIL_FALL | 1.5280m | 0.485 | 0.397 | 0.95 | 0.328m | -0.7635m | 4.48s |

Verdict: **FAIL_VISIBLE_8CM_GATE**

Best optimizer run: `baseline-exp94-k0p64`.
Best no-fall run: `baseline-exp94-k0p64`.

M19 closes only when native visible gate and browser replay both pass.
