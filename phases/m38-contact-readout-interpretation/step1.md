# Step 1 - Interpretation Evidence Smoke

## 읽어야 할 파일
- experiments/03-digital-twin/web/qa/physics_diagnostics_panel_check.mjs — 왜: visible diagnostics panel smoke pattern.
- experiments/03-digital-twin/web/qa/command_contact_timeline.mjs — 왜: source timeline evidence.

## 작업
Generate `experiments/139-contact-readout-interpretation/verify/contact-readout-interpretation.json` and verify local/live visible interpretation copy.

## Acceptance Criteria
```bash
node qa/contact_readout_interpretation_check.mjs --exp=g1-rough-walk --preset=rough-terrain
node qa/contact_readout_interpretation_check.mjs --exp=g1-rough-walk --preset=rough-terrain --live
```

## 금지사항
- Do not pass unless both supported and not-supported claims are present.

