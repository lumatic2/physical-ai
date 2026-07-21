# Changeset: GEN3 paired statistics

- Status: completed
- Target: ROADMAP `GEN3` step-4 — `paired-statistics`

## Scope

- `paired_statistics.py`: GEN1 denominator를 기준으로 OpenVLA와 π₀.₅ canonical result를 60개 task-state key에서 join한다.
- `schemas/paired-report-v1.json`: raw numerator/denominator, paired difference, bootstrap interval, suite/task breakdown과 두 episode ref를 고정한다.
- `test_paired_statistics.py`: unpaired cell, suite omission, zero denominator, rounded-only metric 변이를 거부한다.
- `verify/paired-report.json`: 두 정책의 actual paired statistics 정본.

## Contract

- Source of truth: GEN1 `run-denominator.json`, GEN2 OpenVLA canonical manifest, GEN3 π₀.₅ canonical manifest.
- Pair key: `(suite, task_id, state_index)`이며 정확히 60개여야 한다.
- Statistics: raw success counts와 `π₀.₅ - OpenVLA` paired success difference를 함께 기록한다.
- Interval: 60개 paired difference `{-1,0,1}`를 seed 고정 bootstrap으로 재표집한다.
- Claim boundary: 관측된 고정 LIBERO slice의 비교이며 일반적인 정책 우승자나 모델 크기 효과를 주장하지 않는다.

## Verification

- [x] GEN1의 OpenVLA/π₀.₅ exact run key가 각각 60개 대응.
- [x] 60 pair마다 두 canonical episode ref와 hash 존재.
- [x] overall·suite·task raw counts를 pair rows에서 재계산.
- [x] paired difference와 deterministic bootstrap 95% interval 재현.
- [x] unpaired·suite omission·zero denominator·rounded-only 변이 FAIL.
- [x] JSON Schema, Ruff, focused tests와 `git diff --check` PASS.

## Result

60개 pair에서 OpenVLA는 35 success, π₀.₅는 58 success였다. 관측된 paired difference는 `+23/60 = +0.383333…`, seed `20260721`·10,000회 paired bootstrap 95% 구간은 `[+0.25, +0.516666…]`다. paired contingency는 both success 34, π₀.₅-only success 24, OpenVLA-only success 1, both non-success 1이다.

suite별 raw result는 Spatial `13/20→20/20`, Object `12/20→20/20`, Goal `10/20→18/20`이다. 따라서 전체 차이가 특정 suite 누락으로 생긴 것은 아니지만, 이 고정 LIBERO slice 밖의 일반적 우승자 주장은 열지 않는다.
