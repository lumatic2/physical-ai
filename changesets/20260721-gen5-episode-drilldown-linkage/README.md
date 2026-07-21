# Changeset: GEN5 aggregate-to-episode traceability

- Status: completed
- Target: ROADMAP `GEN5` step-4 — `episode-drilldown-linkage`

## Scope

- 공개 가능한 Spatial task-05 state-00/01 cell에만 LAB3 replay deep link를 제공한다.
- URL은 episode뿐 아니라 source cell, OpenVLA policy, manifest SHA를 함께 고정한다.
- LAB3는 generalization registry와 arm registry를 교차 검증한 뒤에만 dual-camera replay를 연다.
- source cell·manifest·episode·dataset tree·main/wrist camera hash를 QA summary와 화면에 노출한다.

## Verification

- [x] pass/fail 두 링크가 source cell·policy·manifest와 byte-stable URL로 일치한다.
- [x] LAB3 QA summary의 episode·dataset·camera hash가 source registry와 일치한다.
- [x] wrong episode, stale manifest, policy/camera relabel이 FAIL한다.
- [x] 기존 query 없는 LAB3 pass/fail 동작이 유지된다.
- [x] production build와 실제 browser drilldown이 PASS한다.

## Evidence

- `node qa/generalization_drilldown_check.mjs` — 두 source-bound LAB3 episode와 네 negative relabel probe PASS.
- `python qa/arm_lab_player_check.py --prefix gen5-step4-regression` — 기존 query 없는 LAB3 desktop/mobile/error 회귀 PASS.
- Browser pass — Spatial T05 state-00 → PASS, manifest `1197f1e4…9585a47`, camera `a26ae72c…a83710` / `949032b4…365ceb`.
- Browser fail — Spatial T05 state-01 → FAIL, manifest `d81c45cd…3f196a`, camera `95bd112d…e4a104` / `7351f235…2d0754`.
- Registry SHA-256 — `4ab5b110aee5d490a32964f7c696cc49c990eadbde10d10d5733d3b5d428445d`.

## Cleanup

- LAB3 회귀가 중복 생성한 screenshot 4개는 제거했다.
- 전용 provenance screenshot과 회귀 JSON report는 보존했다.
