# G1 local-scene tracker retrain smoke

Verdict: `FAIL_LOCAL_TRACKER_RETRAIN_SMOKE`
Next action: `move_to_full_order_idqp_mpc_or_longer_motion_tracking_training`

| Run | Score | Verdict | Drop | Knee | Hip | Contact | Slip | Final h | Fall |
|---|---:|---|---:|---:|---:|---:|---:|---:|---|
| source-exp105-no-train | 9410.2 | DEPTH_PENDING_7CM | 0.0200m | 0.480 | 0.345 | 0.39 | 3.305m | 0.7592m | never |
| short-local-retrain-contact-tight | 9366.8 | DEPTH_PENDING_7CM | 0.0207m | 0.484 | 0.339 | 0.42 | 3.219m | 0.7379m | never |

Best run: `short-local-retrain-contact-tight` -> `DEPTH_PENDING_7CM`
Browser replay is attempted only after native exp29 visible gate passes.
