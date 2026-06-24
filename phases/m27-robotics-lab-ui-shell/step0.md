# Step 0: vite-react-shadcn-scaffold

## 읽어야 할 파일

- `docs/ARCHITECTURE.md` - 왜: React/shadcn shell과 MuJoCo runtime boundary가 정의되어 있다.
- `docs/adr/0011-robotics-lab-v2-ui-and-environment.md` - 왜: UI migration과 physics changes를 분리하는 결정이다.
- `experiments/03-digital-twin/web/package.json` - 왜: 현재 static app dependency와 script 상태를 확인해야 한다.
- `experiments/03-digital-twin/web/index.html` - 왜: current import map, favicon, COOP/COEP static entry를 React/Vite entry로 보존해야 한다.
- `experiments/03-digital-twin/web/src/main.js` - 왜: MuJoCo runtime, overlay, QA hooks가 현재 한 파일에 들어 있다.
- `experiments/03-digital-twin/web/qa/visual_check.mjs` - 왜: scaffold 후 기존 runtime smoke를 그대로 통과해야 한다.

## 작업

Vite + React + Tailwind + shadcn/ui를 `experiments/03-digital-twin/web`에 도입하되, 첫 step에서는 MuJoCo runtime behavior를 바꾸지 않는다. shadcn CLI는 프로젝트 컨텍스트가 생긴 뒤 `npx shadcn@latest info`와 필요한 component docs를 확인하고 사용한다. 기존 `serve_coi.py` 또는 Vite dev server에서 COOP/COEP 요구가 깨지지 않도록 한다.

## Acceptance Criteria

```bash
cd experiments/03-digital-twin/web
npm run build
node qa/visual_check.mjs --exp=unitree-g1-elastic-stand --steps=1 --chunk=1
```

## 검증 절차

1. shadcn/Tailwind config가 생성됐는지 확인한다.
2. `unitree-g1-elastic-stand`가 기존 qpos[36] replay와 telemetry readout을 유지하는지 확인한다.
3. 성공 시 `phases/m27-robotics-lab-ui-shell/index.json` step 0을 completed로 갱신한다.

## 금지사항

- 이 step에서 physics/contact/grounding behavior를 바꾸지 않는다.
- MuJoCo CDN/WASM cross-origin isolation requirement를 깨지 않는다.
- shadcn component API는 추정하지 말고 CLI info/docs로 확인한다.
