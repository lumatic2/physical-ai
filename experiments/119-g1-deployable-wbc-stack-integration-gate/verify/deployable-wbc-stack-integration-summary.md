# G1 Deployable WBC Stack Integration Gate Summary

- Verdict: `WBC_STACK_CANDIDATE__LOCAL_INTEGRATION_BLOCKED`
- Source tree present: `True`
- 29-DOF model contract pass: `True`
- Existing Unitree DDS/browser path pass: `True`
- Direct GR00T runtime ready on this host: `False`
- Local release checkpoint/model artifact found: `True`
- M19 closed: `False`

## Blockers
- `direct_gr00t_runtime_requires_linux_docker_git_lfs_environment`

## Next Evidence
- Run GR00T/SONIC sim2sim on Linux/WSL2 or Ubuntu host with Git LFS, model download, and Docker/GPU path ready.
- Export or stream the 29-DOF G1 MuJoCo/LowState trace into the existing exp33 DDS/browser candidate gate.
- Evaluate the emitted motion against exp29 visible squat thresholds: >=8cm drop, >=0.60rad knee, >=0.35rad hip, contact/slip/return, then browser replay.
