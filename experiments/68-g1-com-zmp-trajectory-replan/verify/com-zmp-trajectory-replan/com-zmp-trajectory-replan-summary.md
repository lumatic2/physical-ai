# G1 CoM/ZMP Trajectory Replan Summary

| Attempt | 7cm gate | Verdict | Drop | Contact | Slip | CoM min | ZMP min | qfrc | Final h | Fell |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| plan-8cm-early-return | FAIL | DEPTH_PENDING_7CM | 0.0599m | 0.98 | 0.058m | 0.0263m | -0.0103m | 32.1 | 0.7401m | never |
| plan-8p2cm-early-return | FAIL | DEPTH_PENDING_7CM | 0.0641m | 0.99 | 0.046m | 0.0150m | -0.0070m | 14.1 | 0.7437m | never |
| plan-8p25cm-fine | FAIL | DEPTH_PENDING_7CM | 0.0651m | 1.00 | 0.045m | 0.0129m | -0.0041m | 15.3 | 0.7466m | never |
| plan-8p3cm-fine | FAIL | FAIL_FALL | 1.4371m | 0.93 | 0.590m | -0.5776m | -0.5775m | 9.6 | -0.6821m | 5.64s |
| plan-8p35cm-fine | FAIL | FAIL_FALL | 1.4961m | 0.93 | 0.904m | -0.5855m | -0.5852m | 11.5 | -0.5942m | 5.34s |
| plan-8p4cm-early-return | FAIL | FAIL_FALL | 1.4979m | 0.92 | 0.915m | -0.5956m | -0.5955m | 18.8 | -0.5436m | 5.24s |
| plan-8p2cm-mid-return | FAIL | FAIL_FALL | 1.2080m | 0.94 | 0.398m | -0.5805m | -0.5804m | 9.2 | -0.4530m | 5.70s |
| plan-8p5cm-mid-return | FAIL | FAIL_FALL | 1.4954m | 0.91 | 0.970m | -0.6037m | -0.6039m | 19.1 | -0.5886m | 5.30s |
| plan-9cm-support-heavy | FAIL | FAIL_FALL | 1.4969m | 0.89 | 0.939m | -0.6051m | -0.6051m | 13.2 | -0.5456m | 5.20s |

Best recoverable run: None
Best no-fall run: {'attempt': 'plan-8p25cm-fine', 'visible_drop': 0.06508262402435294, 'transition_verdict': 'DEPTH_PENDING_7CM', 'final_height': 0.7466260156529068}
Best depth run: {'attempt': 'plan-8p4cm-early-return', 'visible_drop': 1.4979236695706317, 'fell_at': 5.24, 'transition_verdict': 'FAIL_FALL'}

This is still an intermediate 7cm recoverable gate. M19 closes only after the exp29 8cm native/browser gate passes.
