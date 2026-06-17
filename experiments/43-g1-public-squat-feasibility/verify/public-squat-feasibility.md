# G1 public squat feasibility refresh

## Verdict

- Public feasibility: SUPPORTED_BY_OFFICIAL_SPECS_AND_PUBLIC_DEEP_SQUAT_EVIDENCE
- Local static target feasibility: KINEMATICALLY_PLAUSIBLE
- Dynamic policy status: UNPROVEN_CURRENT_POLICY_NEEDS_WBC_CONTACT_FORCE_CONTROL

## Static probes

| Drop target | IK max foot error | Knee delta | Hip pitch delta | Visible pose gate |
|---:|---:|---:|---:|---|
| 0.08m | 0.0006m | 0.548rad | 0.263rad | PENDING |
| 0.12m | 0.0007m | 0.750rad | 0.359rad | PASS |
| 0.16m | 0.0008m | 0.930rad | 0.444rad | PASS |

## Interpretation

The public evidence supports that Unitree G1-class hardware can assume a deep squat posture, and the local MJCF can solve foot-fixed visible squat targets. This does not mean the current learned policy can dynamically squat; prior native rollouts still show shallow stable motion or collapse. The next controller experiment should therefore treat squat as a WBC/contact-force problem, not a joint-range problem.
