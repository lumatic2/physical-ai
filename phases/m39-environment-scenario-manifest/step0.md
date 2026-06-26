# Step 0 - Scenario Contract

## 읽어야 할 파일
- experiments/03-digital-twin/web/src/environmentPresets.js — 왜: current preset contract and environment summary shape.
- experiments/03-digital-twin/web/src/main.js — 왜: `qaEnvironmentSummary()` and URL parameter handling.
- experiments/03-digital-twin/web/src/App.jsx — 왜: visible environment summary UI.

## 작업
Add an environment scenario manifest layer with id, seed, terrain, friction, lighting, obstacle, and claim boundary fields. Expose it through `qaEnvironmentSummary()` and the React UI.

## Acceptance Criteria
```bash
npm run build
node qa/environment_scenario_check.mjs --exp=g1-rough-walk --scenario=rough-curb-v1
```

## 금지사항
- Do not mutate MJCF physics from JS in M39. This milestone records the scenario contract only.

