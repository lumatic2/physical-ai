# Step 1 - Comparison Local/Live Evidence

## Read First

- `experiments/03-digital-twin/web/qa/randomized_episode_scorecard.mjs` - why: comparison QA should reuse its episode execution contract and metrics.
- `experiments/143-randomized-episode-scorecard/verify/randomized-episode-scorecard.json` - why: shape of prior scorecard evidence.

## Work

Create `qa/randomized_episode_comparison.mjs` that runs the same profile, compares each non-baseline episode against the baseline, and writes local/live plus aggregate evidence.

## Acceptance Criteria

```bash
cd experiments/03-digital-twin/web
node qa/randomized_episode_comparison.mjs --profile=obstacle-command-noise-v1
node qa/randomized_episode_comparison.mjs --live --profile=obstacle-command-noise-v1
```

## Forbidden

- Do not pass comparison just because scorecard passed; require explicit delta rows.
- Do not hide failed episode rows from evidence.
