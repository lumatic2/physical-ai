# Step 1: lazy-loaded-lab-shell

## 읽어야 할 파일

- `phases/m32-asset-backed-lab-shell/index.json` - 왜: Step 0 asset path와 contract를 이어받는다.
- `experiments/03-digital-twin/web/src/main.js` - 왜: GLTFLoader lazy-load와 QA summary 기록 구현 대상이다.
- `experiments/03-digital-twin/web/src/environmentPresets.js` - 왜: asset-backed state를 QA summary에 포함할 수 있다.

## 작업

Three.js `GLTFLoader`로 lab shell asset을 lazy-load해 `Lab Visual Layer`에 붙이고, `qaEnvironmentSummary().assetLayer`에 loaded/path/objectCount/error를 기록한다.

## Acceptance Criteria

```bash
cd experiments/03-digital-twin/web
npm run build
node qa/asset_shell_check.mjs --exp=g1-walk --preset=flat-lab
```

## 금지사항

- asset load 실패가 화면 전체를 깨뜨리게 하지 마라.
- physics/contact summary와 asset visual summary를 섞지 마라.
