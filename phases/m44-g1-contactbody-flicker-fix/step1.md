# Step 1 - Local/Live Regression Evidence

## Read First

- `experiments/03-digital-twin/web/qa/obstacle_scene_smoke.mjs` - why: existing local/live Playwright pattern for G1 obstacle scene.
- `experiments/03-digital-twin/web/src/mujocoUtils.js` - why: Three.js geom material generation affects flicker and visibility.

## Work

Create a QA script that loads G1 obstacle scene, verifies pelvis/torso/head contact geoms are contact eligible, verifies the visual floor overlay is absent from environment summary, and writes local/live evidence.

## Acceptance Criteria

```bash
cd experiments/03-digital-twin/web
node qa/g1_contactbody_flicker_check.mjs
node qa/g1_contactbody_flicker_check.mjs --live
```

## Result

- PASS: local QA writes `experiments/145-g1-contactbody-flicker-fix/verify/g1-contactbody-flicker-fix-local.json`.
- PASS: live QA writes `experiments/145-g1-contactbody-flicker-fix/verify/g1-contactbody-flicker-fix-live.json`.
- PASS: aggregate evidence writes `experiments/145-g1-contactbody-flicker-fix/verify/g1-contactbody-flicker-fix.json`.

## Forbidden

- Do not pass if only foot geoms are contact eligible.
- Do not pass if `Matte visual floor overlay` is still in the visual layer object list.
