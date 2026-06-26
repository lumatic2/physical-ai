# Step 0 - Episode Profile Contract

## Acceptance Criteria

- `obstacle-command-noise-v1` profile declares seed, target scenario, perturbation axes, and episode rows.
- UI/debug summary exposes the profile id, seed, episode count, and applied axes.
- `npm run build` passes.

## Notes

- Current browser runtime can safely apply policy command vectors and control noise.
- Friction/mass/sensor-noise randomization remains an explicit boundary until runtime mutation or MJCF variants are implemented.
