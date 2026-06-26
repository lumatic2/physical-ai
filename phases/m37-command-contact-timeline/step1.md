# Step 1 - Local/Live Timeline Evidence

## 읽어야 할 파일
- experiments/03-digital-twin/web/qa/command_contact_timeline.mjs — 왜: local/live evidence generator.
- ROADMAP.md — 왜: M37 DoD and evidence path.

## 작업
Run local and live timeline smoke and write `experiments/138-command-contact-timeline/verify/command-contact-timeline.json`.

## Acceptance Criteria
```bash
node qa/command_contact_timeline.mjs --exp=g1-rough-walk --preset=rough-terrain
node qa/command_contact_timeline.mjs --exp=g1-rough-walk --preset=rough-terrain --live
```

## 금지사항
- Do not infer causality beyond same-run command/readout correlation.

