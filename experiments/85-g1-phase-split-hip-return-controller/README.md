# Experiment 85: G1 Phase-Split Hip Return Controller

## Hypothesis

Exp84 showed a narrower blocker: the best no-fall branch reached `28.43cm` drop and passed the knee gate, but hip flexion and terminal return remained pending. The hypothesis here was that the controller was coupling two conflicting objectives in one selector branch. If descent and return are split, the descent branch can focus on hip-forward visible pose while the return branch can release the squat target and recover to stand.

Web search supports this split. External sources, accessed 2026-06-18:

- https://www.mdpi.com/1424-8220/25/2/435 — humanoid squat work combines trajectory optimization with WBC rather than relying on a single WBC tracking objective.
- https://arxiv.org/html/2502.12152v1 — HumanUP uses a two-stage discovery/refinement approach for robust real-world Unitree G1 getting-up policies.
- https://arxiv.org/html/2502.08378v1 — humanoid standing-up is described as a multi-stage motor skill with time-varying contacts and motion constraints.

## Method

This experiment copies exp84 and changes the selector branch:

- descent phase: keep hip-forward pose bias and horizon knee/hip shortfall costs.
- return phase: disable pose bias, zero the IK blend, use default stand targets, and increase terminal stand/contact/slip costs.
- second sweep: add a horizon `depth_cap` to prevent the phase-split controller from choosing the delayed collapse branch.

Raw command:

```powershell
$env:OPENBLAS_NUM_THREADS='1'; C:\tmp\e34\Scripts\python.exe .\experiments\85-g1-phase-split-hip-return-controller\run_phase_split_hip_return_controller.py --seconds 6.0
```

Output files:

- `verify/phase-split-hip-return-controller/result.json`
- `verify/phase-split-hip-return-controller/phase-split-hip-return-controller-summary.md`
- `verify/phase-split-hip-return-controller/*/native-eval.json`

## Results

Verdict: `FAIL_VISIBLE_8CM_GATE`.

Final capped sweep:

- `cap18-split-hip0p16-return2p3`: fell at `5.20s`, drop `1.519m`, knee `0.436rad`, hip `0.182rad`, slip `0.427m`.
- `cap22-split-hip0p18-return2p4`: fell at `5.30s`, drop `1.522m`, knee `0.449rad`, hip `0.203rad`, slip `0.392m`.
- `cap25-split-hip0p20-return2p6`: fell at `4.96s`, drop `1.514m`, knee `0.601rad`, hip `0.234rad`, slip `0.424m`.
- `cap18-guarded-hip0p14-return2p6`: fell at `5.54s`, drop `1.506m`, knee `0.423rad`, hip `0.188rad`, slip `0.420m`.

No variant preserved the exp84 no-fall/contact/slip corridor. The `depth_cap` reduced neither the delayed collapse nor return instability enough because the short horizon still underestimates the later fall.

## Insights

The phase split is directionally right but too abrupt. Switching directly from a crouch/hip-forward target to a default stand target turns the remaining M19 blocker from `POSE_GATE_PENDING` into `FAIL_FALL`. That means exp84's low but stable crouch is not yet recoverable by target release alone.

The next experiment should insert an intermediate recapture phase before stand-up: clamp depth around the exp84 no-fall corridor, restore support/ZMP first, then ramp hip/knee back to default. In other words, use three phases instead of two: visible descent -> recapture hold -> terminal stand.
