# G1 Foot-Fixed Action Projection Summary

| Source | Mode | Verdict | Drop | Knee | Hip | Contact | Slip | Final h | Fell |
|---|---|---|---:|---:|---:|---:|---:|---:|---|
| exp50 | none | POSE_GATE_PENDING | 0.1047m | 0.589 | 0.565 | 0.37 | 3.205m | 0.6503m | never |
| exp50 | soft-brake | FAIL_FALL | 1.5309m | 0.646 | 0.231 | 0.93 | 1.021m | -0.7455m | 1.96s |
| exp50 | default-brake | FAIL_FALL | 1.5335m | 0.598 | 0.199 | 0.92 | 0.990m | -0.7295m | 1.94s |
| exp50 | residual-clamp-only | FAIL_FALL | 1.5179m | 0.522 | 0.294 | 0.93 | 0.937m | -0.7479m | 1.24s |
| exp50 | ankle-lock-only | FAIL_FALL | 1.5195m | 0.516 | 0.281 | 0.90 | 0.934m | -0.7409m | 1.22s |
| exp50 | residual-clamp | FAIL_FALL | 1.5321m | 0.633 | 0.200 | 0.92 | 1.012m | -0.7479m | 1.24s |
| exp50 | ankle-lock | FAIL_FALL | 1.5306m | 0.625 | 0.187 | 0.93 | 1.002m | -0.7412m | 1.20s |
| exp46 | none | POSE_GATE_PENDING | 0.1506m | 0.588 | 0.556 | 0.36 | 3.126m | 0.6044m | never |
| exp46 | soft-brake | FAIL_FALL | 1.5325m | 0.654 | 0.248 | 0.92 | 1.009m | -0.7465m | 1.96s |
| exp46 | default-brake | FAIL_FALL | 1.5334m | 0.620 | 0.196 | 0.92 | 1.003m | -0.7292m | 1.94s |
| exp46 | residual-clamp-only | FAIL_FALL | 1.5221m | 0.498 | 0.286 | 0.91 | 0.953m | -0.7475m | 1.24s |
| exp46 | ankle-lock-only | FAIL_FALL | 1.5145m | 0.578 | 0.278 | 0.92 | 0.945m | -0.7403m | 1.22s |
| exp46 | residual-clamp | FAIL_FALL | 1.5325m | 0.626 | 0.195 | 0.91 | 1.009m | -0.7480m | 1.24s |
| exp46 | ankle-lock | FAIL_FALL | 1.5327m | 0.622 | 0.187 | 0.93 | 1.003m | -0.7421m | 1.20s |

M19 closes only when visible depth, knee/hip pose, no-fall, contact, stance, return, and browser replay gates pass together.
