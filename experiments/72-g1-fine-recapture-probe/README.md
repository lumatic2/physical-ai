# 72-g1-fine-recapture-probe

## Hypothesis

exp71 moved the stable recoverable boundary to 6.86cm. The remaining gap to the intermediate 7cm gate is only about 1.4mm, but the neighboring branch collapses. A broad sweep is therefore the wrong instrument.

The hypothesis is that a narrow probe around trigger 6.60-6.66cm, hold 0.12-0.18s, and max blend 0.540-0.542 can cross 7cm while keeping support/ZMP, slip, and terminal stand within gate limits.

Sources accessed 2026-06-18:
- https://arxiv.org/abs/1612.08034
- https://underactuated.mit.edu/humanoids.html
- https://arxiv.org/html/2505.19540v1

## Method

- Reuse exp71's event-triggered recapture native evaluator.
- Keep the search local around the exp71 best run:
  - trigger drop 6.60-6.66cm
  - hold 0.12-0.18s
  - max blend 0.540-0.542
  - support-heavy variants for the best local neighborhood
- Evaluate 24 candidates for 7.0s.
- Store raw evidence under `verify/fine-recapture-probe/`.

Command:

```powershell
$env:OPENBLAS_NUM_THREADS='1'; C:\tmp\e34\Scripts\python.exe .\experiments\72-g1-fine-recapture-probe\run_fine_recapture_probe.py
```

## Results

Native verdict: `PASS_RECOVERABLE_7CM_GATE`.

Raw evidence:
- `verify/fine-recapture-probe/result.json`
- `verify/fine-recapture-probe/fine-recapture-probe-summary.md`
- per-candidate `native-eval.json` files under `verify/fine-recapture-probe/<attempt>/`

Best recoverable run:

| Attempt | 7cm gate | 8cm gate | Drop | Recap | Contact | Slip | CoM min | ZMP min | Final h | Knee | Hip | Fell |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `fine-trig0p0660-hold0p16-b0p542` | PASS | FAIL | 0.0704m | 3.72s | 0.97 | 0.054m | 0.0101m | -0.0126m | 0.7495m | 0.479 | 0.309 | never |

The intermediate recoverable 7cm gate is now closed:

- no fall;
- visible drop >= 7cm;
- return to stand;
- contact ratio >= 0.90;
- foot slip <= 0.08m;
- no joint-limit violation.

This is still not the M19 completion gate. The exp29 visible gate requires >=8cm pelvis drop, knee delta >=0.60rad, hip pitch delta >=0.35rad, native rollout pass, and browser replay.

## Insights

The key was not more depth authority. It was a very narrow timing window:

- trigger at about 6.60cm,
- hold for 0.16s,
- max blend 0.542,
- then recapture immediately.

The same neighborhood shows the remaining cliff clearly: several nearby candidates either stop at 6.9cm or fall into support/ZMP collapse. For M19, the next step is to extend this event-triggered corridor toward the full exp29 visible gate, not to reopen broad parameter search.
