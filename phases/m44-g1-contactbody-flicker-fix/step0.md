# Step 0 - Collision And Visual Contract

## Read First

- `experiments/03-digital-twin/web/assets/scenes/g1/g1_mjx_feetonly.xml` - why: G1 policy scenes include this model and missing body collision is the fall-through bug.
- `experiments/03-digital-twin/web/src/main.js` - why: lab visual overlay floor/grid are created here and can z-fight with MuJoCo floor.

## Work

Add explicit floor-contact eligible collision geoms for pelvis/torso/head while preserving existing G1 policy scene names. Remove the duplicate visual floor overlay so MuJoCo floor is the single rendered floor surface.

## Acceptance Criteria

```bash
cd experiments/03-digital-twin/web
npm run build
```

## Result

- PASS: added `pelvis_floor_collision`, `torso_floor_collision`, and `head_floor_collision` to the G1 MJCF with floor-contact eligibility.
- PASS: removed `Matte visual floor overlay`; the MuJoCo floor is no longer covered by a duplicate transparent Three.js floor plane.

## Forbidden

- Do not hide the robot below an opaque visual floor.
- Do not claim real robot collision; this is MuJoCo browser scene collision only.
