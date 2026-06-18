# Experiment 84: G1 Pose-Biased Multi-Step WBC Projection

## Hypothesis

Before running another M19 probe, I checked whether Unitree G1 squat is a plausible target at all. The answer is yes for hardware/posture feasibility, but not as a solved balance-policy problem.

External sources, accessed 2026-06-18:

- https://www.unitree.com/g1/ — Unitree lists G1 as a 23-43 joint humanoid with 6 DoF per leg, knee torque of `90N.m` / `120N.m`, and knee/hip joint ranges large enough for squat geometry.
- https://docs.quadruped.de/projects/g1/html/operation_1.2.html — G1 operation docs expose `Squat Mode`, but describe the transition as having no balance control. That matches our split: posture is possible, controlled autonomous squat still needs a stance-aware policy/controller.
- https://arxiv.org/html/2502.13013v1 — HOMIE reports humanoid policies that walk and squat to specific heights using RL, height tracking reward, and upper-body pose curriculum.
- https://hub-robot.github.io/ — HuB validates extreme balance tasks on Unitree G1 and includes `Deep Squat` in the evaluation set.

Given exp83 already produced the first `>=8cm` no-fall/contact/slip run, this experiment tested whether adding targeted knee/hip pose residual inside the same multi-step stance guard corridor can close the exp29 visible gate.

## Method

The runner copies exp83's multi-step candidate rollout selector and adds two mechanisms:

- target-level pose bias: health-gated residuals on left/right knee and hip pitch actuator targets.
- horizon pose scoring: shortfall costs for achieved knee delta and hip pitch delta after the cloned candidate rollout.

It keeps exp83's safe `h4-visible-8cm-slow` corridor as the base, then sweeps mild pose, stronger pose, guarded return, and hip-dominant variants.

Raw command:

```powershell
$env:OPENBLAS_NUM_THREADS='1'; C:\tmp\e34\Scripts\python.exe .\experiments\84-g1-pose-biased-multistep-wbc-projection\run_pose_biased_multistep_wbc_projection.py --seconds 6.0
```

Output files:

- `verify/pose-biased-multistep-wbc-projection/result.json`
- `verify/pose-biased-multistep-wbc-projection/pose-biased-multistep-wbc-projection-summary.md`
- `verify/pose-biased-multistep-wbc-projection/*/native-eval.json`

## Results

Verdict: `FAIL_VISIBLE_8CM_GATE`.

Best no-fall run:

- Attempt: `hip-dominant-h4-k0p10-h0p18`
- Visible drop: `0.2843m` PASS
- Knee delta: `0.631rad` PASS
- Hip pitch delta: `0.198rad` FAIL
- Both-foot contact ratio: `0.98` PASS
- Foot slip: `0.034m` PASS
- Fell at: none
- Final height: `0.4717m`, return still pending
- Verdict: `POSE_GATE_PENDING`

The strongest hip-dominant branch reached the visible pose geometry but fell:

- Attempt: `hip-dominant-h4-k0p08-h0p14`
- Visible drop: `0.953m`
- Knee delta: `0.699rad`
- Hip pitch delta: `0.361rad` PASS
- Contact ratio: `0.95` PASS
- Foot slip: `0.203m` FAIL
- Fell at: `5.74s`

## Insights

The web search supports continuing M19: G1 can physically enter squat-like postures, and current humanoid literature reports G1/G1-class deep squat or height-commanded squat policies. The local experiment also advanced the native evidence: exp83 had `8.27cm` no-fall/contact/slip but missed knee and hip; exp84 gets no-fall/contact/slip with both `>=8cm` depth and knee gate passing.

The remaining blocker is narrower now: hip flexion and terminal stand recovery are coupled. When hip flexion is forced enough to pass, the model falls or slips; when stance is preserved, hip flexion stays around `0.13-0.20rad` and the robot ends crouched. The next experiment should split descend and recover into two controller branches: a hip-forward descent branch with explicit slip recapture, followed by a separate terminal stand-up branch instead of asking one horizon selector to optimize both.
