# G1 Qfrc Stance Preload Wrapper Summary

| Rank | Attempt | Score | Visible gate | Verdict | Drop | Knee | Hip | Contact | Slip | Final h | Fell |
|---:|---|---:|---|---|---:|---:|---:|---:|---:|---:|---|
| 1 | preload35-contact | 252.4 | FAIL | POSE_GATE_PENDING | 0.0980m | 0.427 | 0.436 | 0.93 | 0.097m | 0.6570m | never |
| 2 | preload35-knee09 | 267.9 | FAIL | DEPTH_PENDING_8CM | 0.0764m | 0.430 | 0.387 | 0.91 | 0.105m | 0.6786m | never |
| 3 | baseline-exp87-return-heavy | 277.5 | FAIL | POSE_GATE_PENDING | 0.0947m | 0.430 | 0.370 | 0.87 | 0.106m | 0.6603m | never |
| 4 | preload20-return-heavy | 305.2 | FAIL | POSE_GATE_PENDING | 0.1102m | 0.435 | 0.387 | 0.89 | 0.122m | 0.6448m | never |
| 5 | preload50-soft-depth | 311.3 | FAIL | POSE_GATE_PENDING | 0.2656m | 0.422 | 0.295 | 0.96 | 0.080m | 0.4894m | never |
| 6 | preload20-xy-strong | 2084.8 | FAIL | FAIL_FALL | 1.0449m | 0.432 | 0.339 | 0.89 | 0.343m | -0.2899m | 5.72s |

Best optimizer run: {'attempt': 'preload35-contact', 'optimizer_score': 252.42766638425402, 'visible_drop': 0.09803401695952385, 'max_knee_delta_rad': 0.42745255955664185, 'max_hip_pitch_delta_rad': 0.4358402481263364, 'visible_gap': {'drop_shortfall_m': 0.0, 'knee_shortfall_rad': 0.17254744044335812, 'hip_shortfall_rad': 0.0, 'slip_excess_m': 0.017190036859767596}, 'visible_verdict': 'POSE_GATE_PENDING', 'fell_at': None}
Best visible run: None
Best no-fall run: {'attempt': 'preload50-soft-depth', 'visible_drop': 0.26555443977944915, 'max_knee_delta_rad': 0.4221856799271193, 'max_hip_pitch_delta_rad': 0.29498009144894916, 'visible_gap': {'drop_shortfall_m': 0.0, 'knee_shortfall_rad': 0.17781432007288067, 'hip_shortfall_rad': 0.05501990855105082, 'slip_excess_m': 9.444421143783854e-06}, 'visible_verdict': 'POSE_GATE_PENDING'}
Best depth run: {'attempt': 'preload20-xy-strong', 'visible_drop': 1.0449321192297418, 'fell_at': 5.72, 'visible_verdict': 'FAIL_FALL'}

M19 closes only when visible native and browser replay both pass.
