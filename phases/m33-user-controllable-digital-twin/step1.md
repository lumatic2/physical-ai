# Step 1: keyboard-command-smoke

## 읽어야 할 파일

- phases/m33-user-controllable-digital-twin/step0.md - 왜: step 0에서 노출한 command summary 계약을 검증 대상으로 삼음.
- experiments/03-digital-twin/web/qa/workbench_check.mjs - 왜: 기존 workbench QA hook 사용 방식을 따라야 함.
- experiments/03-digital-twin/web/qa/visual_check.mjs - 왜: browser smoke와 artifact 저장 패턴 참고.
- CLAUDE.local.md - 왜: 직전 세션의 local/live Playwright command 검증 조건이 기록되어 있음.

## 작업

`g1-walk`에서 keyboard down/release가 command vector를 바꾸고 원복하는지 local smoke로 검증하고, 가능하면 live `https://robotics.askewly.com/?exp=g1-walk`도 같은 방식으로 확인한다. 결과를 `experiments/134-user-controllable-digital-twin/verify/control-smoke.json`에 저장한다.

### 구현 계획

1. 새 QA 스크립트 `experiments/03-digital-twin/web/qa/control_smoke.mjs`를 만든다.
   - `workbench_check.mjs`의 dev server spawn/wait/Playwright 구조를 재사용한다.
   - 옵션:
     - `--exp=g1-walk`
     - `--live`
     - `--out=../../../134-user-controllable-digital-twin/verify/control-smoke.json` 또는 내부 기본 경로.
   - local 기본 URL은 `http://127.0.0.1:8132/?exp=g1-walk`.
   - live URL은 `https://robotics.askewly.com/?exp=g1-walk`.
2. local smoke assertions:
   - page load 후 `window.demo.qaWorkbenchSummary().control.enabled === true`.
   - initial command `[0, 0, 0]`.
   - `ArrowUp` keydown 후 command가 `[positive vx, 0, 0]`.
   - `ArrowUp` keyup 후 command가 `[0, 0, 0]`.
   - `ArrowLeft` keydown 후 lateral command가 nonzero이고 release 후 reset.
   - UI에 command status text가 실제로 렌더됐는지 locator/text로 확인.
3. live smoke assertions:
   - 같은 검증을 `--live`에서 실행한다.
   - live 실패 시 artifact에 `live.pass=false`, `error`를 기록하고 프로세스는 실패 처리한다. public claim을 닫는 milestone이므로 숨기지 않는다.
4. evidence artifact schema:
   - `milestone`: `M33`
   - `experiment`: `g1-walk`
   - `local`: `{ url, pass, initial, afterArrowUp, afterRelease, afterArrowLeft, uiVisible }`
   - `live`: 동일 구조 또는 실행하지 못한 이유.
   - `claimBoundary`: `browser policy command input, not real robot telemetry`
   - `generatedAt`: ISO timestamp.
5. phase/ROADMAP sync:
   - `experiments/134-user-controllable-digital-twin/verify/`를 생성한다.
   - Step 1 성공 후 M33 complete helper를 실행한다.

## Acceptance Criteria

```bash
cd experiments/03-digital-twin/web
node qa/control_smoke.mjs --exp=g1-walk
node qa/control_smoke.mjs --exp=g1-walk --live
node qa/workbench_check.mjs --exp=g1-walk
```

## 검증 절차

1. local command smoke 실행 및 JSON artifact 확인.
2. live smoke가 가능하면 실행하고 artifact에 URL/결과를 포함.
3. ROADMAP M33 DoD 충족 시 `roadmap_sync.py complete --milestone M33 --evidence experiments/134-user-controllable-digital-twin/verify/control-smoke.json --summary "<한 줄 결과>"`.

## 금지사항

- live smoke 실패를 local PASS로 숨기지 마라. 이유: public workbench claim은 live URL이 중요하다.
- key event 테스트만 보고 visual UI 확인을 생략하지 마라. 이유: M33은 visible command evidence milestone이다.
- command transition 값은 exact hardcode보다 range 기반으로 검증하라. 이유: command range는 policy별로 다를 수 있다.
