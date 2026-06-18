# Experiment 86: G1 Three-Phase Recapture Stand Controller

## Hypothesis

Exp85 showed that switching directly from hip-forward crouch to default stand target causes delayed falls. The hypothesis here was that a middle recapture phase can make the crouch recoverable: first reach a visible descent, then hold a low crouch while prioritizing support/ZMP/slip, then release into terminal stand-up.

Web search supports this direction. External sources, accessed 2026-06-18:

- https://arxiv.org/html/2504.18698v1 — biped push-recovery work explicitly constrains ZMP to remain inside the support polygon.
- https://scaron.info/robotics/capture-point.html — capture point frames balance recovery as stopping divergent CoM dynamics before changing the contact/posture objective.
- https://www.mdpi.com/1424-8220/25/2/435 — humanoid squat work combines trajectory optimization and WBC rather than a single monolithic tracking objective.

## Method

This runner copies exp85 and reinterprets the existing `return_phase` into three internal modes:

- `descend`: use hip/knee pose bias and visible squat target.
- `recapture`: hold a bounded crouch target while multiplying support, ZMP, slip, and recapture-height costs.
- `stand`: disable pose bias, release IK, and use default stand target with stronger stand/contact/slip costs.

Raw command:

```powershell
$env:OPENBLAS_NUM_THREADS='1'; C:\tmp\e34\Scripts\python.exe .\experiments\86-g1-three-phase-recapture-stand-controller\run_three_phase_recapture_stand_controller.py --seconds 6.0
```

Output files:

- `verify/three-phase-recapture-stand-controller/result.json`
- `verify/three-phase-recapture-stand-controller/three-phase-recapture-stand-controller-summary.md`
- `verify/three-phase-recapture-stand-controller/*/native-eval.json`

## Results

Verdict: `FAIL_VISIBLE_8CM_GATE`.

Best no-fall run:

- Attempt: `safe-recap1p6-hip0p14`
- Visible drop: `0.0507m` FAIL
- Knee delta: `0.373rad` FAIL
- Hip pitch delta: `0.182rad` FAIL
- Both-foot contact ratio: `0.98` PASS
- Foot slip: `0.052m` PASS
- Final height: `0.7387m`, just under the `0.74m` return gate
- Fell at: none
- Verdict: `DEPTH_PENDING_8CM`

Depth-push branches were not recoverable:

- `guarded-depth7-hip0p14`: drop `1.510m`, fell at `5.52s`
- `guarded-depth8-hip0p15`: drop `1.500m`, hip `0.370rad` PASS, fell at `5.54s`
- `guarded-depth9-hip0p16`: drop `1.518m`, fell at `5.24s`
- `guarded-depth8-longrecap`: drop `1.526m`, fell at `5.04s`

## Insights

The recapture phase does help the recovery side: the safe branch returns near stand height with contact and slip intact and no fall. However, increasing depth/pose pressure still sends the system into the delayed collapse branch. The short-horizon controller can choose a trajectory that looks acceptable through the recapture window but becomes unrecoverable during stand-up.

M19 should not continue by adding more hand-tuned phase costs. The next aligned step is to turn the exp84/86 corridor into an optimizer or training target: keep the 5cm recoverable 3-phase controller as a safety teacher, and learn/search a depth schedule that expands 5cm -> 8cm under explicit terminal recovery constraints.
