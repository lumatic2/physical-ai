# 129 - Digital Twin Lab Environment Controls

M28 evidence for Robotics Lab v2 environment controls.

## What This Proves

- The web twin exposes three environment presets: `flat-lab`, `instrumented-lab`, and `rough-terrain`.
- Each preset records visual treatment, floor/contact intent, grounding claim, physics profile, and runtime mutation status through `window.demo.qaEnvironmentSummary()`.
- The lab visual layer is Three.js-only and reports `collision=none-threejs-only`, so M28 visual polish does not silently change MuJoCo contact geometry.
- Grounding claims are explicit:
  - `assisted-fixture` means support/fixture evidence, not unassisted success.
  - `physics-contact` means free-contact evidence is required before claiming stability.
  - `replay-locked` means qpos replay, not controller proof.
  - `controller-backed` requires controller/policy/LowCmd evidence.

## What This Does Not Prove

- `rough-terrain` in this M28 smoke records terrain/contact intent and marks `scene.reloadRequired=true`; it does not pretend that the active `unitree-g1-elastic-stand` scene has been live-mutated into rough terrain.
- M28 Step 2/3 controls do not change MuJoCo solver, friction, or contact behavior at runtime.
- Assisted G1 stand remains an assisted simulated fixture and must not be described as real robot telemetry or unassisted humanoid standing.

## Evidence

- `verify/environment-controls-smoke.json` - integrated M28 pass/fail summary.
- `verify/flat-lab-summary.json` and `verify/flat-lab.png`.
- `verify/instrumented-lab-summary.json` and `verify/instrumented-lab.png`.
- `verify/rough-terrain-summary.json` and `verify/rough-terrain.png`.

## Verification Commands

```bash
cd experiments/03-digital-twin/web
npm run build
node qa/environment_check.mjs --exp=unitree-g1-elastic-stand --preset=flat-lab
node qa/environment_check.mjs --exp=unitree-g1-elastic-stand --preset=instrumented-lab
node qa/environment_check.mjs --exp=unitree-g1-elastic-stand --preset=rough-terrain
node qa/environment_check.mjs --exp=unitree-g1-elastic-stand --preset=instrumented-lab --grounding=assisted
node qa/environment_check.mjs --exp=unitree-g1-elastic-stand --preset=rough-terrain --grounding=physics
node qa/workbench_check.mjs --exp=unitree-g1-elastic-stand
node qa/workbench_check.mjs --exp=g1-squat-reference-vs-wbc
```
