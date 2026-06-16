# G1 Squat Controller Probe

- Overall verdict: CONTROLLER_DEPTH_NEEDS_CONTACT
- Stage height: 0.74
- Source params: `/mnt/c/Users/yusun/projects/physical-ai/experiments/22-g1-squat-depth-finetune/verify/train/params.pkl`

| Variant | Verdict | Min height | Fell at | Hold <= stage | Final height | Foot contact |
|---|---|---:|---:|---:|---:|---:|
| policy_only | NO_FALL_DEPTH_PENDING | 0.7501 | never | 0.00s | 0.7512 | 1.00 |
| blend_0p10 | NO_FALL_DEPTH_PENDING | 0.7501 | never | 0.00s | 0.7502 | 0.87 |
| blend_0p20 | STABLE_DEPTH_CONTACT_GAP | 0.7412 | never | 0.86s | 0.7430 | 0.71 |
| blend_0p35 | DEPTH_WITH_FALL | -0.7640 | 2.36 | 3.28s | -0.7561 | 0.71 |
| blend_0p50 | DEPTH_WITH_FALL | -0.7886 | 1.54 | 4.98s | -0.7443 | 0.88 |

Interpretation:
- `CONTROLLER_STAGE_PASS`: use this blend as the next curriculum controller candidate.
- `CONTROLLER_DEPTH_NEEDS_CONTACT`: depth and hold are possible, but stance/contact constraints are not yet good enough.
- `CONTROLLER_DEPTH_NEEDS_HOLD`: depth is possible, but hold/return shaping is still missing.
- `CONTROLLER_UNSTABLE_DEPTH`: depth target is reachable but controller destabilizes the robot.
- `STANDING_ATTRACTOR_PERSISTS`: controller remains too close to the stabilizer standing attractor.
