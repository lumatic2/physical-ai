# G1 Contact Envelope Curriculum Summary

| Level | Verdict | Drop | Knee | Hip | Contact | Slip | Final h | Fell |
|---|---|---:|---:|---:|---:|---:|---:|---|
| level-0p025 | STABLE_BUT_SHALLOW | 0.0123m | 0.138 | 0.045 | 1.00 | 0.013m | 0.7483m | never |
| level-0p040 | STABLE_BUT_SHALLOW | 0.0165m | 0.168 | 0.075 | 1.00 | 0.012m | 0.7483m | never |
| level-0p060 | STABLE_BUT_SHALLOW | 0.0222m | 0.208 | 0.117 | 1.00 | 0.012m | 0.7483m | never |
| level-0p080 | STANCE_ENVELOPE_BROKEN | 1.5054m | 0.614 | 0.550 | 0.81 | 0.909m | -0.7257m | 4.54s |

Stable boundary: {'attempt': 'level-0p060', 'configured_drop': 0.06, 'actual_drop': 0.022160332660954962, 'slip': 0.012353587270678314}
First broken level: {'attempt': 'level-0p080', 'configured_drop': 0.08, 'actual_drop': 1.5053672974420302, 'fell_at': 4.54, 'slip': 0.9087533630728846}

M19 closes only when visible depth, knee/hip pose, no-fall, contact, stance, return, and browser replay gates pass together.
