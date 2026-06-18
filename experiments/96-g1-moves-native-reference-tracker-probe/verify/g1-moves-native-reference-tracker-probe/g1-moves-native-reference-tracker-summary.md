# G1 Moves Native Reference Tracker Probe Summary

| Rank | Attempt | Score | Gate | Verdict | Drop | Knee | Hip | Contact | Slip | Ref err | Final h | Fell |
|---:|---|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | converted-pd-strong | 3469.7 | FAIL | FAIL_FALL | 1.5771m | 1.840 | 1.371 | 0.85 | 0.330m | 0.0775 | -0.5415m | 1.42s |
| 2 | converted-pd-medium | 3591.9 | FAIL | FAIL_FALL | 1.5669m | 1.228 | 0.988 | 0.87 | 0.353m | 0.1528 | -0.6590m | 1.42s |
| 3 | keyframe-joints-medium | 3813.8 | FAIL | FAIL_FALL | 1.5209m | 1.110 | 1.077 | 0.88 | 0.393m | 0.1469 | -0.6713m | 0.88s |
| 4 | converted-pd-weak | 4269.0 | FAIL | FAIL_FALL | 1.5750m | 1.158 | 0.672 | 0.88 | 0.473m | 0.2407 | -0.7154m | 1.12s |
| 5 | converted-open-loop | 5858.7 | FAIL | FAIL_FALL | 1.5830m | 1.821 | 1.494 | 0.60 | 0.741m | 0.1381 | -0.4775m | 1.20s |
| 6 | as-recorded-open-loop | 6560.1 | FAIL | FAIL_FALL | 1.5816m | 1.726 | 1.495 | 0.51 | 0.861m | 0.0746 | -0.5065m | 0.00s |

Best optimizer run: {'attempt': 'converted-pd-strong', 'optimizer_score': 3469.733801849142, 'visible_drop': 1.5771234264819247, 'max_knee_delta_rad': 1.840011767913577, 'max_hip_pitch_delta_rad': 1.3706658995643317, 'visible_verdict': 'FAIL_FALL', 'fell_at': 1.42, 'trajectory_out': 'experiments\\96-g1-moves-native-reference-tracker-probe\\verify\\g1-moves-native-reference-tracker-probe\\converted-pd-strong\\native_rollout_web_trajectory.json'}
Best visible run: None

M19 closes only when visible native and browser replay both pass.
