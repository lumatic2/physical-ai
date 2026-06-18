# G1 Three-Phase Recapture Stand Controller Summary

| Attempt | Visible gate | Verdict | Drop | Knee | Hip | Contact | Slip | Support min | ZMP min | Final h | Fell |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| safe-recap1p6-hip0p14 | FAIL | DEPTH_PENDING_8CM | 0.0507m | 0.373 | 0.182 | 0.98 | 0.052m | 0.0290m | -0.1069m | 0.7387m | never |
| guarded-depth7-hip0p14 | FAIL | FAIL_FALL | 1.5098m | 0.419 | 0.324 | 0.93 | 0.420m | -0.5933m | -0.6467m | -0.7548m | 5.52s |
| guarded-depth8-hip0p15 | FAIL | FAIL_FALL | 1.5002m | 0.428 | 0.370 | 0.92 | 0.389m | -0.5927m | -0.6726m | -0.7452m | 5.54s |
| guarded-depth9-hip0p16 | FAIL | FAIL_FALL | 1.5176m | 0.522 | 0.278 | 0.91 | 0.401m | -0.5988m | -0.6371m | -0.6225m | 5.24s |
| guarded-depth8-longrecap | FAIL | FAIL_FALL | 1.5261m | 0.517 | 0.349 | 0.88 | 0.410m | -0.6033m | -0.6458m | -0.4277m | 5.04s |

Best visible run: None
Best no-fall run: {'attempt': 'safe-recap1p6-hip0p14', 'visible_drop': 0.05069363971224816, 'max_knee_delta_rad': 0.37322139234805096, 'max_hip_pitch_delta_rad': 0.18242636690925823, 'visible_gap': {'drop_shortfall_m': 0.02930636028775184, 'knee_shortfall_rad': 0.22677860765194902, 'hip_shortfall_rad': 0.16757363309074175, 'slip_excess_m': 0.0}, 'visible_verdict': 'DEPTH_PENDING_8CM'}
Best depth run: {'attempt': 'guarded-depth8-longrecap', 'visible_drop': 1.5261389443277675, 'fell_at': 5.04, 'visible_verdict': 'FAIL_FALL'}

M19 closes only when visible native and browser replay both pass.
