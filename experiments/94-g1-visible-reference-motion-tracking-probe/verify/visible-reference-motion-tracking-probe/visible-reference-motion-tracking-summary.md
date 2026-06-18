# G1 Visible Reference Motion Tracking Probe Summary

| Rank | Attempt | Score | Visible gate | Verdict | Drop | Knee | Hip | Contact | Slip | Final h | Fell |
|---:|---|---:|---|---|---:|---:|---:|---:|---:|---:|---|
| 1 | stabilizer-reference-055-contact | 435.3 | FAIL | POSE_GATE_PENDING | 0.2552m | 0.401 | 0.374 | 0.99 | 0.046m | 0.4998m | never |
| 2 | release-reference-050 | 701.5 | FAIL | DEPTH_PENDING_8CM | 0.0328m | 0.276 | 0.205 | 1.00 | 0.024m | 0.7503m | never |
| 3 | knee-priority-reference-045 | 741.3 | FAIL | DEPTH_PENDING_8CM | 0.0311m | 0.253 | 0.195 | 1.00 | 0.023m | 0.7480m | never |
| 4 | stabilizer-reference-040-contact | 803.9 | FAIL | DEPTH_PENDING_8CM | 0.0285m | 0.238 | 0.154 | 1.00 | 0.007m | 0.7473m | never |
| 5 | stabilizer-reference-025 | 971.3 | FAIL | DEPTH_PENDING_8CM | 0.0191m | 0.181 | 0.081 | 1.00 | 0.007m | 0.7471m | never |
| 6 | reference-open-loop | 6573.8 | FAIL | FAIL_FALL | 1.5192m | 0.516 | 0.363 | 0.91 | 0.984m | -0.7495m | 1.26s |

Static reference: {'description': 'Static visible reference target before dynamics tracking.', 'start_height': 0.755, 'reference_height': 0.665, 'intended_base_drop_m': 0.08999999999999997, 'foot_site_z_error_m': 0.008193408284751007, 'foot_site_xy_error_m': 0.03799317383243158, 'target_knee_delta_rad': 0.640000015258789, 'target_hip_pitch_delta_rad': 0.38000003147125244, 'foot_sites_start': [[-0.0014175158435599082, 0.118506455, 0.03330197040558823], [-0.0014175158435599082, -0.118506455, 0.03330197040558823]], 'foot_sites_reference': [[0.03657565694355529, 0.11851536050092269, 0.04149537869033924], [0.03657565694515907, -0.1185153604987369, 0.04149537869033351]]}
Best optimizer run: {'attempt': 'stabilizer-reference-055-contact', 'optimizer_score': 435.2758755086937, 'visible_drop': 0.2551714361525631, 'max_knee_delta_rad': 0.4014901333835425, 'max_hip_pitch_delta_rad': 0.3742165580003563, 'visible_gap': {'drop_shortfall_m': 0.0, 'knee_shortfall_rad': 0.19850986661645748, 'hip_shortfall_rad': 0.0, 'slip_excess_m': 0.0, 'contact_shortfall': 0.0}, 'visible_verdict': 'POSE_GATE_PENDING', 'fell_at': None}
Best no-fall run: {'attempt': 'stabilizer-reference-055-contact', 'optimizer_score': 435.2758755086937, 'visible_drop': 0.2551714361525631, 'max_knee_delta_rad': 0.4014901333835425, 'max_hip_pitch_delta_rad': 0.3742165580003563, 'visible_gap': {'drop_shortfall_m': 0.0, 'knee_shortfall_rad': 0.19850986661645748, 'hip_shortfall_rad': 0.0, 'slip_excess_m': 0.0, 'contact_shortfall': 0.0}, 'visible_verdict': 'POSE_GATE_PENDING'}

M19 closes only when visible native and browser replay both pass.
