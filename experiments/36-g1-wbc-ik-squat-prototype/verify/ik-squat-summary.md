# G1 WBC/IK Squat Prototype Summary

| Attempt | Verdict | IK max foot err | Drop | Fell at | Contact | Final height | Slip |
|---|---|---:|---:|---:|---:|---:|---:|
| ik-drop-0p08-blend-0p25 | DEPTH_PENDING | 0.0006m | 0.0224m | never | 1.00 | 0.7494m | 0.013m |
| ik-drop-0p08-blend-0p35 | FAIL_FALL | 0.0006m | 1.5072m | 4.02s | 0.86 | -0.7381m | 0.816m |
| ik-drop-0p06-blend-0p55 | FAIL_FALL | 0.0005m | 1.5202m | 3.00s | 0.90 | -0.7583m | 0.774m |
| ik-drop-0p08-blend-0p55 | FAIL_FALL | 0.0006m | 1.5142m | 2.94s | 0.90 | -0.7570m | 0.701m |
| ik-drop-0p08-blend-0p75 | FAIL_FALL | 0.0006m | 1.5179m | 2.50s | 0.92 | -0.7206m | 0.707m |
| ik-drop-0p08-no-policy | FAIL_FALL | 0.0006m | 1.5298m | 1.26s | 0.91 | -0.7540m | 0.975m |

M19 is closed only if visible depth, no-fall, stance/contact, return, and browser replay gates pass together.
