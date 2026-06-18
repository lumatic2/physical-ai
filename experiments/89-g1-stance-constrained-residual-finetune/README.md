# Experiment 89: G1 Stance-Constrained Residual Finetune

## Hypothesis

Exp88 showed that the hand-written controller family can either stay safe but miss knee/contact/return, or hit knee/contact transiently and collapse. The next hypothesis was that a learned residual finetune from the exp80 visible-geometry checkpoint could keep the visible pose signal while making stance/contact/slip/return part of the training objective.

Web search supports this direction but not as a guarantee. External sources, accessed 2026-06-18:

- https://arxiv.org/html/2510.05070v1 — residual humanoid learning motivates refining a broad motion-tracking policy with task-specific residual constraints.
- https://arxiv.org/html/2501.02116v1 — humanoid whole-body survey notes that pure learning lacks flexibility around contacts, which matches the need for integrated stance constraints.
- https://www.mdpi.com/1424-8220/25/2/435 — humanoid squat control literature emphasizes foot forces, dynamic constraints, MPC trajectory, and WBC tracking.

## Method

This experiment adds `StanceConstrainedResidualSquat`, a subclass of the exp80 corridor curriculum env. It preserves the policy observation/action shape, so the exp80 visible-geometry checkpoint can be restored, but changes the reward balance:

- keep visible drop and knee/hip pose rewards,
- increase support/contact/slip health rewards,
- add a residual-budget term that penalizes rough action changes when slip/support health is low,
- use stricter `support_floor=0.0` and `slip_limit=0.055`,
- keep terminal stand reward during return.

Raw command:

```powershell
$env:OPENBLAS_NUM_THREADS='1'; C:\tmp\e34\Scripts\python.exe .\experiments\89-g1-stance-constrained-residual-finetune\run_stance_constrained_residual_finetune.py --train --timesteps 20000 --target-drop 0.080 --support-floor 0.000 --slip-limit 0.055 --seconds 6.0
```

Output files:

- `verify/target-0p080-slip-0p06/result.json`
- `verify/target-0p080-slip-0p06/native-eval.json`
- `verify/target-0p080-slip-0p06/stance-constrained-residual-summary.md`
- `verify/target-0p080-slip-0p06/train/params.pkl`
- `verify/target-0p080-slip-0p06/train/rewards.txt`

## Results

Verdict: `DEPTH_PENDING_7CM`, not `PASS_VISIBLE_8CM_GATE`.

Native rollout after 20k finetune:

- Visible drop: `0.0632m` FAIL
- Knee delta: `0.578rad` FAIL
- Hip pitch delta: `0.500rad` PASS
- Fell at: none
- Final height: `0.7588m` PASS
- Both-foot contact ratio: `0.37` FAIL
- Foot slip: `3.250m` FAIL
- Minimum support margin: `-0.1077m` FAIL
- First support breach: `1.38s`
- First slip breach: `1.70s`

Training reward moved only slightly:

- step `0`: `151.996`
- step `20480`: `153.078`
- step `40960`: `153.598`

## Insights

This did not close M19, and it did not materially improve the stance failure. The learned residual kept the no-fall/return behavior, but it did so by retreating to a 6.3cm transition while still allowing large foot slip and poor contact ratio.

That rules out another small reward-only finetune as the next best step. The remaining path should move the stance constraint into the native control layer itself: either train with a WBC/qfrc action wrapper in the loop, or export exp87's no-fall visible schedule as a supervised target for a controller that directly enforces stance-foot force/position constraints during rollout.
