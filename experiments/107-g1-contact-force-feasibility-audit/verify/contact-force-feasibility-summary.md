# G1 Contact Force Feasibility Audit Summary

| Attempt | Verdict | Drop | Knee | Hip | Contact | Slip | Max friction ratio | Saturated frames | Min CoP margin | Force frames | Fall |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| exp91-poseqfrc-braked-8cm | FAIL_FALL | 0.4652m | 0.418 | 0.313 | 0.91 | 0.096m | 1.000 | 150 | 0.0003m | 300 | 5.92s |
| exp91-poseqfrc-braked-knee | FAIL_FALL | 1.5257m | 0.392 | 0.435 | 0.91 | 0.400m | 1.000 | 158 | -0.0001m | 300 | 5.50s |
| exp106-friction-knee-minimal-depth | FRICTION_LIMITED_SHALLOW | 0.0520m | 0.383 | 0.204 | 1.00 | 0.016m | 1.000 | 162 | 0.0018m | 300 | never |
| exp106-friction-tight-medium | FAIL_FALL | 1.5221m | 0.414 | 0.417 | 0.90 | 0.375m | 1.000 | 109 | 0.0001m | 300 | 5.40s |

Best no-fall force-audited: {'attempt': 'exp106-friction-knee-minimal-depth', 'visible_drop': 0.05198772714581834, 'knee': 0.38281909097765765, 'hip': 0.2044383814544241, 'max_friction_ratio': 1.0, 'min_cop_support_margin': 0.001766757487128387, 'force_verdict': 'FRICTION_LIMITED_SHALLOW'}
Best visible candidate: {'attempt': 'exp91-poseqfrc-braked-knee', 'visible_drop': 1.5257117910043432, 'knee': 0.3920349879898506, 'hip': 0.4345580914435561, 'fell_at': 5.5, 'force_verdict': 'FAIL_FALL'}

M19 still requires native exp29 visible gate plus browser replay.
