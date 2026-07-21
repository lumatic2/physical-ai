# Changeset: GEN1 fixed initial states

- Status: completed
- Target: ROADMAP `GEN1` step-2 — `initial-state-contract`

## Scope

- `initial-states.json`: 12 task × state index 0~4의 source/tensor hash 계약.
- `verify_initial_states.py`: pinned init tensor와 두 번의 simulator reset fingerprint를 검증.
- `test_verify_initial_states.py`, `fixtures/invalid-initial-state-mutations.json`: order·seed·hash drift failure probes.
- `verify/canonical/initial-state-report.json`: 60개 reset cell의 canonical evidence.

## Contract

- Source of truth: `benchmark-manifest.json`의 task set + `initial-states.json`의 state set.
- Runtime: LIBERO `8f1084e…`, seed 0, state indices 0~4, 128×128 main/wrist render, reset 2회.
- Compatibility: 기존 LIBERO evaluator의 `env.reset() → env.set_init_state()` 순서를 유지한다.
- Out of scope: policy inference, action execution, success/failure outcome.

## Verification

- [x] 12개 `.pruned_init` source hash와 60개 tensor hash PASS.
- [x] 60개 cell의 두 reset fingerprint 일치.
- [x] task별 5개 reset fingerprint가 서로 구분됨.
- [x] state order, seed, tensor hash drift fixture가 FAIL.
- [x] WSL process/port cleanup, path scrub와 Python test PASS.

## Result

12개 task의 upstream init-state file과 선택 tensor 60개를 고정했다. 첫 probe는 같은 env에서 RNG를 진행시킨 reset을 clean run으로 잘못 비교해 camera drift를 검출했다. 반복마다 seed 0을 재설정하도록 바로잡은 뒤 main/wrist camera·robot·object state의 60×2 fingerprint가 모두 byte 단위로 일치했다.
