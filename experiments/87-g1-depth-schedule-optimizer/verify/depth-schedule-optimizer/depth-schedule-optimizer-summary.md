# G1 Depth Schedule Optimizer Summary

| Rank | Attempt | Score | Visible gate | Verdict | Drop | Knee | Hip | Contact | Slip | Final h | Fell |
|---:|---|---:|---|---|---:|---:|---:|---:|---:|---:|---|
| 1 | sched-8cm-return-heavy | 277.5 | FAIL | POSE_GATE_PENDING | 0.0947m | 0.430 | 0.370 | 0.87 | 0.106m | 0.6603m | never |
| 2 | sched-8cm-tight-cap | 317.3 | FAIL | POSE_GATE_PENDING | 0.0826m | 0.431 | 0.262 | 0.87 | 0.111m | 0.6724m | never |
| 3 | teacher-safe-5cm | 361.2 | FAIL | DEPTH_PENDING_8CM | 0.0507m | 0.373 | 0.182 | 0.98 | 0.052m | 0.7387m | never |
| 4 | sched-8cm-low-residual | 427.1 | FAIL | POSE_GATE_PENDING | 0.2919m | 0.433 | 0.277 | 0.84 | 0.111m | 0.4631m | never |
| 5 | sched-6cm-support | 2106.7 | FAIL | FAIL_FALL | 1.0277m | 0.418 | 0.413 | 0.84 | 0.363m | -0.2727m | 5.74s |
| 6 | sched-7cm-long-recap | 2296.0 | FAIL | FAIL_FALL | 1.5112m | 0.591 | 0.400 | 0.83 | 0.429m | -0.5475m | 4.62s |
| 7 | sched-6p5-soft-pose | 2320.5 | FAIL | FAIL_FALL | 1.5297m | 0.503 | 0.437 | 0.84 | 0.421m | -0.7073m | 5.36s |
| 8 | sched-5p5-tight-return | 2326.4 | FAIL | FAIL_FALL | 1.5277m | 0.549 | 0.412 | 0.85 | 0.434m | -0.6751m | 5.34s |
| 9 | sched-8cm-pose | 2352.9 | FAIL | FAIL_FALL | 1.5137m | 0.428 | 0.313 | 0.93 | 0.411m | -0.7395m | 5.44s |
| 10 | sched-7cm-balanced | 2373.5 | FAIL | FAIL_FALL | 1.5098m | 0.419 | 0.324 | 0.93 | 0.420m | -0.7548m | 5.52s |

Best optimizer run: {'attempt': 'sched-8cm-return-heavy', 'optimizer_score': 277.5408602730674, 'visible_drop': 0.09467003417042408, 'max_knee_delta_rad': 0.43039242443664105, 'max_hip_pitch_delta_rad': 0.3698153379824039, 'visible_gap': {'drop_shortfall_m': 0.0, 'knee_shortfall_rad': 0.16960757556335893, 'hip_shortfall_rad': 0.0, 'slip_excess_m': 0.025636173947894372}, 'visible_verdict': 'POSE_GATE_PENDING', 'fell_at': None}
Best visible run: None
Best no-fall run: {'attempt': 'sched-8cm-low-residual', 'visible_drop': 0.291919857555521, 'max_knee_delta_rad': 0.4329495532144856, 'max_hip_pitch_delta_rad': 0.2769003558313376, 'visible_gap': {'drop_shortfall_m': 0.0, 'knee_shortfall_rad': 0.1670504467855144, 'hip_shortfall_rad': 0.07309964416866238, 'slip_excess_m': 0.03130689488642724}, 'visible_verdict': 'POSE_GATE_PENDING'}
Best depth run: {'attempt': 'sched-6p5-soft-pose', 'visible_drop': 1.5297208863505085, 'fell_at': 5.36, 'visible_verdict': 'FAIL_FALL'}

M19 closes only when visible native and browser replay both pass.
