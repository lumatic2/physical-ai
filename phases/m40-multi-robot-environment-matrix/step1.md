# Step 1 - Matrix Local/Live Evidence

## 읽어야 할 파일
- experiments/03-digital-twin/web/qa/environment_matrix_smoke.mjs — 왜: local/live matrix evidence generator.

## 작업
Generate local/live matrix evidence under `experiments/141-multi-robot-environment-matrix/verify/environment-matrix-smoke.json`.

## Acceptance Criteria
```bash
node qa/environment_matrix_smoke.mjs
node qa/environment_matrix_smoke.mjs --live
```

## 금지사항
- Do not claim all robots have identical robustness. This is scenario contract coverage, not performance ranking.

