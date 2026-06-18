# Experiment 82: G1 Visible Stance WBC Guard

## Hypothesis

Exp81 showed that reward-only constrained return finetuning can recover terminal stand, but it still cannot keep stance feet anchored while preserving visible depth. The next hypothesis was that explicit stance-foot forces and WBC/QP-lite candidate selection could enforce contact/slip constraints directly during the visible-depth and return phases.

Web search before the experiment supported this direction. External sources, accessed 2026-06-18:

- https://www.mdpi.com/1424-8220/25/2/435 — humanoid squat control combines optimized trajectory planning with WBC tracking.
- https://arxiv.org/html/2312.16465v4 — multi-contact WBC motivates posture correction under contact constraints.
- https://mujoco.readthedocs.io/en/3.4.0/computation/ — MuJoCo contact/inverse dynamics notes caution that contact force constraints cannot be inferred from kinematics alone.

## Method

This experiment reused exp67's qfrc/WBC-lite candidate rollout and added an exp29 visible-gate annotation layer. Four variants increased stance-foot Jacobian-transpose force, support/ZMP/slip costs, and return safety while targeting `8.0-8.5cm` visible squat depth.

Raw command:

```powershell
$env:OPENBLAS_NUM_THREADS='1'; C:\tmp\e34\Scripts\python.exe .\experiments\82-g1-visible-stance-wbc-guard\run_visible_stance_wbc_guard.py --seconds 6.0
```

Output files:

- `verify/visible-stance-wbc-guard/result.json`
- `verify/visible-stance-wbc-guard/visible-stance-wbc-guard-summary.md`
- `verify/visible-stance-wbc-guard/*/native-eval.json`

## Results

Verdict: `FAIL_VISIBLE_8CM_GATE`.

Best no-fall run:

- Attempt: `visible-8cm-slow-guard`
- Visible drop: `0.0654m`
- Knee delta: `0.451rad`
- Hip pitch delta: `0.118rad`
- Both-foot contact ratio: `1.00`
- Foot slip: `0.019m`
- Final height: `0.7082m`
- Verdict: `DEPTH_PENDING_8CM`

Depth-biased variants reached or exceeded pose geometry, but they fell:

- `visible-8cm-stance-force`: `1.390m` drop, knee `0.604rad`, hip `0.356rad`, fell at `5.62s`
- `visible-8p2cm-stance-force`: `1.504m` drop, knee `0.662rad`, hip `0.355rad`, fell at `5.30s`
- `visible-8p5cm-depth-biased-guard`: `1.532m` drop, hip `0.396rad`, fell at `2.66s`

## Insights

Explicit stance-foot WBC guard can solve the gross slip/contact side of the problem in the shallow regime: the best no-fall run held both-foot contact and kept slip under `2cm`. But this safety comes by refusing the visible pose. When the controller is allowed to chase visible depth, support/ZMP still collapses and the robot falls.

The next experiment should not simply make stance force stronger. The useful split is now clear: shallow WBC guard has contact, exp80 PPO has visible geometry. M19 likely needs a hybrid where the visible trajectory is planned over multiple steps and then projected through the stance guard, or a learned residual is constrained by a WBC layer rather than replaced by it.
