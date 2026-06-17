# 73-g1-visible-gate-extension

## Hypothesis

exp72 closed the intermediate 7cm recoverable gate, but it did not satisfy the exp29 visible squat gate: the best run had 7.04cm drop, 0.479rad knee delta, and 0.309rad hip pitch delta. The visible gate requires 8cm drop, 0.60rad knee delta, and 0.35rad hip pitch delta.

The hypothesis is that exp72's event-triggered recapture corridor can be extended by increasing target drop and max blend while preserving the same early support recapture timing.

Sources accessed 2026-06-18:
- https://pmc.ncbi.nlm.nih.gov/articles/PMC11769464/
- https://www.lirmm.fr/krut/pdf/2014_galdeano_ssd-0568454426/2014_galdeano_ssd.pdf
- https://arxiv.org/html/2502.17219v1

## Method

- Reuse exp71's event-triggered recapture evaluator.
- Start from exp72's successful timing.
- Increase:
  - IK drop target to 8.6-9.2cm,
  - max blend to 0.542-0.550,
  - support/ZMP/slip weights modestly.
- Measure both:
  - intermediate 7cm recoverable gate,
  - exp29 visible 8cm + knee/hip gate.
- Store raw evidence under `verify/visible-gate-extension/`.

Command:

```powershell
$env:OPENBLAS_NUM_THREADS='1'; C:\tmp\e34\Scripts\python.exe .\experiments\73-g1-visible-gate-extension\run_visible_gate_extension.py
```

## Results

Native verdict: `PASS_RECOVERABLE_7CM_GATE`, but `FAIL_VISIBLE_8CM_GATE`.

Raw evidence:
- `verify/visible-gate-extension/result.json`
- `verify/visible-gate-extension/visible-gate-extension-summary.md`
- per-candidate `native-eval.json` files under `verify/visible-gate-extension/<attempt>/`

Best recoverable run:

| Attempt | 8cm gate | 7cm gate | Drop | Knee | Hip | Contact | Slip | CoM min | ZMP min | Final h | Fell | Visible gap d/k/h |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| `visible-d0p092-b0p546-trig0p0660-hold0p16` | FAIL | PASS | 0.0760m | 0.512 | 0.307 | 0.97 | 0.057m | 0.0140m | -0.0281m | 0.7493m | never | 0.0040m / 0.088rad / 0.043rad |

Best no-fall visible-gap score:

| Attempt | Drop | Knee | Hip | Contact | Slip | Final h | Fell | Visible gap d/k/h |
|---|---:|---:|---:|---:|---:|---:|---|---|
| `visible-d0p089-b0p546-trig0p0660-hold0p18` | 0.0748m | 0.506 | 0.347 | 0.99 | 0.059m | 0.7492m | never | 0.0052m / 0.094rad / 0.003rad |

No candidate passed the full visible gate. The recoverable corridor did extend from exp72's 7.04cm to 7.60cm. The remaining visible gap is small in pelvis drop, but knee and hip flexion remain under the exp29 thresholds.

## Insights

The event-triggered recapture corridor can be extended, but increasing drop/blend alone is not enough. The best recoverable run is still short by:

- 4.0mm pelvis drop,
- 0.088rad knee flexion,
- 0.043rad hip pitch.

The best hip-flexion candidate nearly closes hip gap, but still lacks knee flexion and depth. Nearby deeper candidates cross the 8cm geometry only by entering the collapse branch. The next experiment should bias the target itself toward knee/hip flexion inside the foot-fixed IK solution, not just increase scalar drop or max blend.
