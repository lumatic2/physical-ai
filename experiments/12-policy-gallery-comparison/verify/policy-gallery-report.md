# Policy Gallery Comparison

| Policy | Terrain | Live | forward dx | forward drift y | strafe L dy | strafe R dy | turn L dyaw | turn R dyaw | diagonal dist | min h | failures |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| go1-walk | flat | no | 5.89 | 0.18 | 2.63 | -2.44 | -1.91 | 1.86 | 5.06 | 0.30 | 0 |
| spot-walk | flat | no | 5.47 | 0.22 | 3.02 | -3.01 | -1.67 | 1.64 | 4.98 | 0.44 | 0 |
| go1-rough-walk | rough | yes | 5.83 | 0.11 | 2.61 | -2.47 | -1.91 | 1.86 | 4.98 | 0.30 | 0 |
| spot-rough-walk | rough | yes | 5.20 | 0.54 | 2.92 | -2.96 | -1.57 | 2.17 | 4.99 | 0.43 | 0 |
| g1-rough-walk | rough | yes | 5.03 | 0.06 | 1.36 | -1.46 | 2.34 | -1.73 | 3.62 | 0.74 | 0 |
| barkour-walk | flat | yes | 2.75 | 0.50 | -4.52 | 3.53 | -2.99 | -2.88 | 5.34 | 0.26 | 0 |

## Readout

- All compared sweeps have `failures=0`: no fall, NaN, or console errors in the selected raw reports.
- Go1 remains the cleanest forward baseline; rough Go1 still keeps strong forward progress.
- Spot is stable, but rough terrain shows more command drift than Go1 in the existing M12 reports.
- G1 rough contributes the humanoid axis; it is comparable by protocol but not by morphology.
- Barkour adds a new 465-d history-observation policy. It walks forward after user-facing `vx` is sign-flipped into the env command convention, but its lateral/yaw conventions should be labeled before presenting as intuitive teleop.

## Sources

- `go1-walk`: `experiments/07-command-terrain-robustness/verify/go1-command-sweep.json`
- `spot-walk`: `experiments/07-command-terrain-robustness/verify/spot-command-sweep.json`
- `go1-rough-walk`: `experiments/07-command-terrain-robustness/verify/go1-rough-command-sweep-live.json`
- `spot-rough-walk`: `experiments/07-command-terrain-robustness/verify/spot-rough-command-sweep-live.json`
- `g1-rough-walk`: `experiments/08-policy-expansion/verify/g1-rough-command-sweep-live.json`
- `barkour-walk`: `experiments/10-barkour-rl-walk/verify/barkour-command-sweep-live.json`
