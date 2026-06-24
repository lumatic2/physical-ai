# Step 1: workbench-components

## 읽어야 할 파일

- `phases/m27-robotics-lab-ui-shell/index.json` - 왜: step 0 완료 summary와 scaffold 결과를 이어받는다.
- `docs/PRD.md` - 왜: workbench UI가 보여야 할 runtime/evidence/limit 요구사항이 있다.
- `experiments/03-digital-twin/web/src/main.js` 또는 새 React entry files - 왜: 기존 overlay copy와 QA hooks를 component로 옮긴다.
- shadcn generated component files - 왜: imports, aliases, variants, semantic tokens를 실제 프로젝트 기준으로 써야 한다.

## 작업

Robot picker, workbench summary, telemetry/compare panels, QA status를 shadcn components로 재구성한다. 권장 component: Button, Card, Tabs, Sheet/Drawer, Select, ToggleGroup, Badge, Separator, Tooltip. Current MuJoCo canvas는 full-bleed viewport로 유지하고 UI chrome만 React/shadcn이 소유한다.

## Acceptance Criteria

```bash
cd experiments/03-digital-twin/web
npm run build
node qa/workbench_check.mjs --exp=unitree-g1-elastic-stand
node qa/workbench_check.mjs --exp=g1-squat-reference-vs-wbc
```

## 검증 절차

1. workbench summary JSON의 `runtime`, `stateContract`, `evidenceLanes`, `gate`, `limit`가 유지되는지 확인한다.
2. desktop/mobile layout에서 text overflow와 canvas occlusion이 없는지 Playwright screenshot으로 확인한다.
3. 성공 시 step 1을 completed로 갱신한다.

## 금지사항

- Cards inside cards 구조를 만들지 않는다.
- Tailwind raw color 남발 대신 shadcn semantic tokens를 우선한다.
- QA hook 이름과 summary contract를 깨지 않는다.
