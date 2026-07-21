# Changeset: GEN2 baseline aggregate gate

- Status: completed
- Target: ROADMAP `GEN2` step-5 — `baseline-aggregate-gate`

## Scope

- `aggregate_baseline.py`: canonical 60-cell index에서 outcome·frames·wall latency 재계산.
- `test_aggregate_baseline.py`: denominator 누락, retry 덮어쓰기, infrastructure relabel 검사.
- `verify/baseline-report.json`: overall/suite/task aggregate와 대표 success/timeout trace.

## Verification

- [x] 전체 60: `35 success / 25 timeout`, success rate `0.583333`.
- [x] Spatial `13/20`, Object `12/20`, Goal `10/20`.
- [x] 전체 frames median `189`, wall median `64.978s`.
- [x] 12 task denominator와 suite별 대표 success/timeout 6개가 artifact ref/hash로 역추적.
- [x] timeout 누락, duplicate retry success, infrastructure→policy relabel이 FAIL.
- [x] canonical report path/secret scrub와 source manifest hash PASS.

## Result

OpenVLA 60-cell baseline을 raw ledger/index에서 lossless 재계산했다. infrastructure attempt 1건은 분모에서 제외되고 최초 valid policy result만 사용된다. 이 수치는 OpenVLA 단독 LIBERO simulation baseline이며 π0.5와의 우열이나 실패 원인을 주장하지 않는다.
