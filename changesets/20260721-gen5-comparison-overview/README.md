# Changeset: GEN5 comparison overview

- Status: completed
- Target: ROADMAP `GEN5` step-2 — `comparison-overview`

## Scope

- `/generalization-lab.html`: 기존 LAB3 토큰을 재사용하는 공개 비교 route.
- stat summary band: visible denominator와 정책별 raw success count, paired difference.
- semantic comparison table: suite/task/state/instruction과 두 정책 outcome.
- suite/task filters: 60→20→5 pair로 분모와 raw count를 같은 상태에서 재계산.
- `qaGeneralizationSummary()`: filter, raw counts, execution contract와 evidence hash를 노출.

## Verification

- [x] all view가 35/60, 58/60, +23/60과 fixed bootstrap interval을 보인다.
- [x] suite view 20쌍, task view 5쌍으로 raw count가 재계산된다.
- [x] planned/included/excluded/unmatched가 화면에 보인다.
- [x] zero denominator, hidden exclusion과 rounded-only summary가 FAIL한다.
- [x] build·desktop/mobile·dark/light와 keyboard focus를 확인한다.

## Evidence

- `node qa/generalization_overview_check.mjs` — 60쌍·120 episode, filter와 raw count gate PASS.
- `npm run build` — `/generalization-lab.html` production entry build PASS.
- Browser surface smoke — Goal 20쌍 → Goal task-03 5쌍, evidence row 선택, 390px `scrollWidth <= innerWidth`.
- Screenshots — `local-desktop-dark.png`, `local-desktop-light.png`, `local-mobile-dark.png`.
- Registry SHA-256 — `1bfe68019c6e2baebdd15c446323b4f171fad8839f329b40fec9bd928db12f68`.

## 요소 결정

- `stat-summary-grid`: 낮은 시각적 강도로 분모·정책별 raw count·paired 차이를 같은 높이에 둔다.
- `interactive-data-table`: 60개 task-state의 행·열 정렬과 필터 후 분모 변화를 보존한다.
- `responsive-content-grid`는 행 비교 정렬을 깨뜨리므로 matrix에는 쓰지 않고 모바일에서 행을 의미 단위로 적층한다.
- 기존 arm-lab 색·타이포·간격 토큰을 그대로 사용하고 cyan은 상태·초점 신호에만 제한했다.
- 스타일 자가검토: 토큰 파생, 제한된 accent, 한 개의 주 초점, 상태 완결성, 실험적 장식 배제 모두 통과; 금지 패턴 0건.
