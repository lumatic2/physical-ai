# GR00T WSL Runtime Preflight Summary

- Verdict: `WSL_SIM_RUNTIME_PREFLIGHT_PASS__DEPLOYMENT_PARTIAL`
- Git LFS healthy: `True`
- HF sample download present: `True`
- run_sim_loop help pass: `True`
- venv import smoke pass: `True`
- torch CUDA visible: `True`
- G1 Balance/Walk ONNX present: `True`
- run_sim_loop timeout smoke no traceback: `True`
- M19 closed: `False`

## Blockers / Constraints
- `install_mujoco_sim_must_run_on_wsl_native_filesystem_not_mnt_c`
- `tensorrt_root_missing_for_cpp_deployment`
- `training_stack_not_installed_but_not_needed_for_mujoco_sim_loop`

## Next Evidence
- Run GR00T sim loop and deployment together from WSL-native checkout, preferably headless/offscreen first.
- Capture real measured g1_debug or StateLogger CSV output from the running controller.
- Feed the measured trace through exp120 and only close M19 if native visible/contact/slip/return plus browser replay pass.
