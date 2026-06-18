# Experiment 125 - G1 Crossing-Leg Kick Feasibility

## Question

Before treating a rabona-style kick as a learning target, can the current G1 ball scene support a crossing-leg kick probe at all?

## Method

The probe keeps the same G1 + ball scene used by M21. It does not train a policy. Instead, it sweeps a scripted right-leg pose across the body midline and measures:

- right foot crossing distance on the y-axis
- right-foot to ball contact frames
- right-foot to left-foot self-contact frames
- ball distance and direction error
- base-height fall threshold
- right-leg joint-limit margin

The pass gate is deliberately narrow: the right foot must cross the midline, touch the ball, avoid foot-foot contact, move the ball at least `0.60m`, keep direction error below `0.20rad`, and avoid fall.

## Result

Run:

```powershell
python experiments\125-g1-crossing-leg-kick-feasibility\evaluate_crossing_leg_kick.py
```

Current gate: PASS

- Best candidate: `back_cross`
- Max right-foot crossing y: `0.153m`
- Foot-ball contact frames: `79`
- Foot-foot contact frames: `0`
- Ball distance: `2.242m`
- Direction error: `0.083rad`
- Joint-limit violations: `0`
- Fell: `false`

Raw result is written to:

- `verify/g1-crossing-leg-kick-feasibility.json`
- `verify/g1-crossing-leg-kick-feasibility.md`

## Interpretation

If this probe passes, it means the current scene can represent a crossing-leg ball interaction and the task is worth specifying as a future learned external-object skill.

It does not prove that G1 has learned a rabona kick. Dynamic policy control, balance, timing, and reward shaping remain separate work.

## Evidence

- `evaluate_crossing_leg_kick.py`
- `verify/g1-crossing-leg-kick-feasibility.json`
- `verify/g1-crossing-leg-kick-feasibility.md`
