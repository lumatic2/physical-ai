# Step 1 - Local/Live Contract Evidence

## Read First

- `experiments/03-digital-twin/web/qa/real_robot_collision_contract_check.mjs` - why: local/live gate for the real-robot collision readiness contract.

## Work

Verify that the G1 obstacle scene exposes pelvis/torso/head body-collision zones, planned foot contact patches, required telemetry, actuator gate requirements, stop criteria, and `realRobotCollisionArmed=false` without hardware evidence.

## Acceptance Criteria

```bash
cd experiments/03-digital-twin/web
node qa/real_robot_collision_contract_check.mjs
node qa/real_robot_collision_contract_check.mjs --live
```

## Result

- PASS: local QA writes `experiments/146-real-robot-collision-contract/verify/real-robot-collision-contract-local.json`.
- PASS: live QA writes `experiments/146-real-robot-collision-contract/verify/real-robot-collision-contract-live.json`.
- PASS: aggregate evidence writes `experiments/146-real-robot-collision-contract/verify/real-robot-collision-contract.json`.

## Forbidden

- Do not pass if real robot collision is armed without telemetry/e-stop evidence.
- Do not pass if sim body zones are missing or contact-ineligible.
