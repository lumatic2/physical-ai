# G1 Pose-Biased Multi-Step WBC Projection Summary

| Attempt | Visible gate | Verdict | Drop | Knee | Hip | Contact | Slip | Support min | ZMP min | Final h | Fell |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| pose-h4-k0p06-h0p04 | FAIL | POSE_GATE_PENDING | 0.1260m | 0.517 | 0.133 | 1.00 | 0.027m | -0.1652m | -0.0649m | 0.6290m | never |
| pose-h4-k0p10-h0p06 | FAIL | POSE_GATE_PENDING | 0.1845m | 0.509 | 0.128 | 0.98 | 0.045m | -0.2605m | -0.0808m | 0.5705m | never |
| pose-h4-k0p14-h0p08 | FAIL | FAIL_FALL | 1.5303m | 0.505 | 0.329 | 0.89 | 0.402m | -0.5895m | -0.6426m | -0.7155m | 2.92s |
| pose-return-h4-k0p10-h0p06 | FAIL | POSE_GATE_PENDING | 0.1261m | 0.471 | 0.134 | 0.99 | 0.041m | -0.1955m | -0.0744m | 0.6289m | never |
| hip-dominant-h4-k0p08-h0p14 | FAIL | FAIL_FALL | 0.9454m | 0.702 | 0.360 | 0.95 | 0.199m | -0.6003m | -0.6230m | -0.1904m | 5.74s |
| hip-dominant-h4-k0p10-h0p18 | FAIL | POSE_GATE_PENDING | 0.2843m | 0.631 | 0.198 | 0.98 | 0.033m | -0.4503m | -0.3786m | 0.4707m | never |

Best visible run: None
Best no-fall run: {'attempt': 'hip-dominant-h4-k0p10-h0p18', 'visible_drop': 0.2842801292708207, 'max_knee_delta_rad': 0.6309984714402663, 'max_hip_pitch_delta_rad': 0.198415102645552, 'visible_gap': {'drop_shortfall_m': 0.0, 'knee_shortfall_rad': 0.0, 'hip_shortfall_rad': 0.15158489735444797, 'slip_excess_m': 0.0}, 'visible_verdict': 'POSE_GATE_PENDING'}
Best depth run: {'attempt': 'pose-h4-k0p14-h0p08', 'visible_drop': 1.530343620856903, 'fell_at': 2.92, 'visible_verdict': 'FAIL_FALL'}

M19 closes only when visible native and browser replay both pass.
