# G1 Terminal Stand IDQP/MPC Assist Summary

| Rank | Attempt | Score | Verdict | Drop | Knee | Hip | Contact | Slip | Final h | Return | Fall |
|---:|---|---:|---|---:|---:|---:|---:|---:|---:|---|---|
| 1 | terminal-stand-soft | 313.0 | DEPTH_PENDING_8CM | 0.0553m | 0.395 | 0.216 | 1.00 | 0.029m | 0.7409m | True | never |
| 2 | terminal-stand-earlier | 370.1 | DEPTH_PENDING_8CM | 0.0394m | 0.325 | 0.283 | 0.99 | 0.029m | 0.7442m | True | never |
| 3 | terminal-stand-strong | 464.3 | DEPTH_PENDING_8CM | 0.0318m | 0.267 | 0.241 | 0.99 | 0.029m | 0.7479m | True | never |
| 4 | terminal-depth-fast-return | 2784.7 | FAIL_FALL | 1.5204m | 0.432 | 0.298 | 0.92 | 0.331m | -0.4094m | False | 4.68s |
| 5 | terminal-depth-preserve-delayed | 2840.0 | FAIL_FALL | 1.5189m | 0.441 | 0.426 | 0.92 | 0.336m | -0.5906m | False | 5.28s |
| 6 | terminal-depth-late-pop | 3225.1 | FAIL_FALL | 1.5138m | 0.389 | 0.874 | 0.86 | 0.415m | -0.7189m | False | 5.38s |
| 7 | terminal-knee-return | 3236.5 | FAIL_FALL | 1.5188m | 0.397 | 0.206 | 0.89 | 0.394m | -0.7075m | False | 4.54s |

Best terminal assist run: {'attempt': 'terminal-stand-soft', 'visible_verdict': 'DEPTH_PENDING_8CM', 'visible_drop': 0.0553396075661754, 'max_knee_delta_rad': 0.3950387469324843, 'max_hip_pitch_delta_rad': 0.21602445327539038, 'foot_contact_ratio': 0.9966666666666667, 'foot_slip_distance': 0.028604200613289422, 'final_height': 0.7408742565362982, 'return_to_stand': True, 'fell_at': None, 'terminal_idqp_score': 312.97708433853575}
Best visible geometry run: {'attempt': 'terminal-depth-late-pop', 'visible_verdict': 'FAIL_FALL', 'visible_drop': 1.5137747605840766, 'max_knee_delta_rad': 0.3889292446476658, 'max_hip_pitch_delta_rad': 0.8738128844601627, 'foot_contact_ratio': 0.8633333333333333, 'foot_slip_distance': 0.41548180635229975, 'final_height': -0.7189244432559662, 'return_to_stand': False, 'fell_at': 5.38, 'terminal_idqp_score': 3225.140417664797}

Browser replay is attempted only after native exp29 visible gate passes.
