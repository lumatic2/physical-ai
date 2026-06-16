# G1 visible squat feasibility audit

## Verdict

- Current web replay visible squat: FAIL_VISIBLE_SQUAT_MICRO_DIP
- Static visible-squat target feasibility: KINEMATICALLY_PLAUSIBLE_UNPROVEN_DYNAMICALLY
- Next action: build_deeper_foot_anchored_reference_then_native_controller_probe

## Current replay metrics

| Metric | Value | Gate |
|---|---:|---:|
| pelvis drop | 0.0096m | >= 0.08m |
| max knee delta | 0.1074rad | >= 0.60rad |
| max hip pitch delta | 0.0455rad | >= 0.35rad |

## Static target probe

Proposed visible target deltas: hip pitch -0.45rad, knee +0.75rad, ankle pitch -0.25rad.

All six lower-body target joints within local MJCF limits: True.

## Interpretation

The exp28 browser artifact is a stable micro-dip, not a visible squat. The local G1 model still has enough lower-body joint range for a visible squat target candidate, so the next experiment should generate a deeper foot-anchored reference and test it in native MuJoCo before publishing a new browser replay.
