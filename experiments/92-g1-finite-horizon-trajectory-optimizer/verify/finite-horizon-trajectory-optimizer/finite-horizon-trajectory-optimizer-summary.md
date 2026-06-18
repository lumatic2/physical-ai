# G1 Finite-Horizon Trajectory Optimizer Summary

| Rank | Attempt | Score | Visible gate | Verdict | Drop | Knee | Hip | Contact | Slip | Final h | Fell |
|---:|---|---:|---|---|---:|---:|---:|---:|---:|---:|---|
| 1 | plan-8cm-knee-bias | 221.3 | FAIL | DEPTH_PENDING_8CM | 0.0514m | 0.378 | 0.204 | 1.00 | 0.018m | 0.7489m | never |
| 2 | plan-8cm-slip-tight | 222.1 | FAIL | DEPTH_PENDING_8CM | 0.0512m | 0.376 | 0.202 | 0.99 | 0.022m | 0.7434m | never |
| 3 | plan-9cm-terminal | 222.4 | FAIL | POSE_GATE_PENDING | 0.0930m | 0.421 | 0.368 | 0.93 | 0.085m | 0.6620m | never |
| 4 | baseline-exp90-contact | 273.5 | FAIL | POSE_GATE_PENDING | 0.1721m | 0.427 | 0.436 | 0.91 | 0.096m | 0.5829m | never |
| 5 | plan-terminal-micro-qfrc | 342.9 | FAIL | DEPTH_PENDING_8CM | 0.0541m | 0.395 | 0.181 | 0.99 | 0.025m | 0.7164m | never |
| 6 | plan-terminal-narrow-qfrc | 352.5 | FAIL | DEPTH_PENDING_8CM | 0.0505m | 0.380 | 0.192 | 1.00 | 0.017m | 0.7265m | never |
| 7 | plan-low-residual-long-horizon | 358.7 | FAIL | DEPTH_PENDING_8CM | 0.0511m | 0.378 | 0.179 | 1.00 | 0.025m | 0.7145m | never |
| 8 | plan-light-pose-qfrc | 2040.0 | FAIL | FAIL_FALL | 1.5301m | 0.660 | 0.344 | 0.94 | 0.340m | -0.3090m | 4.88s |

Best optimizer run: {'attempt': 'plan-8cm-knee-bias', 'optimizer_score': 221.29894045042028, 'visible_drop': 0.05142267900619335, 'max_knee_delta_rad': 0.3781609155232335, 'max_hip_pitch_delta_rad': 0.20387576134617597, 'visible_gap': {'drop_shortfall_m': 0.02857732099380665, 'knee_shortfall_rad': 0.22183908447676648, 'hip_shortfall_rad': 0.146124238653824, 'slip_excess_m': 0.0}, 'visible_verdict': 'DEPTH_PENDING_8CM', 'fell_at': None}
Best visible run: None
Best no-fall run: {'attempt': 'baseline-exp90-contact', 'visible_drop': 0.17208431792420775, 'max_knee_delta_rad': 0.42745255955664185, 'max_hip_pitch_delta_rad': 0.43584194664450654, 'visible_gap': {'drop_shortfall_m': 0.0, 'knee_shortfall_rad': 0.17254744044335812, 'hip_shortfall_rad': 0.0, 'slip_excess_m': 0.016297351122908407}, 'visible_verdict': 'POSE_GATE_PENDING'}
Best depth run: {'attempt': 'plan-light-pose-qfrc', 'visible_drop': 1.5300794412791285, 'fell_at': 4.88, 'visible_verdict': 'FAIL_FALL'}

M19 closes only when visible native and browser replay both pass.
