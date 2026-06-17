# G1 Guarded Descent Summary

| Attempt | Verdict | Drop | Fell at | Contact | Final height | Guard trips | Max blend |
|---|---|---:|---:|---:|---:|---:|---:|
| smoke | DEPTH_PENDING | 0.0015m | never | 1.00 | 0.7535m | 0 | 0.08 |
| conservative | FAIL_FALL | 1.5283m | 4.80s | 0.73 | -0.7430m | 173 | 0.65 |
| medium | FAIL_FALL | 1.5272m | 2.66s | 0.82 | -0.7415m | 187 | 0.85 |
| assertive | FAIL_FALL | 1.5392m | 2.44s | 0.83 | -0.7530m | 200 | 1.00 |
| strict-low | RETURN_PENDING | 0.0872m | never | 0.85 | 0.7034m | 100 | 0.45 |
| strict-mid | DEPTH_PENDING | 0.0555m | never | 0.88 | 0.7366m | 153 | 0.55 |

M19 is closed only if a run passes visible depth, no-fall, contact, return, and browser replay gates.

Conclusion: guarded descent alone does not close M19. The best run, `strict-low`, reached visible depth without falling, but foot contact ratio, stance slip, and return-to-stand failed. Next controller work should anchor foot XY/support before lowering the pelvis further.
