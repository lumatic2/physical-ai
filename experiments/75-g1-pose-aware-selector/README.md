# 75-g1-pose-aware-selector

## Hypothesis

exp74 showed that raw knee target offset is unstable: tiny hip bias is useful, but knee bias either reduces depth or enters delayed collapse. The next hypothesis is that knee flexion should be rewarded inside the selector cost, so the controller chooses one-step candidates that achieve more knee flexion while still paying the existing support/ZMP/slip costs.

Sources accessed 2026-06-18:
- https://www.lirmm.fr/krut/pdf/2014_galdeano_ssd-0568454426/2014_galdeano_ssd.pdf
- https://pmc.ncbi.nlm.nih.gov/articles/PMC11769464/
- https://arxiv.org/html/2502.17219v1
- https://www.roboticsproceedings.org/rss21/p070.pdf

## Method

- Reuse exp71's event-triggered recapture evaluator and exp73/74 timing.
- Monkeypatch exp67's one-step `score_candidate`.
- Add negative selector terms for achieved knee and hip progress, while leaving support, ZMP, slip, contact, downward velocity, uprightness, smoothness, and qfrc costs active.
- Compare no hip bias and the exp74 hip-only micro-bias (`0.02rad`).
- Store raw evidence under `verify/pose-aware-selector/`.

Command:

```powershell
$env:OPENBLAS_NUM_THREADS='1'; C:\tmp\e34\Scripts\python.exe .\experiments\75-g1-pose-aware-selector\run_pose_aware_selector.py
```

## Results

Native verdict: `PASS_RECOVERABLE_7CM_GATE`, but `FAIL_VISIBLE_8CM_GATE`.

Raw evidence:
- `verify/pose-aware-selector/result.json`
- `verify/pose-aware-selector/pose-aware-selector-summary.md`
- per-candidate `native-eval.json` files under `verify/pose-aware-selector/<attempt>/`

Best no-fall/recoverable pose-gap candidate:

| Attempt | 8cm gate | 7cm gate | Drop | Knee | Hip | Contact | Slip | CoM min | ZMP min | Final h | Fell | Gap d/k/h |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| `pose-hb0p02-wk0p05-wh0p02` | FAIL | PASS | 0.0761m | 0.513 | 0.337 | 0.97 | 0.072m | 0.0093m | -0.0468m | 0.7605m | never | 0.0039m / 0.087rad / 0.013rad |

Strong pose reward examples:

| Attempt | Drop | Knee | Hip | Slip | CoM min | ZMP min | Fell | Verdict |
|---|---:|---:|---:|---:|---:|---:|---|---|
| `pose-hb0p02-wk0p08-wh0p02` | 1.0191m | 0.513 | 0.338 | 0.190m | -0.5570m | -0.5569m | 6.76s | FAIL_FALL |
| `pose-hb0p02-wk0p12-wh0p02` | 0.9496m | 0.513 | 0.354 | 0.166m | -0.5868m | -0.5834m | 6.78s | FAIL_FALL |

No candidate passed the visible gate. Achieved knee flexion stayed pinned around `0.512-0.513rad` in both recoverable and collapse candidates.

## Insights

Selector cost shaping alone does not unlock the remaining knee flexion. It can preserve the exp74 best recoverable corridor and it can select late-collapse branches, but it does not raise achieved knee delta toward `0.60rad`.

The key new finding is that the bottleneck is likely not candidate selection among the current blend set. The currently generated target/action family itself does not contain a stable achieved-knee-flexion trajectory beyond about `0.513rad`.

The next experiment should change the trajectory family, not just the selector score. A more plausible next step is a staged target that temporarily allows a deeper knee-flexion phase while constraining CoM/ZMP/feet, then recaptures before the delayed 6.7s collapse branch. That means modifying the phase trajectory or adding a short knee-flexion micro-phase with explicit support constraints, not another one-step cost scalar.
