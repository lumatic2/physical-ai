# G1 Moves upstream scene parity audit

Verdict: `PARITY_BLOCKED_EXACT_SCENE_NOT_PUBLIC`
Next action: `stop_hand_adapter_sweeps_and_start_local_scene_tracker_retrain_or_full_order_idqp_mpc`

## Remote tree
- GitHub paths: 68; g1_mode15_square.xml present: False
- Hugging Face paths: 1000; g1_mode15_square.xml present: False
- Direct XML probes with HTTP 200: 0

## Contract hits
- run_policy.py g1_mode15_square hits: 4
- run_policy.py observation/action hits: 24
- HF CLAUDE exact XML hits: 77

## Local scene
- include: ['g1_mjx_feetonly.xml']
- base actuators: {'position': 29}
- compiled: {'compile': 'PASS', 'nq': 36, 'nv': 35, 'nu': 29, 'nsensor': 22, 'nkey': 1, 'timestep': 0.002}

## Blockers
- exact_g1_mode15_square_xml_not_present_in_public_trees_or_direct_probes
- local_scene_uses_position_actuators_not_upstream_motor_pd_scene
- previous_adapter_public_xml_mjlab_rollouts_all_failed_native_gate

## Interpretation
- The public G1 Moves policy route still lacks exact training-scene parity in this repo.
- Previous native adapter/public XML/mjlab attempts already failed, so another hand-written adapter sweep is low value.
- M19 should continue with local-scene tracker retraining or full-order ID-QP/MPC unless the exact upstream XML is obtained.
