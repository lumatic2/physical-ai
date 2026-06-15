# G1 Squat Target Sanity Report

- Overall verdict: TARGET_LOWERING_UNSTABLE
- Reference: `experiments/17-motion-to-policy-loop/verify/g1_squat_reference.compiled.json`
- Scene: `experiments/03-digital-twin/web/assets/scenes/g1/scene_g1_policy.xml`

| Variant | Verdict | Min height | Fell at | Max ref err | Joint limit |
|---|---|---:|---:|---:|---:|
| reference_direct | TARGET_LOWERING_UNSTABLE | -0.766 | 1.22 | 0.19066 | 0.02983 |
| reference_slow_2x | TARGET_LOWERING_UNSTABLE | -0.776 | 1.22 | 0.15013 | 0.02795 |
| reference_deepened_1p35 | TARGET_LOWERING_UNSTABLE | -0.765 | 1.22 | 0.18335 | 0.02996 |
| scripted_deep_legs | TARGET_LOWERING_UNSTABLE | -0.742 | 1.22 | 0.14317 | 0.03075 |

Interpretation:
- Stable depth means the target is viable and PPO/curriculum is the bottleneck.
- Unstable depth means the target lowers the robot but needs a staged controller/curriculum.
- Shallow or pre-depth failure means the pose/reference target should be redesigned before more PPO.
