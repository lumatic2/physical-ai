# Changeset: GEN4 deterministic failure classifier

- Status: completed
- Target: ROADMAP `GEN4` step-3 — `deterministic-classifier`

## Scope

- `classification-rules-v1.json`: 활성/비활성 규칙, threshold, availability 근거와 fallback.
- `classify_patterns.py`: 27 feature row를 evidence-backed pattern record로 결정적으로 변환.
- `test_classify_patterns.py`: input/rule order, conflict, unsupported label, missing pointer 변이.
- `verify/patterns/failure-pattern-index.json`: byte-stable derived label/index.

## Contract

- 활성 규칙: terminal-window displacement `<0.01m`의 `no_progress`, explicit rejected event의 `controller_rejected`.
- 비활성 규칙: object relation·goal distance가 없어 wrong interaction/grasp/near-goal을 판정하지 않는다.
- conflict는 sorted components의 `multiple`, 미충족은 `unknown`이다.
- 모든 record는 Step 1 schema와 Step 2 source hash를 그대로 보존한다.

## Verification

- [x] 27/27 feature가 pattern record 하나로 lossless 대응.
- [x] 같은 evidence, shuffled input/rule order가 byte-identical index를 만든다.
- [x] no_progress threshold와 controller rejection predicate가 typed source pointer를 가진다.
- [x] conflict는 multiple, 미충족/미가용은 unknown으로 보존된다.
- [x] unsupported causal label, missing pointer, order-sensitive mutation이 FAIL한다.
- [x] actual classifier CLI, schema validation, focused tests, Ruff와 diff gate PASS.

## Result

27개 timeout은 `no_progress` 6개와 `unknown` 21개로 분류됐다. no_progress record는 마지막 20% frame window에서 end-effector displacement `<0.01m`인 typed predicate와 trajectory hash를 가진다. controller rejection은 실제 0건이어서 label이 생성되지 않았다.

input feature와 rule 순서를 뒤집어도 record와 SHA-256 `b93cad…`가 같았다. 두 활성 규칙이 동시에 참인 fixture는 sorted component의 multiple이 됐고, unsupported causal label·missing pointer·count/hash drift는 거부됐다.
