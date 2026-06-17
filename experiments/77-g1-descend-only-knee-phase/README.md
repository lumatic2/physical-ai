# Experiment 77: G1 Descend-Only Knee Phase

## Hypothesis

Exp76 showed that a health-gated knee micro-phase can move the recoverable boundary to `7.70cm`, but stable knee flexion still plateaus at `0.516rad`, while harder knee push branches fall late. The next hypothesis was narrower: if the knee/hip micro-target is applied only during descend/hold and forcibly removed during return, the controller might keep the extra knee flexion without exciting the late return collapse.

## Method

This experiment reused the exp71 native event-triggered recapture evaluator and exp29 visible gate. It wrapped `EXP67.choose_blend` so `return_phase` becomes visible to the target patch, then applied the knee/hip micro-target only when `return_phase <= 0`.

Raw command:

```powershell
$env:OPENBLAS_NUM_THREADS='1'; C:\tmp\e34\Scripts\python.exe .\experiments\77-g1-descend-only-knee-phase\run_descend_only_knee_phase.py
```

Output files:

- `verify/descend-only-knee-phase/result.json`
- `verify/descend-only-knee-phase/descend-only-knee-phase-summary.md`
- `verify/descend-only-knee-phase/*/native-eval.json`

External sources, accessed 2026-06-18:

- https://pmc.ncbi.nlm.nih.gov/articles/PMC11769464/ — humanoid squatting needs trajectory optimization plus whole-body control.
- https://www.lirmm.fr/krut/pdf/2014_galdeano_ssd-0568454426/2014_galdeano_ssd.pdf — squat-like humanoid motion needs CoM, feet pose, ZMP regulation, and joint objectives together.
- https://arxiv.org/html/2502.13013v1 — G1-class work reports squat-to-height behavior via height tracking and curriculum.
- https://underactuated.mit.edu/humanoids.html — humanoid planning commonly reasons about CoM vertical motion and angular momentum.

## Results

Verdict: `PASS_RECOVERABLE_7CM_GATE`, not `PASS_VISIBLE_8CM_GATE`.

Best recoverable candidate:

- Attempt: `desc-k0p11-h0p02-p0p45-0p65-0p85-mh0p85`
- Visible drop: `0.0760m`
- Knee delta: `0.512rad`
- Hip pitch delta: `0.324rad`
- Foot contact ratio: `0.97`
- Foot slip: below gate
- Visible gate gap: `0.0040m` drop, `0.0877rad` knee, `0.0264rad` hip

Best no-fall score candidate:

- Attempt: `desc-k0p10-h0p03-p0p45-0p65-0p85-mh0p85`
- Visible drop: `0.0760m`
- Knee delta: `0.512rad`
- Hip pitch delta: `0.326rad`
- Final height: `0.7505m`

Best depth branch:

- Attempt: `desc-k0p11-h0p02-p0p45-0p65-0p85-mh0p75`
- Visible drop: `1.5285m`
- Knee delta: `0.534rad`
- Hip pitch delta: `0.340rad`
- Fell at: `5.64s`

## Insights

Return-phase cutoff did not unlock the stable knee plateau. It reduced the aggressive branch's achieved knee relative to exp76 and did not create an 8cm/no-fall/return solution. The best stable run regressed from exp76's `7.70cm / 0.516rad` to roughly `7.60cm / 0.512rad`.

This falsifies the simple "micro-target during return caused the late collapse" explanation. The failure is more structural: the current one-step target family can either preserve support and recover around 7.6-7.7cm, or push toward visible geometry and lose CoM/ZMP later. The next experiment should introduce an explicit trajectory optimizer or model-predictive schedule with separate objectives for knee flexion, pelvis height, CoM/ZMP margin, and terminal stand.
