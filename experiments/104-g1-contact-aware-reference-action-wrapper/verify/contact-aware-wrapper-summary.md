# G1 Contact-Aware Reference Action Wrapper Summary

| Variant | Verdict | Drop | Knee | Hip | Contact | Slip | Return | Fall | Min scale |
|---|---|---:|---:|---:|---:|---:|---|---|---:|
| direct-exp103 | DEPTH_PENDING_7CM | 0.0572m | 0.583 | 0.492 | 0.39 | 3.090m | True | never | 1.00 |
| support-slip-scale | FAIL_FALL | 1.5358m | 0.609 | 0.242 | 0.91 | 0.985m | False | 2.08s | 0.20 |
| ankle-damped-support-slip | FAIL_FALL | 1.5363m | 0.601 | 0.206 | 0.91 | 0.995m | False | 1.28s | 0.20 |
| early-conservative-scale | FAIL_FALL | 1.5315m | 0.610 | 0.190 | 0.91 | 1.032m | False | 1.22s | 0.05 |
| return-on-contact-breach | FAIL_FALL | 1.5349m | 0.586 | 0.195 | 0.93 | 1.000m | False | 1.26s | 0.00 |

Best variant by score: `direct-exp103` -> `DEPTH_PENDING_7CM`.
Overall verdict: `DEPTH_PENDING_7CM`.
