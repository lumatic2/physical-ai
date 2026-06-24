# Step 3: physics-preset-evidence

## 읽어야 할 파일

- `phases/m28-digital-twin-lab-environment/index.json` - 왜: previous step summaries를 반영한다.
- `experiments/03-digital-twin/web/qa/environment_check.mjs` - 왜: M28 completion evidence runner다.
- `experiments/127-digital-twin-workbench-foundation/README.md` - 왜: M26 evidence summary pattern을 재사용한다.

## 작업

Environment and physics presets의 비교 evidence를 만든다. 최소 3 preset의 summary JSON, screenshot, pass/fail criteria를 `experiments/129-digital-twin-lab-environment/verify/`에 박제한다. README에는 visual environment와 physics setting이 무엇을 증명하고 무엇을 증명하지 않는지 쓴다.

## Acceptance Criteria

```bash
cd experiments/03-digital-twin/web
node qa/environment_check.mjs --exp=unitree-g1-elastic-stand --preset=flat-lab
node qa/environment_check.mjs --exp=unitree-g1-elastic-stand --preset=instrumented-lab
node qa/environment_check.mjs --exp=unitree-g1-elastic-stand --preset=rough-terrain
```

## 금지사항

- M28 완료 evidence를 ignored `qa/out/`에만 두지 않는다.
- physics tuning failure를 숨기지 않는다. collapse/unstable preset은 FAIL_EXPECTED로 별도 표기한다.
