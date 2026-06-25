# Step 2: rough-terrain-evidence

## 읽어야 할 파일

- `experiments/03-digital-twin/web/qa/terrain_scene_check.mjs` - 왜: M31 통합 evidence를 만들 때 재사용한다.
- `experiments/132-physical-rough-terrain-scene/verify/rough-scene-audit.json` - 왜: static MJCF audit 결과와 browser QA를 묶는다.
- `experiments/03-digital-twin/web/qa/out/*terrain*` - 왜: rough browser QA summary source다.

## 작업

M31 README와 `verify/rough-terrain-scene-smoke.json`을 작성한다. evidence는 static MJCF audit + browser MuJoCo model curb geometry check + in-app preset routing smoke를 포함한다.

## Acceptance Criteria

```bash
node -e "const e=require('./experiments/132-physical-rough-terrain-scene/verify/rough-terrain-scene-smoke.json'); if(!e.pass) process.exit(1)"
```

## 금지사항

- policy가 모든 rough terrain을 일반화한다고 쓰지 마라. bundled curb scenes로 범위를 제한한다.
