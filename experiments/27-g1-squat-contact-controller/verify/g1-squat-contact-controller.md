# G1 Squat Contact Controller Probe

- Overall verdict: CONTACT_CONTROLLER_DEPTH_NEEDS_CONTACT
- Stage height: 0.74
- Source params: `/mnt/c/Users/<user>/projects/physical-ai/experiments/22-g1-squat-depth-finetune/verify/train/params.pkl`

| Variant | Verdict | Min height | Fell at | Hold <= stage | Final height | Foot contact | Mean blend |
|---|---|---:|---:|---:|---:|---:|---:|
| policy_only | NO_FALL_DEPTH_PENDING | 0.7501 | never | 0.00s | 0.7512 | 1.00 | 0.000 |
| blend_0p15 | NO_FALL_DEPTH_PENDING | 0.7458 | never | 0.00s | 0.7470 | 0.78 | 0.150 |
| blend_0p18 | STABLE_DEPTH_CONTACT_GAP | 0.7437 | never | 0.54s | 0.7445 | 0.73 | 0.180 |
| blend_0p20 | STABLE_DEPTH_CONTACT_GAP | 0.7412 | never | 0.86s | 0.7422 | 0.72 | 0.200 |
| blend_0p22 | STABLE_DEPTH_CONTACT_GAP | 0.7395 | never | 1.08s | 0.7406 | 0.68 | 0.220 |
| blend_0p25 | STABLE_DEPTH_CONTACT_GAP | 0.7320 | never | 1.48s | 0.7437 | 0.63 | 0.250 |
| guard_0p20_floor_0p05 | NO_FALL_DEPTH_PENDING | 0.7478 | never | 0.00s | 0.7489 | 0.78 | 0.160 |
| guard_0p22_floor_0p08 | NO_FALL_DEPTH_PENDING | 0.7452 | never | 0.00s | 0.7473 | 0.76 | 0.179 |
| guard_0p25_floor_0p10 | STABLE_TOUCH_DEPTH | 0.7441 | never | 0.10s | 0.7463 | 0.73 | 0.202 |

Interpretation:
- `CONTACT_CONTROLLER_STAGE_PASS`: stage 0.74 controller candidate can move to next depth stage.
- `CONTACT_CONTROLLER_DEPTH_NEEDS_CONTACT`: depth/hold remain possible, but contact gate is still open.
- `CONTACT_CONTROLLER_TOO_CONSERVATIVE`: contact is preserved by staying too close to standing.
- `CONTACT_CONTROLLER_UNSTABLE_DEPTH`: depth target is reachable but controller destabilizes the robot.
