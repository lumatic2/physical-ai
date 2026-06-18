# G1 Knee Contact Return Joint Optimizer Summary

| Rank | Attempt | Score | Visible gate | Verdict | Drop | Knee | Hip | Contact | Slip | Final h | Fell |
|---:|---|---:|---|---|---:|---:|---:|---:|---:|---:|---|
| 1 | baseline-exp87-return-heavy | 453.1 | FAIL | POSE_GATE_PENDING | 0.0947m | 0.430 | 0.370 | 0.87 | 0.106m | 0.6603m | never |
| 2 | knee12-soft-height | 3450.5 | FAIL | FAIL_FALL | 1.5146m | 0.526 | 0.362 | 0.83 | 0.366m | -0.3430m | 4.78s |
| 3 | knee10-tight-slip | 3481.7 | FAIL | FAIL_FALL | 1.5297m | 0.666 | 0.504 | 0.83 | 0.357m | -0.6480m | 4.16s |
| 4 | knee11-depth-cap14 | 3484.7 | FAIL | FAIL_FALL | 1.5242m | 0.492 | 0.298 | 0.88 | 0.369m | -0.3042m | 4.94s |
| 5 | knee10-long-recap | 3501.2 | FAIL | FAIL_FALL | 1.5286m | 0.467 | 0.363 | 0.90 | 0.364m | -0.4744m | 5.14s |
| 6 | knee09-contact560 | 3532.8 | FAIL | FAIL_FALL | 1.5220m | 0.436 | 0.319 | 0.90 | 0.361m | -0.5083m | 5.16s |
| 7 | knee11-contact600 | 3571.2 | FAIL | FAIL_FALL | 1.5191m | 0.438 | 0.356 | 0.89 | 0.366m | -0.5849m | 5.24s |
| 8 | knee08-contact-heavy | 3579.1 | FAIL | FAIL_FALL | 1.4984m | 0.429 | 0.304 | 0.92 | 0.352m | -0.7434m | 5.54s |
| 9 | knee09-early-return | 3659.1 | FAIL | FAIL_FALL | 1.3444m | 0.423 | 0.237 | 0.93 | 0.368m | -0.5894m | 5.62s |
| 10 | knee10-contact580 | 3993.5 | FAIL | FAIL_FALL | 1.5205m | 0.411 | 0.368 | 0.83 | 0.434m | -0.7421m | 5.40s |

Best optimizer run: {'attempt': 'baseline-exp87-return-heavy', 'optimizer_score': 453.11657633866656, 'visible_drop': 0.09467003417042408, 'max_knee_delta_rad': 0.43039242443664105, 'max_hip_pitch_delta_rad': 0.3698153379824039, 'visible_gap': {'drop_shortfall_m': 0.0, 'knee_shortfall_rad': 0.16960757556335893, 'hip_shortfall_rad': 0.0, 'slip_excess_m': 0.025636173947894372}, 'visible_verdict': 'POSE_GATE_PENDING', 'fell_at': None}
Best visible run: None
Best no-fall run: {'attempt': 'baseline-exp87-return-heavy', 'visible_drop': 0.09467003417042408, 'max_knee_delta_rad': 0.43039242443664105, 'max_hip_pitch_delta_rad': 0.3698153379824039, 'visible_gap': {'drop_shortfall_m': 0.0, 'knee_shortfall_rad': 0.16960757556335893, 'hip_shortfall_rad': 0.0, 'slip_excess_m': 0.025636173947894372}, 'visible_verdict': 'POSE_GATE_PENDING'}
Best depth run: {'attempt': 'knee10-tight-slip', 'visible_drop': 1.5296740784211451, 'fell_at': 4.16, 'visible_verdict': 'FAIL_FALL'}

M19 closes only when visible native and browser replay both pass.
