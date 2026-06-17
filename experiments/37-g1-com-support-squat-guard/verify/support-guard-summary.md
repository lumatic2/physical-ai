# G1 CoM Support Guard Summary

| Attempt | Verdict | Drop | Fell at | Support min | Breach at | Fast drop at | Guard at | Slip |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| baseline-0p25 | DEPTH_PENDING | 0.0224m | never | 0.0227m | never | never | never | 0.013m |
| baseline-0p35 | FAIL_FALL | 1.5072m | 4.02s | -0.6053m | 3.10s | 3.80s | never | 0.816m |
| support-guard-0p35 | FAIL_FALL | 1.5194m | 4.06s | -0.6031m | 3.10s | 3.80s | 2.90s | 0.837m |
| support-guard-0p45 | FAIL_FALL | 1.5110m | 3.46s | -0.6082m | 2.60s | 3.20s | 2.44s | 0.806m |
| velocity-guard-0p45 | FAIL_FALL | 1.5132m | 3.44s | -0.6128m | 2.60s | 3.14s | 2.68s | 0.807m |

M19 is closed only if visible depth, no-fall, stance/contact, return, and browser replay gates pass together.
