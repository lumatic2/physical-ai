# G1 QFRC WBC Return Selector Summary

| Attempt | 7cm gate | Verdict | Drop | Contact | Slip | CoM min | ZMP min | qfrc | Final h | Fell |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| selector-8cm-r0p065-t24 | FAIL | DEPTH_PENDING_7CM | 0.0601m | 1.00 | 0.022m | -0.0032m | -0.0042m | 7.9 | 0.7430m | never |
| selector-8p2cm-r0p068-t26 | FAIL | FAIL_FALL | 0.5450m | 0.97 | 0.105m | -0.6011m | -0.6008m | 8.2 | 0.2100m | 5.86s |
| selector-8p5cm-r0p068-t26 | FAIL | FAIL_FALL | 0.5623m | 0.97 | 0.103m | -0.6011m | -0.6009m | 8.2 | 0.1927m | 5.86s |
| selector-8p5cm-r0p070-t28 | FAIL | FAIL_FALL | 0.9352m | 0.95 | 0.359m | -0.6025m | -0.6026m | 8.5 | -0.1802m | 5.74s |
| selector-8p2cm-return-biased | FAIL | RETURN_PENDING | 0.1548m | 1.00 | 0.033m | -0.3195m | -0.1475m | 8.2 | 0.6002m | never |
| selector-8cm-early-strong-return | FAIL | DEPTH_PENDING_7CM | 0.0586m | 1.00 | 0.049m | 0.0268m | -0.0127m | 14.7 | 0.7403m | never |
| selector-8p2cm-early-strong-return | FAIL | DEPTH_PENDING_7CM | 0.0626m | 1.00 | 0.034m | 0.0163m | -0.0118m | 13.5 | 0.7433m | never |

Best recoverable run: None
Best no-fall run: {'attempt': 'selector-8p2cm-return-biased', 'visible_drop': 0.15483288020906616, 'transition_verdict': 'RETURN_PENDING', 'final_height': 0.6001671197909338}
Best depth run: {'attempt': 'selector-8p5cm-r0p070-t28', 'visible_drop': 0.9351883842124368, 'fell_at': 5.74, 'transition_verdict': 'FAIL_FALL'}

This is an intermediate 7cm recoverable gate. M19 still requires the exp29 8cm visible native/browser gate.
