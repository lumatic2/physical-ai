# 71-g1-event-triggered-recapture

## Hypothesis

exp70 showed that fixed return schedules split into two modes: terminal-safe runs saturate around 6.55cm, while deeper runs collapse during return. A schedule trigger is therefore too late or too early.

The hypothesis is that an event-triggered recapture policy can do better: once the rollout approaches the 7cm boundary or support/ZMP margin starts shrinking, immediately stop the descent schedule, amplify support-center feedback, and recover toward standing.

Sources accessed 2026-06-18:
- https://arxiv.org/abs/1612.08034
- https://usa.honda-ri.com/w/capture-point-a-step-toward-humanoid-push-recovery
- https://arxiv.org/html/2504.18698v1

## Method

- Reuse exp67's qfrc-assisted WBC selector and stabilizer policy.
- Replace fixed descend/hold/return with an event trigger:
  - visible drop threshold near 6.4-7.0cm,
  - support margin threshold,
  - ZMP margin threshold.
- Once triggered, force return phase, reduce desired depth, and multiply support-center error before the WBC target builder.
- Evaluate 24 variants for 7s and store raw evidence under `verify/event-triggered-recapture/`.

Command:

```powershell
$env:OPENBLAS_NUM_THREADS='1'; C:\tmp\e34\Scripts\python.exe .\experiments\71-g1-event-triggered-recapture\run_event_triggered_recapture.py
```

## Results

Native verdict: `FAIL_RECOVERABLE_7CM_GATE`.

Raw evidence:
- `verify/event-triggered-recapture/result.json`
- `verify/event-triggered-recapture/event-triggered-recapture-summary.md`
- per-candidate `native-eval.json` files under `verify/event-triggered-recapture/<attempt>/`

Best no-fall run:

| Attempt | Drop | Recap | Contact | Slip | CoM min | ZMP min | Final h | Fell | Verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| `recap-drop0p066-b0p540-rs1p15-hold0p12` | 0.0686m | 3.76s | 0.98 | 0.069m | 0.0109m | -0.0301m | 0.7511m | never | `DEPTH_PENDING_7CM` |

Best depth run:

| Attempt | Drop | Recap | Contact | Slip | CoM min | ZMP min | Final h | Fell | Verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| `recap-drop0p067-b0p538-rs1p15-hold0p20` | 1.5099m | 3.90s | 0.86 | 0.888m | -0.5894m | -0.5891m | -0.7549m | 5.32s | `FAIL_FALL` |

No candidate passed the 7cm recoverable gate. Event-triggered recapture with a short hold moved the stable return boundary from exp70's 6.55cm to 6.86cm, but the next small increase flips into the same support/ZMP collapse branch.

## Insights

The event trigger is directionally useful: triggering at ~6.6cm and holding the command for 0.12s gives a recoverable 6.86cm dip with acceptable contact, slip, and final stand height.

The cliff is now narrow. A 0.20s hold or a 6.7cm trigger is already too late and collapses. The next experiment should not broaden the search. It should run a fine probe around:

- trigger drop 6.55-6.70cm,
- hold 0.12-0.17s,
- max blend around 0.540,
- slightly higher return torque/stand weight only if support margin stays positive.

If that still cannot cross 7cm, the remaining gap likely requires a different actuator-space recovery target, not another phase heuristic.
