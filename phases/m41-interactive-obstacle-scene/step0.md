# Step 0 - Obstacle Scene Contract

## 읽어야 할 파일
- experiments/03-digital-twin/web/assets/scenes/g1/scene_g1_rough.xml — 왜: source rough MJCF scene.
- experiments/03-digital-twin/experiments.json — 왜: canonical experiment registry.
- experiments/03-digital-twin/sync_web.py — 왜: web mirror sync boundary.

## 작업
Add a G1 obstacle-lane MJCF scene and registry entry that is distinct from static curb terrain. Add an obstacle scenario contract.

## Acceptance Criteria
```bash
python ../sync_web.py
npm run build
```

## 금지사항
- Canonical registry edits start in `experiments/03-digital-twin/experiments.json`, not only the web mirror.

