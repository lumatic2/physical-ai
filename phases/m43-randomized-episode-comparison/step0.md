# Step 0 - Comparison Contract

## Read First

- `experiments/03-digital-twin/web/src/environmentPresets.js` - why: owns M42 episode profile and will own comparison profile metadata.
- `experiments/03-digital-twin/web/src/main.js` - why: environment QA summary exposes debug contracts to UI and Playwright.
- `experiments/03-digital-twin/web/src/App.jsx` - why: debug UI panel must show comparison profile and baseline episode.

## Work

Add an episode comparison profile that references `obstacle-command-noise-v1`, selects `seed-0001-forward-clean` as baseline, and declares compared metrics and drift thresholds.

## Acceptance Criteria

```bash
cd experiments/03-digital-twin/web
npm run build
```

## Forbidden

- Do not claim sim-to-real or autonomous obstacle avoidance.
- Do not mutate physics parameters for comparison; compare already executed episode outcomes.
