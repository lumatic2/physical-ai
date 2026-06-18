# G1 Moves Standalone ONNX Native Adapter Probe Summary

| Attempt | Gate | Verdict | Drop | Knee | Hip | Contact | Slip | Fell | Action range |
|---|---|---|---:|---:|---:|---:|---:|---|---|
| reference-anchor-step1p0 | FAIL | FAIL_FALL | 1.512m | 2.738 | 2.448 | 0.16 | 1.564m | 0.36s | -11.62..23.59 |
| reference-anchor-step0p5 | FAIL | FAIL_FALL | 1.531m | 2.919 | 2.410 | 0.22 | 3.840m | 0.84s | -9.87..18.65 |
| reference-anchor-step0p25 | FAIL | FAIL_FALL | 1.568m | 2.734 | 2.396 | 0.67 | 1.568m | 0.62s | -9.61..11.40 |
| zero-anchor-step0p5 | FAIL | FAIL_FALL | 1.496m | 2.892 | 3.202 | 0.18 | 3.855m | 0.30s | -13.90..22.97 |
| keyframe-anchor-step0p5 | FAIL | FAIL_FALL | 1.523m | 2.325 | 2.272 | 0.22 | 1.591m | 0.40s | -10.02..16.03 |
| reference-anchor-step0p5-refblend0p15 | FAIL | FAIL_FALL | 1.558m | 2.907 | 2.063 | 0.44 | 1.207m | 0.56s | -12.08..17.37 |

Verdict: **FAIL_VISIBLE_NATIVE**

This is an approximate adapter based on the public README observation map. Browser replay is only allowed after a native visible PASS.
