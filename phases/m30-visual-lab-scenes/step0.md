# Step 0: procedural-lab-scene-composition

## 읽어야 할 파일

- `DESIGN.md` - 왜: M30 preset별 시각 방향과 visual-only guardrail이 정의되어 있다.
- `docs/ARCHITECTURE.md` - 왜: visual scene layer와 MuJoCo collision/physics 경계가 정의되어 있다.
- `experiments/03-digital-twin/web/src/main.js` - 왜: `applyEnvironmentVisuals()`와 scene primitive 생성 함수가 구현 대상이다.
- `experiments/03-digital-twin/web/src/environmentPresets.js` - 왜: QA summary와 preset marker contract가 여기서 나온다.

## 작업

`flat-lab`, `instrumented-lab`, `rough-terrain`이 색상만 다른 화면으로 보이지 않도록 procedural Three.js object composition을 강화한다. 모든 object는 `labVisualLayer` 아래 visual-only로 추가하고 MuJoCo model, collision, solver, policy loop는 변경하지 않는다.

## Acceptance Criteria

```bash
cd experiments/03-digital-twin/web
npm run build
node qa/workbench_check.mjs --exp=g1-walk
node qa/environment_check.mjs --exp=g1-walk --preset=flat-lab
node qa/environment_check.mjs --exp=g1-walk --preset=instrumented-lab
node qa/environment_check.mjs --exp=g1-rough-walk --preset=rough-terrain
```

## 검증 절차

1. AC 커맨드 실행.
2. Playwright로 public `/`에서 GUI/hint가 없는지, preset 전환 후 object set이 바뀌는지 확인.
3. `phases/m30-visual-lab-scenes/index.json` step 업데이트.

## 금지사항

- MJCF scene/collision/contact/solver를 바꾸지 마라. 이유: M30은 visual-only milestone이고 physical terrain은 M31이다.
- `visualOnly=true`와 `collision=none-threejs-only` contract를 깨지 마라.
- UI 패널을 키우지 마라. 이유: 이번 step의 핵심은 scene 자체의 공간감이다.
