# Step 0 - Real Robot Collision Readiness Contract

## Read First

- `experiments/03-digital-twin/web/src/realRobotCollision.js` - why: source of truth for real-robot collision readiness requirements.
- `experiments/03-digital-twin/web/src/main.js` - why: runtime QA summary exposes the contract.

## Work

Map the G1 sim collision envelope to real-robot body zones and explicitly list required telemetry, actuator disable path, e-stop evidence, and stop criteria. Keep the real robot path unarmed unless a hardware bridge and e-stop evidence exist.

## Acceptance Criteria

```bash
cd experiments/03-digital-twin/web
npm run build
```

## Result

- PASS: added `realRobotCollision` runtime summary for G1 with pelvis/torso/head body envelopes and planned foot contact patches.
- PASS: required telemetry, actuator stop gate, e-stop evidence, and stop criteria are explicit.
- PASS: `realRobotCollisionArmed=false` unless hardware telemetry, actuator gate, and e-stop evidence are present.

## Forbidden

- Do not claim hardware collision proof without real telemetry.
- Do not arm real-robot collision handling from browser-only simulation evidence.
