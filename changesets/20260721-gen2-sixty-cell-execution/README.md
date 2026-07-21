# Changeset: GEN2 sixty-cell execution

- Status: completed
- Target: ROADMAP `GEN2` step-4 — `sixty-cell-execution`

## Scope

- `execute_baseline.py`: suite별 checkpoint 1회 load, cell별 attempt/record/export/seal 실행기.
- `verify_execution.py`: ledger에서 60개 sealed artifact를 찾아 dataset/sidecar/event/manifest hash 전수 재계산.
- `verify/canonical/manifest.json`: path-scrubbed 60-cell identity·outcome·timing·hash index.
- `verify/canonical/run-ledger.jsonl`: 123-event append-only canonical ledger snapshot.
- WSL local-only artifact root: 실제 LeRobot episode, dual-camera MP4, causal event와 sealed manifest 60개, 총 134MB.

## Contract

- 각 suite는 exact checkpoint revision을 한 번 load하고 manifest 순서로 20 cell을 실행한다.
- success/timeout만 valid policy terminal이며 infrastructure attempt는 denominator 밖 별도 집계다.
- raw episode는 content hash로 sealed되고 canonical index의 모든 cell에서 역추적된다.
- 완료된 cell은 재개 시 skip하며 server/client/GPU process는 suite와 run 종료 때 정리한다.

## Verification

- [x] 60 planned / 60 terminal / 0 pending / 60 unique run key PASS.
- [x] Spatial `13 success / 7 timeout`, Object `12 / 8`, Goal `10 / 10`.
- [x] 총 `35 success / 25 timeout`; valid policy result를 retry로 덮어쓰지 않음.
- [x] 60 sealed manifest, 60 causal event stream, 60 sidecar, 120 canonical camera video 존재.
- [x] dataset tree, sidecar, event, manifest hash 전수 대조와 process cleanup PASS.
- [x] missing/duplicate cell과 corrupt manifest hash fixture가 FAIL.

## Result

GEN1의 OpenVLA 60개 분모를 실제 RTX 5090·LIBERO 환경에서 모두 실행했다. 최초 smoke attempt는 writer close 전에 event exporter를 호출해 parquet footer가 없던 infrastructure error로 남겼고, exporter를 client 종료 뒤로 옮긴 explicit retry가 성공했다. Object checkpoint의 기본 downloader 연결 정체는 partial cache를 보존한 채 `hf download --max-workers 1` resume로 복구했다. 이후 59개 cell과 Object/Goal suite 실행에서는 infrastructure failure가 없었다.

## Sources

- [LIBERO frozen revision](https://github.com/Lifelong-Robot-Learning/LIBERO/tree/8f1084e3132a39270c3a13ebe37270a43ece2a01) (접근일: 2026-07-21)
- [OpenVLA LIBERO evaluation](https://github.com/openvla/openvla/blob/main/experiments/robot/libero/README.md) (접근일: 2026-07-21)
