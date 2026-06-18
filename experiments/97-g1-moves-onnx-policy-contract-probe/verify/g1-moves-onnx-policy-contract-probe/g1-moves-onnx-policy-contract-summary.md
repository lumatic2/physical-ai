# G1 Moves ONNX Policy Contract Probe Summary

| ONNX | Bytes | Input | Output | Smoke | Unit-ramp action range |
|---|---:|---|---|---|---|
| J_Dance4_Broadway.onnx | 2616790 | [1, 160] | [1, 29] | True | -2.047..3.033 |
| J_Dance4_Broadway_policy.onnx | 1004278 | ['batch', 160] | ['batch', 29] | True | -2.440..3.083 |
| J_Dance4_Broadway_policy.onnx | 2604502 | [1, 154] | [1, 29] | True | -2.896..2.665 |

Verdict: **PASS_ONNX_CONTRACT__NATIVE_ADAPTER_PENDING**

Key finding: the public artifacts provide finite ONNX actor policies, but the actor observation is a motion-command tracking vector, not the local exp05 103-d G1 walking observation.

M19 closes only after this contract is converted into a native rollout and the browser replay also passes the visible gate.
