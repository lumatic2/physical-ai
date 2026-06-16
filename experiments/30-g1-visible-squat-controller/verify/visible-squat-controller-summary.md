# G1 visible squat controller summary

- Overall verdict: `VISIBLE_DEPTH_CONTROLLER_FAILS_STABILITY`
- Stage target: `0.67m`
- Visible gate: pelvis/base drop >= `0.08m`, no fall, foot contact >= `0.90`, final height >= `0.74m`

| Variant | Min height | Visible drop | Fell at | Foot contact | Final height | Verdict |
|---|---:|---:|---:|---:|---:|---|
| stage0p67-scale1p0-blend0p35 | 0.7431m | 0.0119m | never | 1.00 | 0.7499m | DEPTH_PENDING |
| stage0p67-scale1p0-blend1p0 | -0.7702m | invalid after fall | 2.06s | 0.92 | -0.7592m | FAIL_FALL |

Interpretation:
- Weak blend preserves balance/contact but does not produce a visible squat.
- Strong blend reaches visible-depth territory but destabilizes the humanoid and falls.
- Contact ratio alone is not enough because fallen-body contact can inflate the metric.
- Next attempt should add guarded descent, support/torso guards, and return-phase constraints before policy distillation.
