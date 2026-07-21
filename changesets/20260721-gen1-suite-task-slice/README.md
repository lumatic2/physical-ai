# Changeset: GEN1 frozen suite/task slice

- Status: completed
- Target: ROADMAP `GEN1` step-1 — `suite-task-slice`

## Scope

- `experiments/150-multitask-evaluation-contract/benchmark-manifest.json`: 3 suite × 4 task 선택 정본.
- `official-task-catalog.json`: pinned LIBERO task map snapshot.
- `verify_task_slice.py`, `test_verify_task_slice.py`, `fixtures/invalid-mutations.json`: structural/source verification과 failure probes.
- `verify/canonical/task-slice-report.json`: 공식 revision과 BDDL 12개를 대조한 canonical evidence.

## Contract

- Source of truth: `benchmark-manifest.json`.
- Upstream: LIBERO `8f1084e3132a39270c3a13ebe37270a43ece2a01`; task map SHA-256 `dc644c…55fc`.
- Compatibility: LAB1 canonical `libero_spatial/task-05`를 포함한다.
- Out of scope: initial states, policy registry, rollout, aggregate, public UI.

## Verification

- [x] manifest/catalog semantic validation PASS.
- [x] official task map revision/hash PASS.
- [x] selected BDDL 12개 SHA-256 PASS.
- [x] unknown task, duplicate task, suite relabel fixture가 FAIL.
- [x] diff/path scrub와 clean Python test PASS.

## Result

LIBERO pinned revision의 task map SHA-256과 선택된 BDDL 12개가 모두 일치했다. 세 negative mutation은 semantic validator에서 거부됐으며 canonical report에는 로컬 절대경로가 남지 않는다.
