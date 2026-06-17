# Experiment 80: G1 Corridor Curriculum Training

## Hypothesis

Exp79 showed that hand-authored selector families plateau around `7.75cm / 0.517rad`. The next hypothesis was that the Unitree G1 squat is feasible in simulation only if the policy is trained inside the near-success corridor instead of being pushed by another fixed selector. A restored PPO policy should be able to learn from explicit height, knee, hip, support, and terminal-stand rewards around the `7.7cm` corridor.

Web search before the experiment found recent G1/humanoid work using staged curricula and height tracking for difficult whole-body transitions. External sources, accessed 2026-06-18:

- https://arxiv.org/html/2502.13013v1 — G1-class loco-manipulation work reports squatting to specified heights with height tracking and curriculum terms.
- https://www.roboticsproceedings.org/rss21/p070.pdf — paper version of the same G1 height-tracking/squat-to-height result.
- https://arxiv.org/html/2502.12152v1 — G1 getting-up work supports staged curriculum/refinement for difficult humanoid transitions.
- https://arxiv.org/abs/2505.20619 — recent Unitree G1 curriculum work motivates multi-phase humanoid training instead of fixed controller search.

## Method

This experiment added `CorridorCurriculumSquat`, a subclass of exp50's stance-constrained command-conditioned environment. It preserves the observation and action shape so the exp50 checkpoint can be restored, then adds reward and metric terms for:

- visible pelvis drop toward the near-success corridor,
- knee flexion delta toward `0.60rad`,
- hip pitch delta toward `0.35rad`,
- support margin health,
- terminal stand during return.

Native evaluation directly audits the exp29 visible gate: pelvis drop `>=8cm`, knee flexion delta `>=0.60rad`, hip pitch delta `>=0.35rad`, no fall, return to stand, both-foot contact ratio `>=0.90`, foot slip `<=0.08m`, and joint limit violation `<=0.05rad`.

Raw command:

```powershell
$env:OPENBLAS_NUM_THREADS='1'; C:\tmp\e34\Scripts\python.exe .\experiments\80-g1-corridor-curriculum-training\run_corridor_curriculum.py --train --timesteps 20000 --target-drop 0.078 --slip-limit 0.08 --support-floor -0.005 --seconds 6.0
```

Output files:

- `verify/target-0p078-slip-0p08/result.json`
- `verify/target-0p078-slip-0p08/native-eval.json`
- `verify/target-0p078-slip-0p08/corridor-curriculum-summary.md`
- `verify/target-0p078-slip-0p08/train/params.pkl`
- `verify/target-0p078-slip-0p08/train/rewards.txt`

## Results

Verdict: `RETURN_PENDING`, not `PASS_VISIBLE_8CM_GATE`.

Native rollout:

- Visible drop: `0.1126m` PASS
- Max knee delta: `0.5927rad` short by `0.0073rad`
- Max hip pitch delta: `0.5436rad` PASS
- Fell at: none
- Final height: `0.6424m`, so return-to-stand FAIL
- Both-foot contact ratio: `0.38` FAIL
- Foot slip: `3.132m` FAIL
- Minimum support margin: `-0.2206m` FAIL
- Joint limit violation: `0.0213rad` PASS

The policy learned to chase depth and pose much more aggressively than the selector family. It nearly hit the knee threshold and clearly passed the drop/hip thresholds, but it did so by losing stance support and sliding out of the controlled return corridor.

## Insights

The web search claim is plausible for this model family: G1-style squat-to-height behavior is not structurally impossible in simulation. The local experiment also moved from shallow, recoverable micro-squat to a policy that can reach visible geometry without falling by the height/uprightness definition.

But this is still not a usable squat. The failure mode changed from "cannot reach visible pose" to "reaches visible pose by destroying contact, support, and return." The next M19 experiment should not add more depth reward. It should train a two-stage or constrained return policy: first preserve both-foot contact and support while approaching `8cm`, then explicitly recover to stand from the visible-depth state with slip/contact termination kept hard.
