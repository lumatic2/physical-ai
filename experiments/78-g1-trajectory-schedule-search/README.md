# Experiment 78: G1 Trajectory Schedule Search

## Hypothesis

Exp77 falsified the idea that return-phase knee micro-targets alone caused the late collapse. The next hypothesis was that an explicit trajectory schedule, closer to a coarse MPC profile, could coordinate pelvis height, knee/hip flexion, return timing, CoM/ZMP weights, and terminal stand better than a one-step `build_target` patch.

## Method

The experiment reused the exp71 event-triggered native evaluator and exp29 visible gate, but wrapped `EXP67.choose_blend` so the controller sees a scheduled trajectory fraction rather than the original linear `desired_fraction`.

The sweep changed:

- target drop and max blend
- recapture trigger, hold, and return duration
- descend and return profile curvature
- knee/hip pose shaping window
- support/ZMP/slip weight boost
- terminal return profile

Raw command:

```powershell
$env:OPENBLAS_NUM_THREADS='1'; C:\tmp\e34\Scripts\python.exe .\experiments\78-g1-trajectory-schedule-search\run_trajectory_schedule_search.py
```

Output files:

- `verify/trajectory-schedule-search/result.json`
- `verify/trajectory-schedule-search/trajectory-schedule-summary.md`
- `verify/trajectory-schedule-search/*/native-eval.json`

External sources, accessed 2026-06-18:

- https://pmc.ncbi.nlm.nih.gov/articles/PMC11769464/ — TP-MPC plus WBC optimizes humanoid squat trajectories and tracks them under constraints.
- https://www.mdpi.com/1424-8220/25/2/435 — same squat paper; rough trajectory optimization plus WBC tracking motivates this schedule search.
- https://arxiv.org/html/2502.13013v1 — G1-class work reports squat-to-height behavior using height-tracking reward and curriculum.
- https://underactuated.mit.edu/humanoids.html — humanoid planning links CoM plans to whole-body plans through centroidal dynamics.

## Results

Verdict: `PASS_RECOVERABLE_7CM_GATE`, not `PASS_VISIBLE_8CM_GATE`.

Best recoverable/no-fall candidate:

- Attempt: `focus00`
- Visible drop: `0.0769m`
- Knee delta: `0.515rad`
- Hip pitch delta: `0.316rad`
- Final height: `0.7494m`
- Visible gate gap: `0.0031m` drop, `0.0845rad` knee, `0.0338rad` hip

Best depth branch:

- Attempt: `sched00-eg2p9-wb1p00`
- Visible drop: `1.5296m`
- Knee delta: `0.574rad`
- Hip pitch delta: `0.262rad`
- Fell at: `5.24s`

## Insights

The finite schedule search did not close M19. It improved over exp77 but did not beat exp76's best recoverable result (`7.70cm`, knee `0.516rad`). The stable branch remains pinned around `7.6-7.7cm` and `0.515rad` knee flexion, while deeper or more knee-biased schedules go to late collapse.

This is stronger evidence that the current controller family is missing a real trajectory/control degree of freedom, not just better timing constants. The next useful step is to stop wrapping exp71 from the outside and either copy the native evaluator for a real internal trajectory optimizer, or switch back to training with a height/knee/CoM-ZMP curriculum informed by the 7.7cm recoverable corridor.
