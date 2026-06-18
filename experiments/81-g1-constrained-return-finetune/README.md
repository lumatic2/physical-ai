# Experiment 81: G1 Constrained Return Finetune

## Hypothesis

Exp80 proved that a restored PPO policy can reach visible squat geometry, but it destroyed contact, support, slip, and return. The next hypothesis was that a second-stage finetune from the exp80 checkpoint could preserve the visible pose while making contact, support margin, low slip, and terminal stand more expensive.

Web search before the experiment supported this direction. External sources, accessed 2026-06-18:

- https://arxiv.org/html/2502.12152v2 — G1 getting-up work uses a two-stage process where discovered motions are refined into smoother deployable motions.
- https://www.mdpi.com/2313-7673/10/11/783 — two-stage sit-stand RL motivates separating transient contact-rich discovery from constrained execution.
- https://www.mdpi.com/1424-8220/25/2/435 — humanoid squat control literature emphasizes foot forces, dynamic constraints, MPC trajectory, and WBC tracking.

## Method

This experiment added `ConstrainedReturnSquat`, a subclass of exp80's corridor environment. It starts from the exp80 visible-geometry checkpoint and changes the reward balance:

- lower drop/knee/hip reward weights,
- much higher support margin and terminal-stand weights,
- new both-foot contact, slip-health, support-health, height-gate, and action-smoothness rewards,
- stricter `slip_limit=0.06` and `support_floor=0.0`.

Raw command:

```powershell
$env:OPENBLAS_NUM_THREADS='1'; C:\tmp\e34\Scripts\python.exe .\experiments\81-g1-constrained-return-finetune\run_constrained_return.py --train --timesteps 20000 --target-drop 0.080 --slip-limit 0.06 --support-floor 0.000 --seconds 6.0
```

Output files:

- `verify/target-0p080-slip-0p06/result.json`
- `verify/target-0p080-slip-0p06/native-eval.json`
- `verify/target-0p080-slip-0p06/constrained-return-summary.md`
- `verify/target-0p080-slip-0p06/train/params.pkl`
- `verify/target-0p080-slip-0p06/train/rewards.txt`

## Results

Verdict: `DEPTH_PENDING_7CM`, not `PASS_VISIBLE_8CM_GATE`.

Native rollout:

- Visible drop: `0.0616m`, so visible-depth FAIL
- Max knee delta: `0.5942rad`, short by `0.0058rad`
- Max hip pitch delta: `0.5263rad` PASS
- Fell at: none
- Final height: `0.7634m`, so return-to-stand PASS
- Both-foot contact ratio: `0.38` FAIL
- Foot slip: `3.271m` FAIL
- Minimum support margin: `-0.1062m` FAIL
- Joint limit violation: `0.0rad` PASS

Compared with exp80, the terminal stand recovered and the policy did not fall, but visible depth regressed from `11.26cm` to `6.16cm`. Slip/contact still failed badly.

## Insights

The two-stage idea was directionally useful for terminal return but insufficient for stance. Reward-only contact/slip shaping did not create a physically anchored stance foot; it mostly traded away depth while leaving the same slip/contact failure family.

The next M19 attempt should stop treating foot slip as only a scalar reward. It likely needs an explicit stance-foot constraint in the action/control path: stance-foot fixed action projection, contact impulse guard, or a WBC/QP layer during the visible-depth and return phases, then PPO can finetune around that constrained controller.
