# Step 0 - Interpretation Copy And UI

## 읽어야 할 파일
- README.md — 왜: public claim boundary copy.
- experiments/README.md — 왜: experiment index row for M36-M38 evidence.
- experiments/03-digital-twin/web/src/App.jsx — 왜: visible diagnostics interpretation text.
- experiments/138-command-contact-timeline/verify/command-contact-timeline.json — 왜: interpretation source evidence.

## 작업
Add explicit supported / not-supported interpretation text for browser MuJoCo runtime readout.

## Acceptance Criteria
```bash
npm run build
```

## 금지사항
- Do not turn same-run timeline evidence into calibrated causality or real-robot telemetry claims.

