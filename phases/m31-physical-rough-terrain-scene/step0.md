# Step 0: rough-scene-compatibility-audit

## 읽어야 할 파일

- `ROADMAP.md` - 왜: M31 DoD와 evidence path를 확인한다.
- `experiments/03-digital-twin/experiments.json` - 왜: canonical rough experiment registry를 확인한다.
- `experiments/03-digital-twin/web/assets/scenes/g1/scene_g1_rough.xml` - 왜: G1 rough scene collision geoms를 확인한다.
- `experiments/03-digital-twin/web/assets/scenes/go1/scene_go1_rough.xml` - 왜: Go1 rough scene collision geoms를 확인한다.
- `experiments/03-digital-twin/web/assets/scenes/spot/scene_spot_rough.xml` - 왜: Spot rough scene collision geoms를 확인한다.

## 작업

rough experiment들이 실제 `curb_*` MJCF geoms를 가진 scene variant에 연결되어 있는지 감사하고, 결과를 `experiments/132-physical-rough-terrain-scene/verify/rough-scene-audit.json`에 기록한다.

## Acceptance Criteria

```bash
node -e "const e=require('./experiments/132-physical-rough-terrain-scene/verify/rough-scene-audit.json'); if(!e.pass) process.exit(1)"
```

## 금지사항

- rough terrain을 visual-only object만으로 통과 처리하지 마라.
- canonical registry가 아닌 `web/experiments.json`만 수정하지 마라.
