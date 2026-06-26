# Step 1 - Scorecard Local/Live Evidence

## Acceptance Criteria

- `node qa/randomized_episode_scorecard.mjs --profile=obstacle-command-noise-v1` passes locally.
- `node qa/randomized_episode_scorecard.mjs --live --profile=obstacle-command-noise-v1` passes on `robotics.askewly.com`.
- Aggregated evidence exists at `experiments/143-randomized-episode-scorecard/verify/randomized-episode-scorecard.json`.

## Notes

- PASS means every episode finishes without NaN/fall/console error and records a bounded score, not that obstacle avoidance is solved.
