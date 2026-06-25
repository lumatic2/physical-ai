# Step 1: rough-preset-scene-routing

## 읽어야 할 파일

- `phases/m31-physical-rough-terrain-scene/index.json` - 왜: Step 0 audit 결과를 이어받는다.
- `experiments/03-digital-twin/web/src/App.jsx` - 왜: environment preset 버튼이 scene/action 전환을 호출하는 곳이다.
- `experiments/03-digital-twin/web/src/main.js` - 왜: initial/switch experiment에서 rough preset 기본값과 QA summary를 갱신한다.
- `experiments/03-digital-twin/web/src/environmentPresets.js` - 왜: rough terrain summary에 contact-bearing scene 상태를 기록한다.

## 작업

visitor가 rough terrain preset을 선택하면 현재 로봇의 rough action이 있을 때 in-app scene switch로 rough scene을 연다. rough scene experiment는 environment summary에 contact-bearing scene으로 기록한다.

## Acceptance Criteria

```bash
cd experiments/03-digital-twin/web
npm run build
node qa/terrain_scene_check.mjs --exp=g1-rough-walk --preset=rough-terrain
node qa/terrain_scene_check.mjs --exp=go1-rough-walk --preset=rough-terrain
node qa/terrain_scene_check.mjs --exp=spot-rough-walk --preset=rough-terrain
```

## 금지사항

- 전체 page reload로 전환하지 마라.
- rough가 없는 로봇에서 거짓 physical claim을 만들지 마라.
