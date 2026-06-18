# G1 Predictive Sampling Trajectory Search Summary

| Rank | Attempt | Score | Visible gate | Verdict | Drop | Knee | Hip | Contact | Slip | Final h | Fell |
|---:|---|---:|---|---|---:|---:|---:|---:|---:|---:|---|
| 1 | baseline-plan9-terminal | 439.5 | FAIL | POSE_GATE_PENDING | 0.0871m | 0.421 | 0.403 | 0.94 | 0.075m | 0.6679m | never |
| 2 | sample-09 | 455.9 | FAIL | DEPTH_PENDING_8CM | 0.0519m | 0.378 | 0.196 | 0.99 | 0.027m | 0.7520m | never |
| 3 | sample-12 | 460.1 | FAIL | DEPTH_PENDING_8CM | 0.0522m | 0.380 | 0.189 | 0.99 | 0.026m | 0.7601m | never |
| 4 | sample-08 | 463.7 | FAIL | DEPTH_PENDING_8CM | 0.0502m | 0.372 | 0.208 | 1.00 | 0.018m | 0.7506m | never |
| 5 | seed-sample15-visible-branch | 518.3 | FAIL | POSE_GATE_PENDING | 0.1073m | 0.423 | 0.395 | 0.94 | 0.094m | 0.6477m | never |
| 6 | sample-07 | 553.1 | FAIL | DEPTH_PENDING_8CM | 0.0617m | 0.425 | 0.256 | 0.97 | 0.075m | 0.7271m | never |
| 7 | sample-10 | 569.4 | FAIL | DEPTH_PENDING_8CM | 0.0629m | 0.420 | 0.384 | 0.95 | 0.090m | 0.6921m | never |
| 8 | sample-16 | 611.0 | FAIL | DEPTH_PENDING_8CM | 0.0598m | 0.422 | 0.187 | 0.99 | 0.029m | 0.7269m | never |
| 9 | sample-14 | 618.8 | FAIL | DEPTH_PENDING_8CM | 0.0590m | 0.422 | 0.184 | 0.99 | 0.028m | 0.7241m | never |
| 10 | sample-15 | 624.5 | FAIL | DEPTH_PENDING_8CM | 0.0563m | 0.413 | 0.209 | 1.00 | 0.016m | 0.7098m | never |
| 11 | sample-03 | 647.2 | FAIL | DEPTH_PENDING_8CM | 0.0552m | 0.404 | 0.202 | 1.00 | 0.017m | 0.7039m | never |
| 12 | sample-06 | 653.7 | FAIL | DEPTH_PENDING_8CM | 0.0558m | 0.402 | 0.181 | 1.00 | 0.025m | 0.7208m | never |
| 13 | sample-17 | 656.2 | FAIL | DEPTH_PENDING_8CM | 0.0550m | 0.397 | 0.190 | 1.00 | 0.021m | 0.7165m | never |
| 14 | sample-18 | 657.3 | FAIL | DEPTH_PENDING_8CM | 0.0550m | 0.395 | 0.193 | 0.99 | 0.033m | 0.7136m | never |
| 15 | sample-05 | 657.8 | FAIL | DEPTH_PENDING_8CM | 0.0547m | 0.396 | 0.191 | 1.00 | 0.020m | 0.7201m | never |
| 16 | sample-13 | 666.3 | FAIL | DEPTH_PENDING_8CM | 0.0519m | 0.382 | 0.215 | 1.00 | 0.015m | 0.7253m | never |
| 17 | sample-02 | 668.8 | FAIL | DEPTH_PENDING_8CM | 0.0511m | 0.377 | 0.215 | 1.00 | 0.016m | 0.7317m | never |
| 18 | sample-01 | 683.9 | FAIL | DEPTH_PENDING_8CM | 0.0518m | 0.380 | 0.183 | 1.00 | 0.023m | 0.7364m | never |
| 19 | sample-11 | 698.7 | FAIL | DEPTH_PENDING_8CM | 0.0507m | 0.380 | 0.188 | 1.00 | 0.020m | 0.7143m | never |
| 20 | sample-04 | 3327.2 | FAIL | FAIL_FALL | 1.5307m | 0.540 | 0.318 | 0.96 | 0.321m | -0.7094m | 5.44s |

Best optimizer run: {'attempt': 'baseline-plan9-terminal', 'optimizer_score': 439.4943527086485, 'visible_drop': 0.08705565158027107, 'max_knee_delta_rad': 0.4205253134615663, 'max_hip_pitch_delta_rad': 0.40305016500951135, 'visible_gap': {'drop_shortfall_m': 0.0, 'knee_shortfall_rad': 0.17947468653843368, 'hip_shortfall_rad': 0.0, 'slip_excess_m': 0.0}, 'visible_verdict': 'POSE_GATE_PENDING', 'fell_at': None}
Best visible run: None
Best no-fall run: {'attempt': 'seed-sample15-visible-branch', 'visible_drop': 0.10729392343828414, 'max_knee_delta_rad': 0.42296876315367893, 'max_hip_pitch_delta_rad': 0.39510898867417504, 'visible_gap': {'drop_shortfall_m': 0.0, 'knee_shortfall_rad': 0.17703123684632105, 'hip_shortfall_rad': 0.0, 'slip_excess_m': 0.014193713619651896}, 'visible_verdict': 'POSE_GATE_PENDING'}
Best depth run: {'attempt': 'sample-04', 'visible_drop': 1.5307100715536428, 'fell_at': 5.44, 'visible_verdict': 'FAIL_FALL'}

M19 closes only when visible native and browser replay both pass.
