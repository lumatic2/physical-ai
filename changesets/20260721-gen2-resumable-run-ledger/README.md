# Changeset: GEN2 resumable run ledger

- Status: completed
- Target: ROADMAP `GEN2` step-2 — `resumable-run-ledger`

## Scope

- `run_ledger.py`: lock·single-write append·fsync와 semantic replay를 가진 attempt ledger.
- `schemas/run-ledger-event-v1.json`: initialization/start/interruption/terminal event schema.
- `test_run_ledger.py`: forced interruption, retry, duplicate, partial promotion과 infrastructure 분리 검사.
- `verify_run_ledger.py`, `verify/resume-fault-injection.json`: bounded resume 증거.
- `run_baseline.py`: `--ledger`, `--resume` 실행 gate와 completed-cell filtering.

## Contract

- 각 run key의 attempt index는 0부터 순차 증가하고 retry는 직전 attempt id를 반드시 가리킨다.
- success/timeout은 sealed artifact ref/hash가 있어야 valid policy terminal이 된다.
- infrastructure error는 error ref와 함께 별도 기록되며 policy failure로 합산되지 않는다.
- valid policy terminal 뒤 retry, active partial을 숨긴 새 attempt와 duplicate terminal은 거부한다.

## Verification

- [x] forced interruption 뒤 completed cell 1개 skip, partial cell만 retry link 생성.
- [x] retry 뒤 completed 2개, pending 1개로 state 재계산 PASS.
- [x] 모든 event가 Draft 2020-12 schema PASS.
- [x] hidden retry, duplicate completion, partial artifact promotion이 FAIL.
- [x] infrastructure error attempt가 별도 집계되고 명시적 retry 가능.

## Result

runner는 이제 ledger 없이 실제 subprocess를 시작하지 않는다. 중단된 attempt와 infrastructure retry의 이력이 append-only로 남고, sealed episode가 없는 실행은 완료로 가장할 수 없다. 이 changeset은 fault-injection evidence이며 실제 OpenVLA rollout 결과는 포함하지 않는다.
