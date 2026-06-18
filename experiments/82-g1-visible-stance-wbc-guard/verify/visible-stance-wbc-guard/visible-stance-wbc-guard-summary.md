# G1 Visible Stance WBC Guard Summary

| Attempt | Visible gate | Verdict | Drop | Knee | Hip | Contact | Slip | Support min | ZMP min | Final h | Fell |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| visible-8cm-stance-force | FAIL | FAIL_FALL | 1.3904m | 0.604 | 0.356 | 0.93 | 0.392m | -0.6018m | -0.6211m | -0.6354m | 5.62s |
| visible-8p2cm-stance-force | FAIL | FAIL_FALL | 1.5040m | 0.662 | 0.355 | 0.92 | 0.377m | -0.5988m | -0.6223m | -0.6093m | 5.30s |
| visible-8cm-slow-guard | FAIL | DEPTH_PENDING_8CM | 0.0654m | 0.451 | 0.118 | 1.00 | 0.019m | 0.0020m | -0.0043m | 0.7082m | never |
| visible-8p5cm-depth-biased-guard | FAIL | FAIL_FALL | 1.5320m | 0.488 | 0.396 | 0.94 | 0.396m | -0.5932m | -0.6275m | -0.7292m | 2.66s |

Best visible run: None
Best no-fall run: {'attempt': 'visible-8cm-slow-guard', 'visible_drop': 0.06543707449716951, 'max_knee_delta_rad': 0.45147298243066136, 'max_hip_pitch_delta_rad': 0.11776066803264268, 'visible_gap': {'drop_shortfall_m': 0.01456292550283049, 'knee_shortfall_rad': 0.14852701756933862, 'hip_shortfall_rad': 0.2322393319673573, 'slip_excess_m': 0.0}, 'visible_verdict': 'DEPTH_PENDING_8CM'}
Best depth run: {'attempt': 'visible-8p5cm-depth-biased-guard', 'visible_drop': 1.5319619098281976, 'fell_at': 2.66, 'visible_verdict': 'FAIL_FALL'}

M19 closes only when visible native and browser replay both pass.
