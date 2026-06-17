# G1 Stance Anchor Summary

| Attempt | Verdict | Drop | Fell at | Contact | Final height | Slip | Trigger |
|---|---|---:|---:|---:|---:|---:|---|
| smoke | DEPTH_PENDING | 0.0016m | never | 1.00 | 0.7534m | 0.001m | - @  |
| early-visible-return | FAIL_FALL | 1.5264m | 2.48s | 0.95 | -0.6518m | 1.004m | visible_then_abort @ 2.16 |
| preemptive-return | FAIL_FALL | 1.5341m | 2.54s | 0.90 | -0.6596m | 0.977m | visible_then_abort @ 2.16 |
| stance-tight | FAIL_FALL | 1.5303m | 2.62s | 0.89 | -0.6665m | 0.961m | slip_abort @ 2.28 |
| slow-visible-return-9s | FAIL_FALL | 1.5286m | 4.88s | 0.89 | -0.7242m | 1.162m | contact_loss @ 4.3 |
| slow-preemptive-9s | FAIL_FALL | 1.5281m | 4.14s | 0.91 | -0.7204m | 1.158m | contact_loss @ 3.58 |
| no-policy-visible-return | FAIL_FALL | 1.5333m | 1.24s | 0.91 | -0.7490m | 1.005m | visible_then_abort @ 0.96 |
| no-policy-preemptive | FAIL_FALL | 1.5330m | 1.24s | 0.92 | -0.7505m | 0.988m | visible_then_abort @ 0.92 |

M19 is closed only if visible depth, no-fall, contact, stance, return, and browser replay gates pass together.

Conclusion: stance-anchor scheduling does not close M19. Early return cannot arrest the downward momentum once the visible-depth reference has pulled the robot past the support margin, and disabling the learned policy residual makes the result worse. Next work should use explicit whole-body/stance constraints or train a stance-aware return policy rather than adding more hand-written blend schedules.
