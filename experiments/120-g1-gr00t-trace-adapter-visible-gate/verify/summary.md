# GR00T Trace Adapter Visible Gate Summary

- Verdict: `TRACE_ADAPTER_READY__RUNTIME_PREFLIGHT_PARTIAL`
- Synthetic web contract: `PASS`
- Synthetic visible gate: `PASS`
- WSL available: `True`
- WSL Docker CLI: `True`
- WSL GPU visible: `True`
- WSL git-lfs healthy: `False`
- M19 closed: `False`

## Blockers
- `wsl_git_lfs_broken_or_missing`

## Next Evidence
- Fix WSL git-lfs, then run python download_from_hf.py and GR00T sim2sim in WSL/Ubuntu.
- Capture realtime g1_debug or CSV logs from g1_deploy and feed measured fields through this adapter.
- Only close M19 if the real controller trace passes native exp29 visible/contact/slip/return gates and browser replay.
