# G1 Return Phase Support/ZMP Clamp Summary

| Attempt | 7cm gate | Verdict | Drop | Contact | Slip | CoM min | ZMP min | Final h | Clamp | Fell |
|---|---|---|---:|---:|---:|---:|---:|---:|---|---|
| release-8p5cm-r0p068-t26-rate0p72 | FAIL | FAIL_FALL | 1.5130m | 0.90 | 0.938m | -0.5715m | -0.5721m | -0.7292m | release:8,clamped:36,panic_release:121,descend:235 | 6.02s |
| release-8p5cm-r0p070-t28-rate0p90 | FAIL | FAIL_FALL | 1.5132m | 0.89 | 0.922m | -0.5711m | -0.5735m | -0.7567m | release:2,clamped:42,panic_release:121,descend:235 | 5.74s |
| release-8p3cm-r0p070-t28-rate0p90 | FAIL | FAIL_FALL | 1.5136m | 0.90 | 0.928m | -0.5732m | -0.5745m | -0.7406m | release:7,clamped:51,panic_release:122,descend:220 | 5.58s |
| release-8p2cm-r0p068-t26-rate1p10 | FAIL | FAIL_FALL | 1.5130m | 0.90 | 0.920m | -0.5724m | -0.5722m | -0.7259m | release:12,clamped:42,panic_release:126,descend:220 | 6.02s |
| release-8p0cm-r0p070-t28-rate1p20 | FAIL | FAIL_FALL | 1.5117m | 0.90 | 0.906m | -0.5756m | -0.5759m | -0.7177m | release:10,clamped:60,panic_release:120,descend:210 | 5.36s |

Best recoverable run: None
Best no-fall run: None
Best depth run: {'attempt': 'release-8p3cm-r0p070-t28-rate0p90', 'visible_drop': 1.5135724133851376, 'fell_at': 5.58, 'transition_verdict': 'FAIL_FALL'}

This is still an intermediate 7cm corridor gate, not the full M19 exp29 8cm native/browser gate.
