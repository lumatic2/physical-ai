# Attempt 013 Reference Audit

- stage height: `0.740`
- contact-preserving reference: `False`

| Metric | Value | Gate |
|---|---:|---:|
| min declared height | 0.7400 | <= 0.740 |
| min foot-anchored base height | 0.7532 | <= 0.745 |
| max foot XY drift | 0.0012 | <= 0.030 |
| max foot Z error at declared height | 0.0132 | <= 0.030 |
| max joint limit violation | 0.0000 | <= 0.050 |

| t | raw h | declared h | foot-anchored h | foot XY drift | foot Z err | joint viol |
|---:|---:|---:|---:|---:|---:|---:|
| 0.00 | 0.7550 | 0.7550 | 0.7550 | 0.0000 | 0.0000 | 0.0000 |
| 0.40 | 0.7190 | 0.7400 | 0.7532 | 0.0012 | 0.0132 | 0.0000 |
| 0.80 | 0.6830 | 0.7400 | 0.7532 | 0.0012 | 0.0132 | 0.0000 |
| 1.20 | 0.6470 | 0.7400 | 0.7532 | 0.0012 | 0.0132 | 0.0000 |
| 1.60 | 0.6200 | 0.7400 | 0.7532 | 0.0012 | 0.0132 | 0.0000 |
| 2.00 | 0.6200 | 0.7400 | 0.7532 | 0.0012 | 0.0132 | 0.0000 |
| 2.40 | 0.6200 | 0.7400 | 0.7532 | 0.0012 | 0.0132 | 0.0000 |
| 2.80 | 0.6470 | 0.7400 | 0.7532 | 0.0012 | 0.0132 | 0.0000 |
| 3.20 | 0.6830 | 0.7400 | 0.7532 | 0.0012 | 0.0132 | 0.0000 |
| 3.60 | 0.7190 | 0.7400 | 0.7532 | 0.0012 | 0.0132 | 0.0000 |
| 4.00 | 0.7550 | 0.7550 | 0.7550 | 0.0000 | 0.0000 | 0.0000 |

## Raw Reference Scale Sweep

| scale | min foot-anchored h | max foot XY drift | max foot Z err | max joint delta | joint viol |
|---:|---:|---:|---:|---:|---:|
| 0.10 | 0.7534 | 0.0010 | 0.0150 | 0.0151 | 0.0000 |
| 0.25 | 0.7510 | 0.0026 | 0.0150 | 0.0377 | 0.0000 |
| 0.50 | 0.7467 | 0.0051 | 0.0150 | 0.0755 | 0.0000 |
| 0.75 | 0.7422 | 0.0077 | 0.0150 | 0.1132 | 0.0000 |
| 1.00 | 0.7375 | 0.0102 | 0.0150 | 0.1510 | 0.0000 |

## Interpretation

- `declared h` is the staged target height used by exp28.
- `foot-anchored h` is the base height implied if the same joint target keeps the feet at their initial ground height.
- Large foot XY/Z errors mean the reference is not a clean fixed-feet squat target and should be rebuilt before more PPO.
