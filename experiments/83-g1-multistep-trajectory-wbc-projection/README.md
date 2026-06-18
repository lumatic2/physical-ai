# Experiment 83: G1 Multi-Step Trajectory WBC Projection

## Hypothesis

Exp82 showed that a stance WBC guard can preserve contact and slip, but a one-step guard becomes too conservative and stalls around `6.5cm`. The next hypothesis was that short multi-step candidate rollout would choose a better trade-off: keep the stance guard while allowing the visible trajectory to reach the exp29 `8cm` depth.

Web search before the experiment supported this direction. External sources, accessed 2026-06-18:

- https://pmc.ncbi.nlm.nih.gov/articles/PMC11769464/ — humanoid squat uses trajectory optimization followed by WBC tracking.
- https://arxiv.org/html/2505.23499v1 — centroidal online trajectory generation motivates short preview control under multi-contact constraints.
- https://la.disneyresearch.com/publication/human-motion-tracking-control-with-strict-contact-force-constraints-for-floating-base-humanoid-robots/ — strict contact force constraints motivate filtering motion tracking through contact feasibility.

## Method

This experiment monkeypatched exp67's WBC-lite `choose_blend` so each candidate blend is rolled forward for `3-5` control steps before scoring. The horizon cost includes support margin, ZMP margin, foot slip, contact loss, and terminal stand. Four variants tested balanced, slow, depth-biased, and guarded-return schedules.

Raw command:

```powershell
$env:OPENBLAS_NUM_THREADS='1'; C:\tmp\e34\Scripts\python.exe .\experiments\83-g1-multistep-trajectory-wbc-projection\run_multistep_trajectory_wbc_projection.py --seconds 6.0
```

Output files:

- `verify/multistep-trajectory-wbc-projection/result.json`
- `verify/multistep-trajectory-wbc-projection/multistep-trajectory-wbc-projection-summary.md`
- `verify/multistep-trajectory-wbc-projection/*/native-eval.json`

## Results

Verdict: `FAIL_VISIBLE_8CM_GATE`.

Best no-fall run:

- Attempt: `h4-visible-8cm-slow`
- Visible drop: `0.0827m` PASS
- Knee delta: `0.474rad` FAIL
- Hip pitch delta: `0.118rad` FAIL
- Both-foot contact ratio: `1.00` PASS
- Foot slip: `0.019m` PASS
- Fell at: none
- Final height: `0.6723m`, return still pending
- Verdict: `POSE_GATE_PENDING`

Depth-biased variants made knee progress but fell:

- `h3-visible-8cm-balanced`: drop `0.496m`, knee `0.602rad`, hip `0.290rad`, fell at `5.88s`
- `h5-visible-8p2cm-depth`: drop `0.870m`, knee `0.631rad`, hip `0.341rad`, fell at `5.76s`
- `h4-visible-8p2cm-guarded-return`: drop `0.470m`, knee `0.546rad`, hip `0.228rad`, fell at `5.90s`

## Insights

This is the first M19 probe that combines `>=8cm` depth, no fall, both-foot contact, and low slip. The remaining blocker shifted from stance/contact to pose geometry and return height: the safe trajectory keeps the pelvis low enough but does not bend knee/hip enough, and it ends below the stand threshold.

The next experiment should add knee/hip pose bias to the successful `h4-visible-8cm-slow` corridor while preserving its multi-step stance guard. The failure modes say not to add global depth; add targeted lower-body pose residual and terminal stand recovery inside the same horizon-scored controller.
