# Step 0: environment-preset-contract

## 읽어야 할 파일

- `docs/ARCHITECTURE.md` - 왜: environment layer와 QA-readable summary contract가 정의되어 있다.
- `experiments/03-digital-twin/web/experiments.json` - 왜: scene registry와 per-experiment config 확장 위치를 판단한다.
- `experiments/03-digital-twin/web/src/main.js` 또는 React runtime adapter - 왜: selected environment state를 runtime에 주입해야 한다.

## 작업

Environment preset contract를 정의한다. 최소 preset: `flat-lab`, `instrumented-lab`, `rough-terrain`. 각 preset은 visual environment, floor material, terrain/contact intent, allowed grounding/physics knobs, default values를 가진다. UI와 `window.demo.qaEnvironmentSummary()`에서 같은 값이 나오게 한다.

## Acceptance Criteria

```bash
cd experiments/03-digital-twin/web
node qa/environment_check.mjs --exp=unitree-g1-elastic-stand --preset=flat-lab
node qa/environment_check.mjs --exp=unitree-g1-elastic-stand --preset=instrumented-lab
```

## 금지사항

- preset summary 없이 visual만 바꾸지 않는다.
- default preset이 기존 replay/policy QA를 깨면 안 된다.
