# GEN4 — Observable Failure Patterns

## 가설

실패 원인을 추정하지 않아도 canonical episode의 trajectory·event·terminal state에서 사람이 재검토할 수 있는 “관측 가능한 실패 양상”을 만들 수 있다.

## 방법

GEN2 OpenVLA 25개 timeout과 GEN3 π₀.₅ 2개 timeout을 공통 evidence contract로 읽는다. taxonomy→derived feature→deterministic classifier→reviewer calibration→coverage gate 순서로 진행하며 canonical episode는 수정하지 않는다.

## 결과

Step 1은 8개 pattern ID, typed predicate, frame range와 content-hashed source pointer를 `failure-pattern-schema.json`으로 고정했다. policy failure label 7개와 attempt-only `infrastructure_error`를 분리했고, invalid fixture 5개와 역전 frame range가 모두 거부됐다.

Step 2는 actual 27개 timeout episode에서 8D state·7D action·dual camera·controller event를 read-only 추출했다. rejected controller event는 0이며, object relation과 goal distance는 canonical source가 없어 27개 모두 explicit unavailable이다. raw source는 추출 전후 SHA-256가 동일하다.

```bash
python experiments/153-observable-failure-patterns/verify_contract.py
python experiments/153-observable-failure-patterns/test_verify_contract.py
/home/yusun/.venvs/vla-eval/bin/python experiments/153-observable-failure-patterns/extract_features.py
/home/yusun/.venvs/vla-eval/bin/python experiments/153-observable-failure-patterns/test_extract_features.py
```

## 통찰

“왜 실패했는가”를 바로 생성하기보다 “어떤 관측 조건이 충족됐는가”를 먼저 정본화해야 이후 분류와 공개 UI가 hidden reasoning을 사실처럼 표시하지 않는다.
