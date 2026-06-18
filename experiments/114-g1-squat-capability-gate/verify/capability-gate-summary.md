# G1 squat capability gate summary

Verdict: `CAPABLE_IN_PRINCIPLE__CURRENT_CONTROLLER_FAILS`
Next action: `upstream_tracker_scene_parity_first_then_full_order_idqp_mpc`

## Public evidence
- Unitree G1 controls documentation (https://docs.quadruped.de/projects/g1/html/operation_1.2.html, accessed 2026-06-18): stock Squat Mode proves a posture path exists, not an autonomous balanced squat skill.
- Unitree G1 overview documentation (https://www.docs.quadruped.de/projects/g1/html/g1_overview.html, accessed 2026-06-18): leg morphology is not an obvious blocker for squat-like posture control.
- IEEE Robots Guide: Unitree G1 (https://robotsguide.com/robots/unitree-g1, accessed 2026-06-18): public visual evidence supports kinematic deep squat feasibility.
- G1 Moves dataset (https://huggingface.co/datasets/exptech/g1-moves, accessed 2026-06-18): learned G1 full-body motion tracking is a practical route, but scene/policy parity matters.
- UniTracker paper (https://arxiv.org/html/2507.07356v2, accessed 2026-06-18): G1-class hardware can track rich whole-body motions when the tracker and dynamics stack are aligned.
- Isaac Lab issue #3751 (https://github.com/isaac-sim/IsaacLab/issues/3751, accessed 2026-06-18): our ONNX/native failures are consistent with model-scene-action mismatch, not proof that squat is impossible.

## Local evidence
- Static best: drop 0.16m, foot error 0.0008m, knee 0.930rad, hip 0.444rad.
- Latest stable native: `terminal-stand-soft` drop 0.0553m, knee 0.395rad, hip 0.216rad, contact 1.00, slip 0.029m, return True.
- Latest visible native branch: `terminal-depth-late-pop` reached large drop but verdict `FAIL_FALL` with fall at 5.38s.

## Interpretation
- The robot appears capable of squat-like postures and full-body tracking in principle.
- The stock Squat Mode is explicitly not a balanced autonomous squat skill.
- The current M19 controller stack still fails the exp29 native visible gate, so browser replay is intentionally not attempted.
