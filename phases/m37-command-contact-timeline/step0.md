# Step 0 - Timeline Smoke Script

## 읽어야 할 파일
- experiments/03-digital-twin/web/qa/control_smoke.mjs — 왜: keyboard command transition smoke pattern 재사용.
- experiments/03-digital-twin/web/qa/physics_diagnostics_panel_check.mjs — 왜: physicsReadout evidence path/write pattern 재사용.
- experiments/03-digital-twin/web/src/main.js — 왜: `qaStep()` and `qaWorkbenchSummary()` contracts.

## 작업
Add a Playwright QA script that records baseline, command-held, stepped, and released samples in one timeline.

## Acceptance Criteria
```bash
node qa/command_contact_timeline.mjs --exp=g1-rough-walk --preset=rough-terrain
```

## 금지사항
- Do not claim real robot telemetry. This is browser MuJoCo WASM runtime readout only.

