# Step 0: workbench-evidence-panel

## 읽어야 할 파일

- `ROADMAP.md` - 왜: M26 DoD와 evidence path가 정의된 상위 milestone이다.
- `docs/PRD.md` - 왜: public viewer를 workbench로 끌어올리는 사용자 가치와 scope를 정의한다.
- `docs/ARCHITECTURE.md` - 왜: runtime layers와 QA summary contract를 정의한다.
- `docs/adr/0010-digital-twin-workbench-foundation.md` - 왜: backend rewrite보다 workbench layer를 먼저 두는 결정을 보존한다.
- `experiments/03-digital-twin/web/src/main.js` - 왜: overlay, telemetry, compare, stream, QA hook이 구현되는 단일 viewer entrypoint다.
- `experiments/03-digital-twin/web/qa/visual_check.mjs` - 왜: 기존 Playwright QA 패턴과 local COOP/COEP server startup을 재사용한다.

## 작업

Selected experiment의 runtime mode, state contract, evidence lanes, current limit을 visible panel과 `window.demo.qaWorkbenchSummary()`로 노출한다. `unitree-g1-elastic-stand`가 telemetry sidecar + replay qpos contract를 드러내고, 기존 replay/policy QA path를 깨지 않게 한다.

## Acceptance Criteria

```bash
cd experiments/03-digital-twin/web
node qa/workbench_check.mjs --exp=unitree-g1-elastic-stand
node qa/visual_check.mjs --exp=unitree-g1-elastic-stand --steps=1 --chunk=1
```

## 검증 절차

1. AC 커맨드 실행.
2. `experiments/127-digital-twin-workbench-foundation/verify/unitree-g1-elastic-stand-workbench-summary.json`에 `pass: true`, `stateContract.nq: 36`, telemetry evidence가 있는지 확인.
3. `phases/m26-digital-twin-workbench/index.json` step 0 상태를 `completed` 또는 `error`로 갱신한다.

## 금지사항

- assisted fixture를 real robot telemetry 또는 unassisted controller proof로 표현하지 않는다.
- canonical experiment JSON을 바꾸지 않는다. 이번 step은 web UI와 QA만 다룬다.
- existing visual QA를 깨뜨리지 않는다.
