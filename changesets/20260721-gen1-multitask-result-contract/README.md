# Changeset: GEN1 multitask result contract

- Status: completed
- Target: ROADMAP `GEN1` step-4 — `multitask-result-contract`

## Scope

- `run-denominator.json`: task/state/policy artifact/adapter revision에서 생성한 120개 immutable run key.
- `schemas/multitask-run-v1.json`: success/timeout/error/excluded terminal result schema.
- `verify_result_contract.py`, tests와 fixtures: denominator identity·coverage·evidence semantic gate.
- `verify/canonical/result-contract-report.json`: canonical contract evidence.

## Contract

- Source of truth: benchmark manifest + initial states + policy registry의 SHA-256.
- Run key: suite/task/state/policy/artifact revision/adapter revision 전체를 포함한다.
- Evidence: success·timeout은 episode, error는 error report, excluded는 이유가 필수다.
- Out of scope: 실제 result, retries, aggregate statistics, public UI.

## Verification

- [x] 120 planned run / 120 unique immutable key PASS.
- [x] success/timeout/error/excluded JSON Schema와 lossless round-trip PASS.
- [x] result identity가 denominator task/state/policy revision과 일치.
- [x] duplicate key, missing complete denominator, evidenceless result가 FAIL.
- [x] path/secret scrub, Python tests와 canonical report PASS.

## Result

세 정본 파일의 content hash에서 120개 immutable run key를 생성했고 중복은 0개다. success/timeout/error/excluded fixture가 Draft 2020-12 schema와 semantic identity gate를 lossless round-trip했다. duplicate, complete denominator 누락, episode evidence 누락은 모두 거부됐다.
