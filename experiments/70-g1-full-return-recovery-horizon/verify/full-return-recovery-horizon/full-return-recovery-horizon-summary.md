# G1 Full Return Recovery Horizon Summary

| Attempt | 8cm | 7cm | Verdict | Drop | Contact | Slip | CoM min | ZMP min | qfrc | Final h | Fell |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| recover-d0p0832-b0p533-tr1p15-rel0p09-0p18 | FAIL | FAIL | FAIL_FALL | 1.5048m | 0.90 | 0.912m | -0.5670m | -0.5795m | 37.0 | -0.6441m | 6.02s |
| recover-d0p0832-b0p533-tr1p15-rel0p12-0p24 | FAIL | FAIL | FAIL_FALL | 1.5029m | 0.88 | 0.894m | -0.5639m | -0.5784m | 37.0 | -0.7341m | 5.88s |
| recover-d0p0832-b0p533-tr1p45-rel0p09-0p18 | FAIL | FAIL | FAIL_FALL | 1.5012m | 0.90 | 0.888m | -0.5658m | -0.5819m | 37.0 | -0.5362m | 6.12s |
| recover-d0p0832-b0p533-tr1p45-rel0p12-0p24 | FAIL | FAIL | FAIL_FALL | 1.5031m | 0.87 | 0.896m | -0.5664m | -0.5775m | 37.0 | -0.7322m | 5.92s |
| recover-d0p0832-b0p536-tr1p15-rel0p09-0p18 | FAIL | FAIL | FAIL_FALL | 1.5013m | 0.87 | 0.890m | -0.5688m | -0.5779m | 37.0 | -0.7335m | 5.58s |
| recover-d0p0832-b0p536-tr1p15-rel0p12-0p24 | FAIL | FAIL | FAIL_FALL | 1.5042m | 0.88 | 0.908m | -0.5683m | -0.5766m | 37.0 | -0.7408m | 5.52s |
| recover-d0p0840-b0p533-tr1p15-rel0p09-0p18 | FAIL | FAIL | FAIL_FALL | 1.5070m | 0.87 | 0.896m | -0.5693m | -0.5764m | 37.0 | -0.7375m | 5.58s |
| recover-d0p0840-b0p533-tr1p15-rel0p12-0p24 | FAIL | FAIL | FAIL_FALL | 1.5073m | 0.86 | 0.908m | -0.5684m | -0.5842m | 37.0 | -0.7325m | 5.54s |
| recover-d0p0832-b0p533-tr1p75-rel0p09-0p18 | FAIL | FAIL | FAIL_FALL | 1.5013m | 0.91 | 0.900m | -0.5661m | -0.5765m | 32.9 | -0.5203m | 6.20s |
| recover-d0p0832-b0p533-tr1p75-rel0p12-0p24 | FAIL | FAIL | FAIL_FALL | 1.5024m | 0.89 | 0.875m | -0.5687m | -0.5795m | 37.0 | -0.7163m | 5.94s |
| recover-d0p0832-b0p532-tr1p15-rel0p09-0p18 | FAIL | FAIL | FAIL_FALL | 1.5013m | 0.88 | 0.904m | -0.5655m | -0.5809m | 37.0 | -0.6028m | 6.06s |
| recover-d0p0832-b0p532-tr1p15-rel0p12-0p24 | FAIL | FAIL | FAIL_FALL | 1.4997m | 0.92 | 0.928m | -0.5662m | -0.5825m | 37.0 | -0.6111m | 6.36s |
| recover-d0p0832-b0p532-tr1p45-rel0p09-0p18 | FAIL | FAIL | FAIL_FALL | 1.5030m | 0.88 | 0.889m | -0.5646m | -0.5780m | 37.0 | -0.5710m | 6.12s |
| recover-d0p0832-b0p532-tr1p45-rel0p12-0p24 | FAIL | FAIL | FAIL_FALL | 1.4052m | 0.94 | 0.561m | -0.5671m | -0.5722m | 20.6 | -0.6502m | 6.66s |
| recover-d0p0832-b0p532-tr1p75-rel0p09-0p18 | FAIL | FAIL | FAIL_FALL | 1.4987m | 0.90 | 0.912m | -0.5658m | -0.5739m | 37.0 | -0.5507m | 6.14s |
| recover-d0p0832-b0p532-tr1p75-rel0p12-0p24 | FAIL | FAIL | DEPTH_PENDING_7CM | 0.0655m | 0.99 | 0.049m | 0.0068m | -0.0112m | 14.0 | 0.7541m | never |
| recover-d0p0832-b0p536-tr1p45-rel0p09-0p18 | FAIL | FAIL | FAIL_FALL | 1.5015m | 0.87 | 0.933m | -0.5710m | -0.5800m | 37.0 | -0.7217m | 5.60s |
| recover-d0p0832-b0p536-tr1p45-rel0p12-0p24 | FAIL | FAIL | FAIL_FALL | 1.5094m | 0.88 | 0.903m | -0.5702m | -0.5842m | 37.0 | -0.7331m | 5.54s |

Best recoverable run: None
Best no-fall run: {'attempt': 'recover-d0p0832-b0p532-tr1p75-rel0p12-0p24', 'visible_drop': 0.0654678672647363, 'transition_verdict': 'DEPTH_PENDING_7CM', 'final_height': 0.7540581083344043}
Best depth run: {'attempt': 'recover-d0p0832-b0p536-tr1p45-rel0p12-0p24', 'visible_drop': 1.5094186172609225, 'fell_at': 5.54, 'transition_verdict': 'FAIL_FALL'}

This audit uses a 7s rollout so the return phase can finish before verdict assignment.
