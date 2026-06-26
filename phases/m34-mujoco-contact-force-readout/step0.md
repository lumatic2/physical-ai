# Step 0: runtime-field-audit

## 읽어야 할 파일

- docs/ARCHITECTURE.md - 왜: physics readout layer와 unsupported field 처리 규칙이 있음.
- docs/adr/0012-controllable-physics-evidence-workbench.md - 왜: MuJoCo runtime readout 우선 결정을 확인해야 함.
- experiments/03-digital-twin/web/src/main.js - 왜: MuJoCo WASM model/data 접근 위치가 있음.
- experiments/107-g1-contact-force-feasibility-audit/README.md - 왜: native contact/force audit에서 어떤 값이 의미 있었는지 참고.

## 작업

브라우저 `mujoco-js` runtime에서 `data.ncon`, `data.contact`, `data.cfrc_ext`, `data.sensordata` 또는 동등 필드가 접근 가능한지 read-only probe를 작성한다. 지원/미지원 필드를 모두 기록하고, 미지원 값은 추정하지 않는다.

## Acceptance Criteria

```bash
cd experiments/03-digital-twin/web
npm run build
node qa/workbench_check.mjs --exp=g1-rough-walk
```

## 검증 절차

1. read-only probe가 sim behavior를 바꾸지 않는지 확인.
2. `experiments/135-mujoco-contact-force-readout/verify/contact-readout-probe.json`에 supported/unavailable 필드를 기록.
3. `phases/m34-mujoco-contact-force-readout/index.json` step 0 상태 갱신.

## 금지사항

- 필드가 없는데 visual cue로 대체하지 마라. 이유: M34의 핵심은 unsupported도 정직하게 밝히는 것이다.
- MuJoCo binding이나 physics engine을 교체하지 마라. 이유: 이 step은 probe이지 runtime migration이 아니다.
