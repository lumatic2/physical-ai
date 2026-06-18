# G1 Multi-Step Trajectory WBC Projection Summary

| Attempt | Visible gate | Verdict | Drop | Knee | Hip | Contact | Slip | Support min | ZMP min | Final h | Fell |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| h3-visible-8cm-balanced | FAIL | FAIL_FALL | 0.4961m | 0.602 | 0.290 | 0.97 | 0.068m | -0.5974m | -0.6157m | 0.2589m | 5.88s |
| h4-visible-8cm-slow | FAIL | POSE_GATE_PENDING | 0.0827m | 0.474 | 0.118 | 1.00 | 0.019m | -0.0533m | -0.0096m | 0.6723m | never |
| h5-visible-8p2cm-depth | FAIL | FAIL_FALL | 0.8698m | 0.631 | 0.341 | 0.94 | 0.154m | -0.5926m | -0.6152m | -0.1148m | 5.76s |
| h4-visible-8p2cm-guarded-return | FAIL | FAIL_FALL | 0.4702m | 0.546 | 0.228 | 0.96 | 0.050m | -0.5804m | -0.6000m | 0.2848m | 5.90s |

Best visible run: None
Best no-fall run: {'attempt': 'h4-visible-8cm-slow', 'visible_drop': 0.08267485013646325, 'max_knee_delta_rad': 0.4738053446919541, 'max_hip_pitch_delta_rad': 0.11823090329592773, 'visible_gap': {'drop_shortfall_m': 0.0, 'knee_shortfall_rad': 0.12619465530804586, 'hip_shortfall_rad': 0.23176909670407225, 'slip_excess_m': 0.0}, 'visible_verdict': 'POSE_GATE_PENDING'}
Best depth run: {'attempt': 'h5-visible-8p2cm-depth', 'visible_drop': 0.8697987381765107, 'fell_at': 5.76, 'visible_verdict': 'FAIL_FALL'}

M19 closes only when visible native and browser replay both pass.
