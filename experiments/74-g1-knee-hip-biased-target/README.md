# 74-g1-knee-hip-biased-target

## Hypothesis

exp73 extended the recoverable corridor to 7.60cm but still missed the exp29 visible squat gate, mainly in knee and hip flexion. The next hypothesis is that a small actuator-space bias on the foot-fixed IK target can close the knee/hip gaps without increasing scalar drop or max blend.

Sources accessed 2026-06-18:
- https://pmc.ncbi.nlm.nih.gov/articles/PMC11769464/
- https://www.lirmm.fr/krut/pdf/2014_galdeano_ssd-0568454426/2014_galdeano_ssd.pdf
- https://support.unitree.com/home/en/G1_developer
- https://www.unitree.com/robocup

## Method

- Reuse exp71's event-triggered recapture evaluator and exp73's best recoverable timing.
- Monkeypatch the target builder so the IK target receives explicit actuator-space bias:
  - hip pitch: more negative on left/right hip pitch,
  - knee: more positive on left/right knee,
  - ankle pitch: held at zero in the final sweep after early ankle counter-bias destabilized stance.
- Run a bounded native sweep around small knee/hip biases.
- Store raw evidence under `verify/knee-hip-biased-target/`.

Command:

```powershell
$env:OPENBLAS_NUM_THREADS='1'; C:\tmp\e34\Scripts\python.exe .\experiments\74-g1-knee-hip-biased-target\run_knee_hip_biased_target.py
```

## Results

Native verdict: `PASS_RECOVERABLE_7CM_GATE`, but `FAIL_VISIBLE_8CM_GATE`.

Raw evidence:
- `verify/knee-hip-biased-target/result.json`
- `verify/knee-hip-biased-target/knee-hip-biased-target-summary.md`
- per-candidate `native-eval.json` files under `verify/knee-hip-biased-target/<attempt>/`

Best recoverable run:

| Attempt | 8cm gate | 7cm gate | Drop | Knee | Hip | Contact | Slip | CoM min | ZMP min | Final h | Fell | Visible gap d/k/h |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| `biasmk0p00mh0p02ma0p00` | FAIL | PASS | 0.0761m | 0.513 | 0.337 | 0.97 | 0.072m | 0.0093m | -0.0468m | 0.7605m | never | 0.0039m / 0.087rad / 0.013rad |

Baseline no-bias run in the same sweep:

| Attempt | Drop | Knee | Hip | Contact | Slip | Final h | Fell | Visible gap d/k/h |
|---|---:|---:|---:|---:|---:|---:|---|---|
| `biasmk0p00mh0p00ma0p00` | 0.0760m | 0.512 | 0.306 | 0.97 | 0.058m | 0.7494m | never | 0.0040m / 0.088rad / 0.044rad |

Small hip-only bias improved hip gap from 0.044rad to 0.013rad while preserving 7cm recovery. Direct knee bias did not help: moderate knee-biased candidates either stopped around 6.6-6.9cm or entered the delayed collapse branch around 5.2s.

## Insights

Knee/hip target bias is not a free visible-gate fix. A tiny hip pitch bias is useful and almost closes the hip metric, but knee bias appears coupled to support/ZMP and slip enough that the selector backs away from depth or collapses later.

The remaining blocker is now narrower:

- pelvis drop is short by about 3.9mm,
- knee flexion is still short by about 0.087rad,
- hip pitch is close enough to solve with a small hip-only bias.

The next experiment should not directly add knee target offset. It should shape knee flexion through a feasible descent/recapture trajectory or cost term that rewards achieved knee flexion while preserving support/ZMP, likely by modifying the one-step selector score rather than the raw IK target.
