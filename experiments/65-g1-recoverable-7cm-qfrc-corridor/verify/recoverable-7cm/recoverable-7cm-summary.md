# G1 Recoverable 7cm QFRC Corridor Summary

| Attempt | 7cm gate | Verdict | Drop | Knee | Hip | Contact | Slip | CoM min | ZMP min | Final h | Fell |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| qfrc-8cm-r0p065-t24-baseline | FAIL | DEPTH_PENDING_7CM | 0.0600m | 0.428 | 0.201 | 1.00 | 0.026m | 0.0199m | -0.0311m | 0.7524m | never |
| qfrc-8cm-r0p070-t24 | FAIL | DEPTH_PENDING_7CM | 0.0632m | 0.443 | 0.263 | 1.00 | 0.030m | 0.0098m | -0.0359m | 0.7512m | never |
| qfrc-8cm-r0p070-t28 | FAIL | DEPTH_PENDING_7CM | 0.0620m | 0.438 | 0.216 | 1.00 | 0.029m | 0.0173m | -0.0324m | 0.7542m | never |
| qfrc-8p2cm-r0p068-t26 | FAIL | DEPTH_PENDING_7CM | 0.0642m | 0.445 | 0.273 | 1.00 | 0.038m | -0.1486m | -0.0365m | 0.7416m | never |
| qfrc-8p5cm-r0p068-t26 | FAIL | RETURN_PENDING | 0.0742m | 0.458 | 0.249 | 1.00 | 0.049m | -0.2703m | -0.1353m | 0.6808m | never |
| qfrc-8p5cm-r0p070-t28 | FAIL | RETURN_PENDING | 0.1938m | 0.466 | 0.220 | 0.99 | 0.049m | -0.3960m | -0.3068m | 0.5612m | never |
| qfrc-9cm-r0p068-t26-slow | FAIL | RETURN_PENDING | 0.0846m | 0.480 | 0.166 | 1.00 | 0.051m | -0.2912m | -0.1577m | 0.6704m | never |
| qfrc-8p5cm-r0p068-t26-early-return | FAIL | FAIL_FALL | 0.9871m | 0.563 | 0.354 | 0.94 | 0.354m | -0.5696m | -0.5696m | -0.2321m | 5.76s |
| qfrc-8p5cm-r0p070-t28-early-return | FAIL | FAIL_FALL | 1.3434m | 0.568 | 0.361 | 0.94 | 0.527m | -0.5727m | -0.5723m | -0.5884m | 5.68s |
| qfrc-8p3cm-r0p070-t28-early-return | FAIL | FAIL_FALL | 1.5074m | 0.572 | 0.364 | 0.92 | 0.908m | -0.5761m | -0.5758m | -0.7524m | 5.56s |

Best recoverable run: None
Best no-fall run: {'attempt': 'qfrc-8p5cm-r0p070-t28', 'visible_drop': 0.19380789553435784, 'transition_verdict': 'RETURN_PENDING'}
Best depth run: {'attempt': 'qfrc-8p3cm-r0p070-t28-early-return', 'visible_drop': 1.5074235069860569, 'fell_at': 5.56, 'transition_verdict': 'FAIL_FALL'}

This remains an intermediate corridor gate. M19 still requires exp29 8cm visible depth, knee/hip pose, native no-fall, browser replay, contact, stance, and return together.
