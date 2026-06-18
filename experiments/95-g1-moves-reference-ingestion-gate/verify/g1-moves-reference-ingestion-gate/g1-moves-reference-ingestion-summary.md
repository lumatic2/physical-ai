# G1 Moves Reference Ingestion Gate Summary

Verdict: PASS_INGESTION_GATE
Selected clip: J_Dance4_Broadway (dance)
CSV: https://huggingface.co/datasets/exptech/g1-moves/resolve/main/dance/J_Dance4_Broadway/retarget/J_Dance4_Broadway.csv

| Rank | Clip | Category | Knee range | Hip pitch range | Knee max | Has policy | Score |
|---:|---|---|---:|---:|---:|---|---:|
| 1 | J_Dance4_Broadway | dance | 2.392 | 1.822 | 2.498 | True | 8.943 |
| 2 | J_Dance17_Shuffle | dance | 2.282 | 1.858 | 2.389 | True | 8.756 |
| 3 | J_ShortDance15_Nineties | dance | 2.154 | 1.861 | 2.277 | True | 8.374 |
| 4 | B_LongDance | dance | 2.137 | 2.040 | 2.244 | True | 8.354 |
| 5 | J_ShortDance16_JazzWalk | dance | 2.108 | 1.969 | 2.187 | True | 8.344 |
| 6 | J_Dance19_LetsGO | dance | 2.133 | 1.968 | 2.246 | True | 8.335 |
| 7 | J_Dance18_TikTok | dance | 2.141 | 1.822 | 2.211 | True | 8.205 |
| 8 | M_ShortMove13 | karate | 2.043 | 1.870 | 2.163 | True | 8.079 |

Best 6s window: {'start_frame': 360, 'end_frame': 720, 'duration_s': 6.0, 'root_height_drop_m': 0.19995799999999997, 'left_knee_range_rad': 1.876039, 'right_knee_range_rad': 2.37093, 'left_hip_pitch_range_rad': 1.8002610000000001, 'right_hip_pitch_range_rad': 1.8217860000000001, 'max_knee_delta_rad': 2.37093, 'max_hip_pitch_delta_rad': 1.8217860000000001, 'knee_max_rad': 2.498221, 'hip_pitch_min_rad': -1.57, 'reference_gate_like': True, 'score': 6.763604}
Contract check: {'verdict': 'PASS', 'contract': 'physical-ai-web-trajectory-v1', 'frames': 360, 'fps': 60.0, 'duration_s': 6.0, 'nq': 36, 'scene': 'g1/scene_g1_policy.xml', 'shape_valid': True, 'finite_valid': True, 'start_height_m': 0.805576, 'min_height_m': 0.646794, 'max_height_m': 0.846752, 'end_height_m': 0.810531, 'root_height_drop_m': 0.15878199999999998, 'errors': []}

This gate proves ingestion only. M19 still requires a native dynamics rollout and browser replay that pass exp29 visible metrics.
