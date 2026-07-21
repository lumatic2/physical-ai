# Changeset: GEN5 observable failure explorer

- Status: completed
- Target: ROADMAP `GEN5` step-3 — `failure-pattern-explorer`

## Scope

- 27개 timeout 전부를 GEN4 정본과 같은 분모로 집계한다.
- policy/suite/task/pattern filter와 12개 deterministic representative evidence row를 제공한다.
- `no_progress`와 `unknown` 정의, predicate·frame·manifest hash를 화면에 노출한다.
- 판정에 필요한 metric이 없는 세 양상을 disabled 상태로 명시한다.

## Verification

- [x] 27 = no_progress 6 + unknown 21이며 정책·suite filter count가 정본과 일치한다.
- [x] representative sample은 timeout만 포함하고 unknown·no_progress·두 정책을 포함한다.
- [x] predicate, frame range, manifest hash와 label definition이 visible하다.
- [x] unknown 숨김·성공 혼입·원인 진단 문구가 gate에서 FAIL한다.
- [x] production build와 desktop/mobile surface smoke가 PASS한다.

## Evidence

- `node qa/generalization_failure_check.mjs` — 27 failures, no_progress 6, unknown 21 PASS.
- filter counts — OpenVLA 25, π0.5 2; Goal 12, Object 8, Spatial 7.
- Browser surface — π0.5 2 → unknown 1, π0.5+Spatial 0 empty state, predicate·manifest·disabled patterns visible.
- Mobile — 390×844에서 4개 filter와 12 representative rows, horizontal overflow 없음.
- Screenshots — `verify/failure-explorer/local-desktop-dark.png`, `local-mobile-dark.png`.

## Claim boundary

- no_progress는 terminal-window end-effector displacement predicate만 뜻한다.
- unknown은 관측 predicate가 맞지 않았다는 뜻이며 숨은 원인 진단이 아니다.
- grasp relation, goal distance, object identity metric이 없어 세 양상은 disabled로 유지한다.
