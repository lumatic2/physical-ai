# G1 Longer Local Tracker Training Gate

Verdict: `FAIL_LONGER_LOCAL_TRACKER_TRAINING_GATE`
Next action: `stop_short_local_tracker_sweeps_and_move_to_real_wbc_stack_or_substantially_longer_tracker_training`

| Run | Score | Verdict | Drop | Knee | Hip | Contact | Slip | Final h | Fall |
|---|---:|---|---:|---:|---:|---:|---:|---:|---|
| source-exp105-no-train | 11055.4 | DEPTH_PENDING_7CM | 0.0200m | 0.480 | 0.345 | 0.39 | 3.305m | 0.7592m | never |
| longer-local-tracker-contact-tight | 11004.9 | DEPTH_PENDING_7CM | 0.0262m | 0.482 | 0.341 | 0.43 | 3.236m | 0.7288m | never |

Delta trained-vs-source: `{"drop_delta_m": 0.006175238685399376, "knee_delta_rad": 0.0016722275349942972, "hip_delta_rad": -0.0043454173943613394, "contact_delta": 0.043333333333333335, "slip_delta_m": -0.06899430387002559, "score_delta": -50.50092250740272}`
Best run: `longer-local-tracker-contact-tight` -> `DEPTH_PENDING_7CM`
Browser replay is attempted only after native exp29 visible gate passes.
