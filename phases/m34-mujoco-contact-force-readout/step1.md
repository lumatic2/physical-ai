# Step 1: debug-summary-integration

## 읽어야 할 파일

- phases/m34-mujoco-contact-force-readout/step0.md - 왜: supported/unavailable 필드 결과를 이어받아야 함.
- experiments/03-digital-twin/web/src/main.js - 왜: `window.demo.qaWorkbenchSummary()`와 debug hooks가 있음.
- experiments/03-digital-twin/web/src/App.jsx - 왜: QA-only 또는 debug-only UI 노출 위치를 판단해야 함.
- docs/PRD.md - 왜: physics evidence readout의 public scope와 제외 범위 확인.

## 작업

step 0에서 실제로 읽힌 값만 QA/debug summary에 연결한다. UI에 노출할 경우 debug-only 또는 compact diagnostics로 제한하고, unsupported fields는 artifact에 남긴다.

## Acceptance Criteria

```bash
cd experiments/03-digital-twin/web
npm run build
node qa/workbench_check.mjs --exp=g1-rough-walk
```

## 검증 절차

1. QA summary에 physics readout claim level이 포함되는지 확인.
2. `contact-readout-probe.json`을 최종 evidence로 갱신.
3. ROADMAP M34 DoD 충족 시 `roadmap_sync.py complete --milestone M34 --evidence experiments/135-mujoco-contact-force-readout/verify/contact-readout-probe.json --summary "<한 줄 결과>"`.

## 금지사항

- public copy에서 "force measured"처럼 과장하지 마라. 이유: readout 필드의 의미와 단위가 확인된 뒤에만 공개 claim을 올린다.
- M33 command UI와 M34 readout UI를 한 카드에 과밀하게 합치지 마라. 이유: 사용자는 control state와 physics diagnostics를 구분해서 읽어야 한다.
