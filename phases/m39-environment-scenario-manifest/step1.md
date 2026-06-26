# Step 1 - Scenario QA Evidence

## 읽어야 할 파일
- experiments/03-digital-twin/web/qa/environment_check.mjs — 왜: environment smoke pattern.
- ROADMAP.md — 왜: M39 DoD and evidence path.

## 작업
Generate local/live evidence for `rough-curb-v1` and verify the scenario fields are machine-readable.

## Acceptance Criteria
```bash
node qa/environment_scenario_check.mjs --exp=g1-rough-walk --scenario=rough-curb-v1
node qa/environment_scenario_check.mjs --exp=g1-rough-walk --scenario=rough-curb-v1 --live
```

## 금지사항
- Do not pass if scenario id, seed, terrain parameters, and claim boundary are absent.

