# Step 1 - Diagnostics Panel Smoke

## Acceptance Criteria

- Playwright verifies the diagnostics panel is visible on `?debug=1`.
- Evidence records local and live checks under `experiments/137-physics-diagnostics-panel/verify/physics-diagnostics-panel-smoke.json`.
- The check asserts visible claim boundary text so runtime readout is not confused with real robot telemetry.

## Verification

- `node qa/physics_diagnostics_panel_check.mjs --exp=g1-rough-walk --preset=rough-terrain`
- `node qa/physics_diagnostics_panel_check.mjs --exp=g1-rough-walk --preset=rough-terrain --live`

