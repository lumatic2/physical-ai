# G1 Actuator Authority Probe Summary

| Attempt | Verdict | Lower x | Ankle extra x | Drop | Knee | Hip | Contact | Slip | Final h | Fell |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| baseline-gain1p0 | STANCE_ENVELOPE_BROKEN | 1.00 | 1.00 | 1.5054m | 0.614 | 0.550 | 0.81 | 0.909m | -0.7257m | 4.54s |
| lower-gain1p5 | STABLE_BUT_SHALLOW | 1.50 | 1.00 | 0.0191m | 0.174 | 0.120 | 1.00 | 0.019m | 0.7533m | never |
| lower-gain2p0 | STABLE_BUT_SHALLOW | 2.00 | 1.00 | 0.0024m | 0.063 | 0.045 | 0.99 | 0.089m | 0.7568m | never |
| lower-gain1p5-ankle3p0 | STANCE_ENVELOPE_BROKEN | 1.50 | 3.00 | 1.5154m | 0.623 | 0.546 | 0.71 | 0.427m | -0.7592m | 1.72s |
| lower-gain2p0-ankle3p0 | STANCE_ENVELOPE_BROKEN | 2.00 | 3.00 | 1.5185m | 0.587 | 0.544 | 0.67 | 0.573m | -0.7597m | 1.30s |

Best no-fall run: {'attempt': 'lower-gain1p5', 'visible_drop': 0.019058906844167667, 'foot_slip_distance': 0.019221628006693497, 'return_to_stand': True}
Best depth run: {'attempt': 'lower-gain2p0-ankle3p0', 'visible_drop': 1.5184600588761468, 'fell_at': 1.3, 'foot_slip_distance': 0.5731791514060732}

This is a simulation authority diagnostic only. It does not prove that the physical G1 can safely execute the same controller.
