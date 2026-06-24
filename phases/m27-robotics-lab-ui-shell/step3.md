# Step 3: responsive-visual-qa

## 읽어야 할 파일

- `docs/plans/2026-06-24-robotics-lab-v2.md` - 왜: M27 completion gate와 M28 handoff가 있다.
- `experiments/03-digital-twin/web/qa/visual_check.mjs` - 왜: existing desktop/mobile visual smoke를 확장한다.
- `experiments/03-digital-twin/web/README.md` - 왜: user-facing run/deploy instructions를 UI shell 변경에 맞게 갱신한다.

## 작업

Desktop and mobile responsive polish pass. Canvas, command controls, workbench panels, robot selector, telemetry/compare readouts, favicon, and QA status must fit without overlap. Update README with new dev/build commands.

## Acceptance Criteria

```bash
cd experiments/03-digital-twin/web
npm run build
node qa/visual_check.mjs --exp=unitree-g1-elastic-stand --steps=1 --chunk=1
node qa/visual_check.mjs --exp=unitree-g1-elastic-stand --mobile --steps=1 --chunk=1
node qa/workbench_check.mjs --exp=g1-squat-reference-vs-wbc
```

## 검증 절차

1. desktop/mobile screenshots를 확인한다.
2. consoleErrors=0을 확인한다.
3. M27 DoD evidence JSON을 `experiments/128-robotics-lab-ui-shell/verify/`에 박제한다.
4. M27이 닫히면 ROADMAP helper로 complete 처리한다.

## 금지사항

- visual QA 없이 M27 완료 처리하지 않는다.
- UI polish 중 physics tuning을 섞지 않는다.
