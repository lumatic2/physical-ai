# 최종 보고서 — GEN4 관측 가능한 실패 양상

> 완료: 2026-07-21 · 대상: GEN4 · 작성: 완료 경계(§B3) — 이 보고서가 완료 의식의 정본이다.

## 1. 문제 정의 (무엇을 왜 하려 했나)

GEN3는 두 VLA의 60쌍 실제 결과를 비교했지만 27개 non-success는 성공률의 반대편 숫자로만 남아 있었다. 이를 자유 생성 진단으로 설명하면 모델이 “이해하지 못했다”거나 planning이 실패했다는 근거 없는 원인 주장이 되기 쉽다. GEN4는 원인을 추정하지 않고 trajectory·controller event·camera·manifest에서 직접 확인되는 실패 양상만 분류하고, 근거가 모자라면 `unknown`으로 보존하는 것을 목표로 했다.

## 2. Objective 연결 (북극성과의 관계)

Objective의 “검증된 능력과 아직 검증되지 않은 한계가 함께 드러난다”는 계약을 non-success 분석에 적용했다. 사람이 aggregate에서 원 episode의 dual camera·event·metric pointer까지 내려갈 수 있게 했고, 관측된 양상과 hidden reasoning·root cause·실물 로봇 성능 사이의 경계를 검증 코드로 고정했다.

## 3. 경로 (horizon → milestone → steps)

“여러 과제에서 통하는 로봇 판단 실험실” Horizon의 네 번째 Milestone이다. Step 1은 8개 관측 label과 predicate/evidence schema를 만들었다. Step 2는 27개 timeout의 trajectory·action·controller·dual-camera source를 원본 변경 없이 추출했다. Step 3은 순서에 무관한 규칙으로 pattern index를 생성했다. Step 4는 관측된 policy/suite/label 7개 계층을 camera·event로 검토했다. Step 5는 전체 분모와 negative claim을 통합 검증했다. 승인 plan의 다섯 Step을 변경 없이 완주했다.

## 4. 구현 결과 (무엇이 만들어졌나)

27/27 non-success가 evidence-backed pattern 또는 `unknown` record를 가진다. terminal window end-effector displacement가 0.01m 미만인 `no_progress`는 6개(22.2%)이고, 현재 활성 predicate로 더 구체화할 수 없는 `unknown`은 21개(77.8%)다. policy별로 OpenVLA는 5/20, π0.5는 1/1이며 각각 no_progress/unknown 순이다. suite별로 goal은 5/7, object는 0/8, spatial은 1/6이다.

모든 record에는 frame range, typed predicate, 상대 source ref와 SHA-256가 있다. object pose/contact와 task-specific goal-distance source는 27개 모두 없으므로 wrong-object, grasp-lost, near-goal 규칙을 억지로 활성화하지 않았다. 이 미가용성이 높은 unknown 비율의 직접적인 evidence coverage 한계다.

## 5. 이슈와 해결 (막혔던 것, 어떻게 풀었나)

처음 taxonomy는 wrong-object·grasp-lost·near-goal까지 포함했지만 canonical episode에는 그 판단에 필요한 object relation과 goal-distance metric이 없었다. camera 영상만 보고 원인을 추정하지 않고 해당 규칙을 disabled로 남겼다. 실제 classifier는 terminal displacement와 explicit controller rejection만 사용하며 충돌은 `multiple`, 불충분은 `unknown`으로 보존한다.

사람 검토 계약에는 독립적인 제2 검토자가 없었다. 이를 숨기지 않고 Codex evidence review라는 reviewer kind를 별도로 기록했다. 7개 계층의 main/wrist 시작·중간·종료 프레임을 실제 디코딩해 확인했고, 원 event stream hash와 220·280·300개 accepted controller event를 대조했다. 판정은 7/7 일치했지만 독립 인간 agreement로 주장하지 않는다. 검토에 사용한 임시 PNG 8개는 정본에 포함하지 않고 휴지통으로 이동했다.

## 6. 결과물과 증거 (검증 포함)

- Changesets: `changesets/20260721-gen4-failure-pattern-contract/`, `changesets/20260721-gen4-trajectory-event-features/`, `changesets/20260721-gen4-deterministic-classifier/`, `changesets/20260721-gen4-reviewer-calibration/`, `changesets/20260721-gen4-failure-coverage-gate/`.
- Commits: `b0a6547`, `df9616e`, `db58594`, `e95e0d8`; 마지막 coverage changeset과 이 보고서는 GEN4 완료 commit에 포함된다.
- 계약 정본: `experiments/153-observable-failure-patterns/failure-pattern-schema.json`; 관측 용어 8개와 causal claim 거부.
- Feature 정본: `experiments/153-observable-failure-patterns/verify/features/failure-features.json`; 27 timeout, raw before/after hash 동일, dual camera·event 27/27.
- Pattern 정본: `experiments/153-observable-failure-patterns/verify/patterns/failure-pattern-index.json`; no_progress 6, unknown 21, deterministic record hash 고정.
- Reviewer 정본: `experiments/153-observable-failure-patterns/verify/reviewer-report.json`; 7 strata, unknown 포함, evidence agreement 7/7, 비독립성 disclosure.
- Coverage 정본: `experiments/153-observable-failure-patterns/verify/failure-coverage-report.json`; indexed 27/27, omitted 0, unknown 21/27, claim boundary PASS.
- Negative gates: causal label, missing pointer, order-sensitive rule, success-only sample, unknown 제외, reviewer override 무기록, denominator omission, unknown 은폐, root-cause·planning/perception·독립 인간·실물 로봇 claim을 거부했다.
- 크기 회고: 승인 plan의 5개 changeset으로 닫혀 선언한 `changesets>=5`와 일치한다. contract, feature, classifier, review, coverage가 각각 독립 검증 표면이다.
- 실표면: canonical 7개 표본의 main/wrist camera를 실제 디코딩하고 event 원본 hash·acceptance count를 확인했다. CLI에서 `failure coverage gate: PASS (indexed=27/27, no_progress=6, unknown=21)`을 관측했다.
- 재현: `python experiments/153-observable-failure-patterns/classify_patterns.py && python experiments/153-observable-failure-patterns/reviewer_calibration.py && python experiments/153-observable-failure-patterns/coverage_gate.py`.

## 7. 후속 제안 (다음에 무엇을)

다음 Milestone GEN5는 비교 aggregate에서 policy·suite·pattern별 drill-down을 제공하고, 각 card를 LAB3의 public dual-camera episode와 causal evidence drawer에 연결한다. 공개 UI는 `unknown 77.8%`와 disabled rule을 숨기지 않고, 시뮬레이션 관측을 real-robot 또는 root-cause 주장으로 확장하지 않아야 한다.
