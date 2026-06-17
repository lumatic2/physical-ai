# G1 Phase Trajectory Summary

| Attempt | Verdict | Drop | Fell at | Final h | Contact | Slip | Support min | Max gain | Switches |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| stop-0p03-support0p030 | DEPTH_PENDING | 0.0311m | never | 0.7483m | 1.00 | 0.016m | 0.0201m | 0.34 | 2.14:return:target_drop, 2.62:stand:gain_zero |
| stop-0p05-support0p030 | FAIL_FALL | 1.5104m | 3.42s | -0.7410m | 0.84 | 0.868m | -0.5703m | 0.39 | 2.14:return:support_floor, 2.58:stand:gain_zero |
| stop-0p08-support0p030 | FAIL_FALL | 1.5171m | 3.20s | -0.7621m | 0.78 | 0.898m | -0.5694m | 0.40 | 2.0:return:support_floor, 2.38:stand:gain_zero |
| guard-0p08-support0p045 | DEPTH_PENDING | 0.0292m | never | 0.7484m | 1.00 | 0.016m | 0.0267m | 0.34 | 1.72:return:support_floor, 2.0:stand:gain_zero |
| fast-return-0p08 | FAIL_FALL | 1.5227m | 2.84s | -0.7570m | 0.87 | 0.674m | -0.5682m | 0.45 | 1.86:return:support_floor, 2.12:stand:gain_zero |
| low-policy-fast-return | FAIL_FALL | 1.5384m | 4.00s | -0.7372m | 0.89 | 0.928m | -0.6048m | 0.62 | 2.6:return:target_drop, 2.98:stand:gain_zero |

M19 remains open unless visible depth, no-fall, contact, stance, return, knee/hip pose, and browser replay gates pass together.
