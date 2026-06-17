# G1 Multi-step Rollout Risk Summary

| Attempt | Verdict | Horizon | Drop | Knee | Hip | Contact | Slip | CoM min | ZMP min | Blend | Fdbk | Force | Inv torque | Fell |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| h0p4-balanced-0p08 | FAIL_FALL | 0.4s | 1.5090m | 0.569 | 0.371 | 0.95 | 0.717m | -0.5997m | -0.6058m | 0.70 | 1.00 | 2738.0 | 64.2 | 3.06s |
| h0p8-balanced-0p08 | FAIL_FALL | 0.8s | 1.5078m | 0.465 | 0.430 | 0.91 | 0.890m | -0.5962m | -0.5958m | 0.41 | 1.00 | 1542.9 | 50.2 | 4.62s |
| h0p4-depth-0p10 | FAIL_FALL | 0.4s | 1.5046m | 0.484 | 0.417 | 0.97 | 0.687m | -0.5968m | -0.6000m | 0.85 | 1.00 | 1889.9 | 68.6 | 2.94s |
| h0p8-depth-0p10 | FAIL_FALL | 0.8s | 1.5070m | 0.618 | 0.407 | 0.91 | 0.801m | -0.6102m | -0.6103m | 0.85 | 1.00 | 2544.1 | 75.2 | 4.26s |

Best no-fall run: None
Best depth run: {'attempt': 'h0p4-balanced-0p08', 'visible_drop': 1.509033345501381, 'fell_at': 3.06, 'foot_slip_distance': 0.7170407568293521}

M19 closes only when visible depth, knee/hip pose, no-fall, contact, stance, return, and browser replay gates pass together.
