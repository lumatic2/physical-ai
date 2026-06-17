# G1 Actuator Contact WBC Probe Summary

| Attempt | Verdict | Drop | Knee | Hip | Contact | Slip | CoM min | ZMP min | PD tau | qfrc | Final h | Fell |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| torque-only-0p08-t20 | DEPTH_PENDING | 0.0580m | 0.419 | 0.184 | 1.00 | 0.023m | 0.0225m | -0.0281m | 13.3 | 13.3 | 0.7504m | never |
| torque-only-0p08-r0p07-t20 | FAIL_FALL | 1.5091m | 0.564 | 0.349 | 0.92 | 0.930m | -0.5702m | -0.5757m | 12.4 | 12.4 | -0.5430m | 5.24s |
| torque-only-0p08-r0p08-t20 | FAIL_FALL | 1.5080m | 0.569 | 0.362 | 0.87 | 0.938m | -0.5710m | -0.5707m | 9.5 | 9.5 | -0.7473m | 4.68s |
| torque-only-0p08-t40 | DEPTH_PENDING | 0.0541m | 0.397 | 0.260 | 0.99 | 0.110m | -0.0575m | -0.0308m | 32.3 | 32.3 | 0.7311m | never |
| foot-light-0p08-t30 | DEPTH_PENDING | 0.0557m | 0.406 | 0.196 | 0.99 | 0.031m | 0.0277m | -0.0284m | 30.0 | 30.0 | 0.7505m | never |
| stance-torque-0p08-t30 | DEPTH_PENDING | 0.0512m | 0.384 | 0.149 | 1.00 | 0.036m | 0.0345m | -0.0227m | 30.0 | 29.9 | 0.7503m | never |
| balanced-torque-0p08-t60 | FAIL_FALL | 1.5078m | 0.566 | 0.353 | 0.86 | 0.444m | -0.5524m | -0.5768m | 41.0 | 140.0 | -0.5058m | 5.02s |
| pose-torque-0p08-t100 | FAIL_FALL | 1.5179m | 0.583 | 0.351 | 0.87 | 0.409m | -0.5704m | -0.5984m | 52.4 | 190.0 | -0.7629m | 4.56s |
| slow-torque-0p10-t60 | FAIL_FALL | 1.5104m | 0.583 | 0.352 | 0.83 | 0.407m | -0.5488m | -0.5761m | 53.4 | 160.0 | -0.5041m | 4.98s |

Best no-fall run: {'attempt': 'torque-only-0p08-t20', 'visible_drop': 0.057995347017174015, 'max_knee_delta_rad': 0.41898959758087173, 'max_hip_pitch_delta_rad': 0.18418163725523848, 'min_support_margin': 0.022529168648058345, 'min_zmp_margin': -0.02811317046990426, 'return_to_stand': True}
Best depth run: {'attempt': 'pose-torque-0p08-t100', 'visible_drop': 1.5179022142304692, 'fell_at': 4.56, 'min_support_margin': -0.5704449557891146, 'min_zmp_margin': -0.5983987077107121}

M19 closes only when visible depth, knee/hip pose, no-fall, contact, stance, return, and browser replay gates pass together.
