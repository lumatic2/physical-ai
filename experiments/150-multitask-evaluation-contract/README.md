# GEN1 — frozen multitask evaluation contract

이 디렉터리는 정책 실행 전에 LIBERO Spatial/Object/Goal의 평가 task 12개를 고정한다. 아직 rollout, 성공률, 일반화 성능을 주장하지 않는다.

## 정본

- `benchmark-manifest.json`: 선택된 3 suite × 4 task의 실행 분모 정본.
- `official-task-catalog.json`: LIBERO revision `8f1084e3132a39270c3a13ebe37270a43ece2a01`의 task map snapshot.
- `verify_task_slice.py`: task id, language, BDDL file/hash와 공식 source를 대조한다.

공식 출처: [LIBERO repository](https://github.com/Lifelong-Robot-Learning/LIBERO/tree/8f1084e3132a39270c3a13ebe37270a43ece2a01) 및 [suite task map](https://github.com/Lifelong-Robot-Learning/LIBERO/blob/8f1084e3132a39270c3a13ebe37270a43ece2a01/libero/libero/benchmark/libero_suite_task_map.py) (접근일: 2026-07-21).

## 검증

```powershell
python experiments/150-multitask-evaluation-contract/test_verify_task_slice.py
python experiments/150-multitask-evaluation-contract/verify_task_slice.py
python experiments/150-multitask-evaluation-contract/verify_task_slice.py `
  --libero-root C:/path/to/LIBERO-at-8f1084e `
  --output experiments/150-multitask-evaluation-contract/verify/canonical/task-slice-report.json
```

실패 fixture는 unknown task, duplicate task, suite relabel을 각각 거부한다. canonical report의 `official_source.verified_bddl=12`여야 이 Step을 닫는다.

## 범위 경계

이 산출물은 12개 task identity와 BDDL byte를 고정한다. task별 5개 initial state는 GEN1 step-2, policy compatibility는 step-3에서 추가한다.
