# Changeset: GEN5 public reviewer release

- Status: completed — 2026-07-21 production release and live reviewer gate PASS
- Target: ROADMAP `GEN5` step-5 — `public-reviewer-release`

## Scope

- 최종 route의 desktop dark/light, 390px mobile과 interactive reviewer flow를 검증한다.
- registry 200/hash, console/network, denominator, unknown, drilldown, claim boundary를 release gate로 묶는다.
- 5분 reviewer checklist와 local/live report를 남긴다.
- 사람 visual confirmation 뒤에만 production alias를 갱신한다.

## Verification

- [x] local release gate와 최종 screenshots가 PASS한다 — 60 pairs, 27 failures, registry SHA-256 `4ab5b110aee5...`.
- [x] 사용자가 직접 시각 확인을 명시적으로 생략하고 production 배포를 승인했다.
- [x] production deploy 후 live route·asset·console/network·mobile이 PASS한다 — Vercel `dpl_6eKWczLY8u6U9ByFRBp3hhxKzC3G`, console/network error 0, mobile overflow 0.
- [x] general winner/live/real robot/root-cause relabel이 차단된다 — 두 LAB3 deep link와 negative relabel probe PASS.
- [x] final report·ROADMAP·harness ledger와 clean git state를 완료한다 — `archive/reports/2026-07-21-gen5-public-generalization-lab.md`.

## Result

- Public: `https://robotics.askewly.com/generalization-lab.html`
- Evidence: `experiments/03-digital-twin/web/verify/generalization-lab/live-release-report.json`
- LAB3 regression: `experiments/03-digital-twin/web/verify/arm-lab/gen5-live-player-report.json`
- Residual boundary: 120개 episode 중 공개 dual-camera replay는 canonical LAB3 두 건이며, 나머지 118건은 hash-level evidence다.
