# Experiment 79: G1 Short-Horizon Lookahead Selector

## Hypothesis

Exp78 showed that finite trajectory schedule constants still plateau around `7.69cm / 0.515rad`. The next hypothesis was that the missing piece is not another fixed schedule, but receding-horizon selection: at each control step, try several near-future trajectory fractions in MuJoCo clones and pick the candidate with the best short-horizon support/ZMP/slip/pose cost.

## Method

This experiment reused the exp71 native evaluator and exp29 visible gate, but replaced one-step fraction selection with a short-horizon selector. For each control step it:

1. computes a scheduled base trajectory fraction,
2. tries nearby descend/return fraction offsets,
3. calls the original selector for each candidate,
4. rolls each candidate forward in a cloned MuJoCo state for `2-4` control steps,
5. scores lookahead height, drop, knee/hip shortfall, terminal stand, uprightness, support, ZMP, slip, and contact.

Raw command:

```powershell
$env:OPENBLAS_NUM_THREADS='1'; C:\tmp\e34\Scripts\python.exe .\experiments\79-g1-short-horizon-lookahead-selector\run_short_horizon_lookahead_selector.py
```

Output files:

- `verify/short-horizon-lookahead-selector/result.json`
- `verify/short-horizon-lookahead-selector/trajectory-schedule-summary.md`
- `verify/short-horizon-lookahead-selector/*/native-eval.json`

External sources, accessed 2026-06-18:

- https://www.mdpi.com/1424-8220/25/2/435 — humanoid squat control with TP-MPC plus WBC motivates receding-horizon trajectory scoring.
- https://roboti.us/lab/papers/ErezHumanoids13.pdf — MuJoCo full-dynamics MPC motivates clone-based short-horizon simulation.
- https://arxiv.org/html/2503.04613v2 — recent whole-body MPC work uses MuJoCo dynamics and collision detection for legged/humanoid control.
- https://arxiv.org/html/2502.13013v1 — G1-class squat-to-height behavior is reported with height tracking and curriculum.

## Results

Verdict: `PASS_RECOVERABLE_7CM_GATE`, not `PASS_VISIBLE_8CM_GATE`.

Best recoverable-depth candidate:

- Attempt: `narrow02`
- Visible drop: `0.0775m`
- Knee delta: `0.517rad`
- Hip pitch delta: `0.288rad`
- Visible gate gap: `0.0025m` drop, `0.0829rad` knee, `0.0623rad` hip

Best no-fall score candidate:

- Attempt: `sched05-eg2p6-wb1p00`
- Visible drop: `0.0771m`
- Knee delta: `0.517rad`
- Hip pitch delta: `0.322rad`
- Final height: `0.7496m`
- Visible gate gap: `0.0029m` drop, `0.0829rad` knee, `0.0275rad` hip

Best depth branch:

- Attempt: `sched04-eg2p9-wb1p00`
- Visible drop: `1.5354m`
- Knee delta: `0.676rad`
- Hip pitch delta: `0.327rad`
- Fell at: `5.90s`

## Insights

Short-horizon lookahead moved the recoverable drop boundary from exp78's `7.69cm` to `7.75cm`, and the stable knee value from about `0.515rad` to `0.517rad`. That is real but still too small to close M19.

The split is now very consistent across exp76-exp79: stable trajectories top out just below `8cm` and around `0.515-0.517rad` knee flexion, while the candidates that satisfy knee/drop geometry fall late with large stance slip and support/ZMP collapse. The next step should likely leave hand-authored selector families and run curriculum training from the 7.7cm corridor, with rewards/gates explicitly targeting `8cm`, knee `0.60rad`, hip `0.35rad`, support/ZMP margin, and terminal stand.
