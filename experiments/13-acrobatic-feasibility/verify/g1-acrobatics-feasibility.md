# G1 Acrobatic Feasibility Gate

- Model: `experiments/03-digital-twin/web/assets/scenes/g1/g1_mjx_feetonly.xml`
- Joints / actuators / sensors: 29 / 29 / 22
- Contact pairs: 5
- Foot-floor pairs: 2
- Hand-floor pairs: 0
- Arm torque range: 5.0..25.0 Nm
- Leg torque range: 50.0..139.0 Nm

| Skill | Verdict | Reason | Next gate |
|---|---|---|---|
| squat_or_pose_hold | go | Uses leg/waist position control and existing foot-floor contacts; no new contact class required. | M19 custom reward wrapper. |
| front_kick | go_with_guardrails | Leg torques reach 50-139 Nm and foot contact sensors exist, but single-support balance must be evaluated. | Start with no-ball kick target before ball contact. |
| ball_tap_or_simple_kick | needs_scene | Robot model is usable, but no ball body, ball sensor, or goal metric exists in current scene. | M21 ball-skill sandbox. |
| handstand | blocked_until_contact_model_update | Palm sites and hand collision geoms exist, but there is no hand-floor contact pair; wrist torque is only 5 Nm on pitch/yaw. | Add palm-floor contact, hand force sensors, and a hand support pose test before RL. |
| cartwheel_or_tumble | blocked_until_reference_motion | The model has feet-only locomotion contacts and no reference motion/tracking objective for aerial full-body rotation. | M22 reference-motion loop, then a prep skill such as jump-turn or handstand prep. |
| rabona_kick | defer | Requires ball scene plus crossing-leg balance and target-direction kick; this is downstream of simple kick and ball tap. | M21 angled kick after front kick succeeds. |
