# Changeset: GEN4 failure pattern contract

- Status: completed
- Target: ROADMAP `GEN4` step-1 — `failure-pattern-contract`

## Scope

- `failure-pattern-schema.json`: 관측 가능한 실패 양상 8개와 record/evidence 계약.
- `verify_contract.py`: taxonomy 언어, predicate, frame range, canonical pointer와 claim boundary 검증.
- `fixtures/invalid-pattern-contract.json`: 원인 추정 label, evidence/predicate 누락, absolute path 변이.
- `test_verify_contract.py`: schema와 semantic guard adversarial test.

## Contract

- policy failure label은 `no_progress`, `wrong_object_interaction`, `grasp_lost`, `timeout_near_goal`, `controller_rejected`, `unknown`, `multiple`만 허용한다.
- `infrastructure_error`는 attempt scope이며 policy non-success denominator에 합치지 않는다.
- 모든 record는 frame range, typed metric predicate와 content-hashed canonical source를 가진다.
- pattern은 관측 가능한 양상이며 perception/planning/reasoning의 root cause가 아니다.

## Verification

- [x] label 8개와 policy/attempt scope가 정확히 고정된다.
- [x] 모든 definition이 metric predicate와 evidence source를 요구한다.
- [x] record JSON Schema가 frame range·hash·relative ref를 강제한다.
- [x] unknown/multiple/infrastructure conditional contract가 PASS한다.
- [x] `bad_reasoning`, `did_not_understand`, missing evidence/predicate, absolute path가 FAIL한다.
- [x] CLI report, focused tests, Ruff와 diff gate PASS.

## Result

8개 label과 definition이 모두 typed predicate와 canonical evidence source를 요구한다. `infrastructure_error`만 attempt scope이고 나머지 7개는 policy episode scope다. unknown은 이유를, multiple은 둘 이상의 component를 요구하며 모든 record는 content hash와 상대 artifact ref를 가진다.

JSON Schema가 표현하지 못하는 frame range의 `start≤end`는 consumer semantic validator가 강제한다. 원인 추정 label 2개, predicate/evidence 누락, absolute local path와 역전 frame range가 모두 거부됐다.
