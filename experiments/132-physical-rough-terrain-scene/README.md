# M31 - Physical Rough Terrain Scene

## What This Proves

The `rough-terrain` preset is now backed by active MuJoCo rough scene variants for supported rough actions.

- `g1-rough-walk` loads `g1/scene_g1_rough.xml`.
- `go1-rough-walk` loads `go1/scene_go1_rough.xml`.
- `spot-rough-walk` loads `spot/scene_spot_rough.xml`.

Each active browser model exposes `curb_1`, `curb_2`, and `curb_3` terrain geoms through `qaEnvironmentSummary()`.

## User Flow

When a visitor starts from a robot with a rough action, selecting `거친 지형 레인` switches the app internally to that robot's rough action. It does not perform a full page reload.

## What This Does Not Prove

This does not claim broad terrain generalization. The claim is limited to the bundled curb scenes and the policies registered for those scenes.

## Evidence

- Static audit: `verify/rough-scene-audit.json`
- Integrated smoke: `verify/rough-terrain-scene-smoke.json`
- Browser QA summaries:
  - `experiments/03-digital-twin/web/qa/out/g1-rough-walk_rough-terrain_terrain_scene_summary.json`
  - `experiments/03-digital-twin/web/qa/out/go1-rough-walk_rough-terrain_terrain_scene_summary.json`
  - `experiments/03-digital-twin/web/qa/out/spot-rough-walk_rough-terrain_terrain_scene_summary.json`

## Verification

```bash
cd experiments/03-digital-twin/web
npm run build
node qa/terrain_scene_check.mjs --exp=g1-rough-walk --preset=rough-terrain
node qa/terrain_scene_check.mjs --exp=go1-rough-walk --preset=rough-terrain
node qa/terrain_scene_check.mjs --exp=spot-rough-walk --preset=rough-terrain
```
