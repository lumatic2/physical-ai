# 70-g1-full-return-recovery-horizon

## Hypothesis

exp69 found a deep no-fall candidate with 14.49cm drop but `RETURN_PENDING` at 6.0s. Because that candidate used `descend_s=3.5`, fixed hold `0.4`, and `return_s=2.2`, the full return phase ends at 6.1s. A 6.0s verdict can therefore misclassify a recovery that simply has not finished.

The hypothesis is that evaluating beyond the full return horizon, while sweeping faster release and stronger stand-up costs, will distinguish a true recoverable squat from an evaluation cutoff artifact.

Sources accessed 2026-06-18:
- https://www.mdpi.com/1424-8220/25/2/435
- https://arxiv.org/html/2505.19540v1
- https://www.lirmm.fr/krut/pdf/2014_galdeano_ssd-0568454426/2014_galdeano_ssd.pdf

## Method

- Reuse exp67's qfrc-assisted WBC selector.
- Start from exp69's deep no-fall corridor: `drop ~= 0.0832`, `max_blend ~= 0.533`, `residual_scale = 0.0682`.
- Evaluate 18 recovery variants with 7.0s rollouts, so `descend + hold + return` can complete.
- Sweep:
  - target drop
  - max blend
  - return duration
  - slow/fast release rates
  - stronger stand/upright/support/ZMP costs
- Store raw evidence under `verify/full-return-recovery-horizon/`.

Command:

```powershell
$env:OPENBLAS_NUM_THREADS='1'; C:\tmp\e34\Scripts\python.exe .\experiments\70-g1-full-return-recovery-horizon\run_full_return_recovery_horizon.py
```

## Results

Native verdict: `FAIL_RECOVERABLE_7CM_GATE`.

Raw evidence:
- `verify/full-return-recovery-horizon/result.json`
- `verify/full-return-recovery-horizon/full-return-recovery-horizon-summary.md`
- per-candidate `native-eval.json` files under `verify/full-return-recovery-horizon/<attempt>/`

Best no-fall run:

| Attempt | Drop | Contact | Slip | CoM min | ZMP min | qfrc | Final h | Fell | Verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| `recover-d0p0832-b0p532-tr1p75-rel0p12-0p24` | 0.0655m | 0.99 | 0.049m | 0.0068m | -0.0112m | 14.0 | 0.7541m | never | `DEPTH_PENDING_7CM` |

Best depth run:

| Attempt | Drop | Contact | Slip | CoM min | ZMP min | qfrc | Final h | Fell | Verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| `recover-d0p0832-b0p536-tr1p45-rel0p12-0p24` | 1.5094m | 0.88 | 0.903m | -0.5702m | -0.5842m | 37.0 | -0.7331m | 5.54s | `FAIL_FALL` |

No candidate passed the 7cm recoverable gate. The 7s horizon removed exp69's possible cutoff artifact: deep candidates do not merely need more time to stand up; they enter support/ZMP collapse during return.

## Insights

The useful result is negative but narrower. The problem is no longer "evaluate longer" or "release faster." Existing qfrc WBC selection has two modes:

- terminal-safe mode: no fall, good contact/slip, final stand, but depth saturates around 6.55cm;
- deep mode: reaches visible 7cm+ and even 8cm+ geometry, but return creates support/ZMP collapse and fall.

The next experiment should therefore be event-triggered, not schedule-triggered: once the rollout first crosses 7cm, immediately switch to a recovery controller that prioritizes support-center recapture before standing tall. A fixed descend/hold/return plan is too late.
