# Step 1 - Obstacle Scene Smoke

## 읽어야 할 파일
- experiments/03-digital-twin/web/qa/terrain_scene_check.mjs — 왜: active MJCF geometry smoke pattern.
- experiments/03-digital-twin/web/qa/environment_scenario_check.mjs — 왜: scenario contract assertions.

## 작업
Verify the obstacle scene loads, exposes obstacle geoms in `qaEnvironmentSummary()`, and produces local/live evidence.

## Acceptance Criteria
```bash
node qa/obstacle_scene_smoke.mjs --exp=g1-obstacle-walk --scenario=obstacle-lane-v1
node qa/obstacle_scene_smoke.mjs --exp=g1-obstacle-walk --scenario=obstacle-lane-v1 --live
```

## 금지사항
- Do not claim obstacle avoidance or successful navigation unless the QA evidence measures it.

