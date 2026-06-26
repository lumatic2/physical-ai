# Step 0: command-state-ui

## 읽어야 할 파일

- docs/ARCHITECTURE.md - 왜: control evidence layer와 QA summary 계약이 여기 정의됨.
- docs/PRD.md - 왜: M33 성공 기준과 public claim 경계를 확인해야 함.
- docs/adr/0012-controllable-physics-evidence-workbench.md - 왜: fake contact cue 대신 runtime/control evidence를 쓰는 결정 근거.
- experiments/03-digital-twin/web/src/App.jsx - 왜: Robotics Lab UI shell과 action selection surface가 있음.
- experiments/03-digital-twin/web/src/main.js - 왜: keyboard command listener와 `window.demo` QA hooks가 있음.

## 작업

`g1-walk` 같은 policy mode에서 현재 command vector, 입력 source, key down/release 상태를 visible UI와 `window.demo.qaWorkbenchSummary()`에 노출한다. 기존 policy command semantics는 바꾸지 말고, 이미 연결된 Arrow/WASD/QE path를 읽어서 설명 가능하게 만든다.

### 구현 계획

1. `main.js`에 read-only control summary helper를 추가한다.
   - 위치: `workbenchSummary()` 근처 또는 command binding 근처.
   - 반환 계약:
     - `enabled`: policy experiment 여부.
     - `command`: 현재 `[vx, vy, vyaw]`.
     - `range`: policy command range.
     - `inputSource`: `keyboard` / `slider` / `initial` / `released`.
     - `heldCommands`: 현재 눌린 semantic command 목록.
     - `mapping`: `Arrow/WASD/QE`가 어떤 축을 바꾸는지.
     - `claimLevel`: `policy-command-input`, real robot telemetry 아님.
   - `qaWorkbenchSummary()`의 `control` 필드로 포함한다.
2. `bindCommandKeys()`에서 command state만 기록한다.
   - `held` set을 summary helper에서 읽을 수 있게 인스턴스 필드로 보관한다.
   - `keydown` 때 `lastCommandInputSource = "keyboard"`, `keyup` 뒤 held가 비면 `released`.
   - slider path는 가능하면 `addCommandGUI()`의 controller `onChange`로 `slider` source를 기록한다.
   - command 값 계산은 현재 로직 그대로 유지한다.
3. `App.jsx`의 상단 "지금 보는 것" 카드 아래에 compact control status를 넣는다.
   - policy experiment일 때만 표시.
   - 표시 내용: `vx`, `vy`, `yaw`, 마지막 입력 source, 짧은 조작 힌트.
   - 모바일에서도 한 줄/두 줄로 접히게 유지한다.
   - 실제 로봇 조종처럼 읽히는 문구 금지. "정책 command" 또는 "브라우저 policy input"으로 표현한다.
4. event refresh를 보장한다.
   - keydown/keyup 또는 command change 때 `robotics-lab-control-change` custom event를 dispatch한다.
   - `App.jsx`는 이 event를 listen해 즉시 `readDemoState()`를 갱신한다.
   - 기존 500ms polling은 유지해 fallback으로 둔다.

## Acceptance Criteria

```bash
cd experiments/03-digital-twin/web
npm run build
node qa/workbench_check.mjs --exp=g1-walk
```

추가 수동 확인:

```js
window.demo.qaWorkbenchSummary().control
```

기대값:

- `enabled === true`
- `command`가 길이 3 배열
- `mapping`에 `ArrowUp`, `ArrowLeft`, `Q`, `E` 또는 동등 키 설명 포함
- 초기 상태에서 command는 `[0, 0, 0]`

## 검증 절차

1. AC 커맨드 실행.
2. UI copy가 real robot telemetry나 새 controller proof를 암시하지 않는지 확인.
3. `phases/m33-user-controllable-digital-twin/index.json` step 0 상태 갱신.

## 금지사항

- policy observation/action contract를 바꾸지 마라. 이유: command evidence 노출이 목표이지 policy 재학습/재계약이 아니다.
- fake force/contact overlay를 추가하지 마라. 이유: M34 전에는 runtime contact evidence가 아직 닫히지 않았다.
- `workbench_check.mjs`를 command transition 검증까지 비대하게 만들지 마라. 이유: Step 0은 summary/UI 계약, Step 1은 interaction smoke가 책임이다.
