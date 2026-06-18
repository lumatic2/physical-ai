# Experiment 88: G1 Knee Contact Return Joint Optimizer

## Hypothesis

Exp87 found a no-fall visible branch: `9.47cm` pelvis drop and hip gate pass, but knee flexion, contact, slip, and terminal return were still short. The hypothesis here was that the branch could be pushed over the M19 gate by optimizing those remaining objectives jointly, without yet paying for another PPO finetune.

Web search continued to support the overall direction but also warned against raw pose tracking. External sources, accessed 2026-06-18:

- https://www.unitree.com/g1/ — G1's leg joint ranges and knee torque still make the squat pose physically plausible.
- https://agile.human2humanoid.com/ — ASAP shows Unitree G1 squat-like whole-body skills, but with learned tracking and residual deployment alignment.
- https://hugwbc.github.io/ — HUGWBC frames fine-grained humanoid locomotion as a unified whole-body control problem.
- https://arxiv.org/html/2502.12152v2 — G1 get-up work motivates refining discovered transitions under additional deployment constraints.

## Method

This runner copies exp87's three-phase WBC-lite controller and keeps the exp87 `sched-8cm-return-heavy` branch as the baseline. The new grid applies stronger joint pressure on:

- knee flexion reward/cost,
- stance foot XY stiffness and force limit,
- support/contact/slip costs,
- return-to-stand cost and return torque.

The optimizer score was also changed to weight knee shortfall, slip excess, contact loss, and final stand height more heavily than exp87.

Raw command:

```powershell
$env:OPENBLAS_NUM_THREADS='1'; C:\tmp\e34\Scripts\python.exe .\experiments\88-g1-knee-contact-return-joint-optimizer\run_knee_contact_return_joint_optimizer.py --seconds 6.0
```

Output files:

- `verify/knee-contact-return-joint-optimizer/result.json`
- `verify/knee-contact-return-joint-optimizer/knee-contact-return-joint-optimizer-summary.md`
- `verify/knee-contact-return-joint-optimizer/*/native-eval.json`

## Results

Verdict: `FAIL_VISIBLE_8CM_GATE`.

Best optimizer / best no-fall run:

- Attempt: `baseline-exp87-return-heavy`
- Visible drop: `0.0947m` PASS
- Knee delta: `0.430rad` FAIL
- Hip pitch delta: `0.370rad` PASS
- Both-foot contact ratio: `0.87` FAIL
- Foot slip: `0.106m` FAIL
- Final height: `0.6603m` FAIL
- Fell at: none

The stronger knee/contact variants did not improve the safe branch. They mostly crossed into collapse:

- `knee10-tight-slip`: knee `0.666rad` PASS and hip `0.504rad` PASS, but fell at `4.16s`, slip `0.357m`.
- `knee10-long-recap`: contact `0.90` PASS, but fell at `5.14s`, slip `0.364m`.
- `knee08-contact-heavy`: contact `0.92` PASS, but fell at `5.54s`, slip `0.352m`.

## Insights

The hand-written controller family is now the bottleneck. It can choose either:

- no-fall visible-depth with insufficient knee/contact/slip/return, or
- knee/contact-passing transient geometry that collapses with large slip.

That split is useful evidence. The remaining M19 work should stop widening this grid and switch to a learned residual or finetune that treats exp87's no-fall visible branch as the geometry teacher and exp86's 5cm branch as the safety teacher. The training target should make stance/contact a hard part of the action/control path, not only a scalar reward after the fact.
