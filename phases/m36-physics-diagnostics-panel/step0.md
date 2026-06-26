# Step 0 - Debug Diagnostics Panel

## Acceptance Criteria

- `?debug=1` renders a compact React panel with `data-testid="physics-diagnostics-panel"`.
- The panel reads from `qaWorkbenchSummary().physicsReadout` without mutating the simulation.
- The panel shows contact count, supported/unavailable runtime fields, sample values, and a claim boundary.

## Verification

- `npm run build`
- `node qa/workbench_check.mjs --exp=g1-rough-walk`

