# Changeset: GEN4 reviewer calibration

- Status: completed
- Target: ROADMAP `GEN4` step-4 — `reviewer-calibration`

## Scope

- `reviewer_calibration.py`: 관측된 policy/suite/label 계층마다 1개를 결정적으로 고른다.
- `reviewer-packet.json`: 원 episode camera/event/trajectory pointer와 rule predicate를 함께 묶는다.
- `reviewer-decisions.json`: 검토자 신원·비독립성, source 확인, 판정과 disagreement를 기록한다.
- `reviewer-report.json`: label agreement와 unknown 포함 여부를 집계한다.

## Claim boundary

이 단계의 수동 검토는 Codex가 수행하는 evidence review이며 독립적인 제2 인간 검토가 아니다. 관측 가능한 predicate와 source alignment만 확인하고 root cause, hidden reasoning, real-robot 성능을 판정하지 않는다.

## Verification

- [x] 실제 7개 관측 계층을 모두 포함한다.
- [x] `unknown`, 두 policy, 세 suite를 제외하지 않는다.
- [x] main/wrist camera와 event source를 원 episode에서 확인한다.
- [x] disagreement와 reviewer override를 기록 없이 덮어쓸 수 없다.
- [x] success-only, unknown 제외, source omission failure probe가 FAIL한다.

## Result

실제 27개 timeout에서 관측된 7개 policy/suite/label 계층마다 1개를 선택했다. `no_progress` 3개와 `unknown` 4개이며 OpenVLA·π0.5와 goal·object·spatial suite가 모두 포함된다.

각 표본의 main/wrist camera 시작·중간·종료 프레임을 직접 확인했고 빈 프레임이나 역할 불일치는 없었다. 원 event stream의 SHA-256도 모두 일치했으며 controller acceptance는 표본별 220·280·300개로 feature index와 같았다. evidence reviewer 판정은 7/7 일치했다. 이는 독립적인 제2 인간 검토가 아니라 명시된 Codex evidence review다.
