# Step 0 - Matrix Smoke Script

## 읽어야 할 파일
- experiments/03-digital-twin/web/qa/environment_scenario_check.mjs — 왜: scenario contract assertions.
- experiments/03-digital-twin/experiments.json — 왜: robot experiment keys and scene mapping.

## 작업
Add a matrix QA script that loads G1/Go1/Spot flat and rough scenarios, records environment summary, and asserts each row has a scenario contract.

## Acceptance Criteria
```bash
node qa/environment_matrix_smoke.mjs
```

## 금지사항
- Do not use screenshots as the only evidence; matrix rows must be structured JSON.

