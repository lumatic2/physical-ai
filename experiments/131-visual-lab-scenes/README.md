# M30 - Visual Lab Scenes

## What This Proves

Robotics Lab environment presets now change the visible lab composition, not just the color palette.

- `flat-lab`: calibration bay fixtures, floor seams, marker posts, and safety stripes.
- `instrumented-lab`: measurement gantry, overhead tracking sensors, telemetry monitors, and cable runs.
- `rough-terrain`: visual curb blocks, side barriers, hazard stripes, and lane volume guides.

## What This Does Not Prove

This milestone is visual-only. The added objects live under the Three.js `Lab Visual Layer` and do not change MuJoCo collision, contact, solver, or policy behavior.

Physical rough-terrain evidence belongs to M31.

## Evidence

- Verify JSON: `verify/visual-lab-scenes-smoke.json`
- Source QA summaries:
  - `experiments/03-digital-twin/web/qa/out/g1-walk_workbench_summary.json`
  - `experiments/03-digital-twin/web/qa/out/g1-walk_flat-lab_environment_summary.json`
  - `experiments/03-digital-twin/web/qa/out/g1-walk_instrumented-lab_environment_summary.json`
  - `experiments/03-digital-twin/web/qa/out/g1-rough-walk_rough-terrain_environment_summary.json`

## Verification

```bash
cd experiments/03-digital-twin/web
npm run build
node qa/workbench_check.mjs --exp=g1-walk
node qa/environment_check.mjs --exp=g1-walk --preset=flat-lab
node qa/environment_check.mjs --exp=g1-walk --preset=instrumented-lab
node qa/environment_check.mjs --exp=g1-rough-walk --preset=rough-terrain
```
