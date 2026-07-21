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

## 초기 상태 계약

`initial-states.json`은 각 task의 `.pruned_init`에서 index 0~4를 고정한다. 다음 명령은 LIBERO/MuJoCo runtime에서 main camera, wrist camera, robot state, object state fingerprint를 같은 초기 상태마다 두 번 대조한다.

```bash
export PYTHONPATH="$HOME/LIBERO"
export MUJOCO_GL=egl
python verify_initial_states.py --libero-root "$HOME/LIBERO" --probe-resets \
  --output verify/canonical/initial-state-report.json
```

## 정책 호환성 registry

`policy-registry.json`은 OpenVLA와 π0.5의 입력이 같다고 가장하지 않는다. OpenVLA는 main camera+instruction만 사용하고, π0.5는 main+wrist camera, 8D state와 prompt를 사용한다. 두 정책 모두 LIBERO에 실행되는 7D action으로 수렴하지만 OpenVLA는 단일 action, π0.5는 action chunk를 생성한다.

- OpenVLA checkpoint: [Spatial](https://huggingface.co/openvla/openvla-7b-finetuned-libero-spatial/tree/962318cec55ac10993ff0f5f43eda9a270b4c873), [Object](https://huggingface.co/openvla/openvla-7b-finetuned-libero-object/tree/287d6cfdf12d07b1449505f66d9bf3550257e9b3), [Goal](https://huggingface.co/openvla/openvla-7b-finetuned-libero-goal/tree/fa5ae1e7509348889295bba8e08621d8b55e9baf) (접근일: 2026-07-21).
- π0.5 source/adapter: [openpi commit](https://github.com/Physical-Intelligence/openpi/tree/15a9616a00943ada6c20a0f158e3adb39df2ccac), [LIBERO policy](https://github.com/Physical-Intelligence/openpi/blob/15a9616a00943ada6c20a0f158e3adb39df2ccac/src/openpi/policies/libero_policy.py), [official evaluator](https://github.com/Physical-Intelligence/openpi/blob/15a9616a00943ada6c20a0f158e3adb39df2ccac/examples/libero/main.py) (접근일: 2026-07-21).
- π0.5 checkpoint metadata: [public GCS listing](https://storage.googleapis.com/storage/v1/b/openpi-assets/o?prefix=checkpoints/pi05_libero/) (접근일: 2026-07-21).

## 실행·결과 계약

`run-denominator.json`은 suite/task/state/policy artifact/adapter revision을 모두 포함한 120개 immutable run key다. `schemas/multitask-run-v1.json`은 terminal result를 다음처럼 분리한다.

- `success`, `timeout`: canonical episode reference 필수.
- `error`: 재현 가능한 error report reference 필수.
- `excluded`: 실행하지 않은 이유 필수.

```powershell
python verify_result_contract.py --output verify/canonical/result-contract-report.json
python test_verify_result_contract.py
```

## 범위 경계

이 산출물은 12개 task identity, BDDL byte, task별 5개 initial state, 두 policy의 호환성 선언과 120개 실행·결과 identity를 고정한다. 실제 rollout 성공률은 아직 주장하지 않는다.

## GEN1 통합 gate

`verify_contract.py`는 task slice, initial state, policy registry, 120-cell denominator와 네 canonical report를 하나의 gate로 묶는다. cell 삭제·중복·environment revision drift를 주입한 fixture는 모두 거부해야 한다.

```powershell
python test_verify_contract.py
python verify_contract.py `
  --libero-root C:/path/to/LIBERO-at-8f1084e `
  --openpi-root C:/path/to/openpi-at-15a9616 `
  --verify-live-gcs `
  --output verify/canonical/gen1-contract-report.json
```

공식 원본은 [LIBERO commit](https://github.com/Lifelong-Robot-Learning/LIBERO/tree/8f1084e3132a39270c3a13ebe37270a43ece2a01), [openpi commit](https://github.com/Physical-Intelligence/openpi/tree/15a9616a00943ada6c20a0f158e3adb39df2ccac), [π0.5 LIBERO checkpoint listing](https://storage.googleapis.com/storage/v1/b/openpi-assets/o?prefix=checkpoints/pi05_libero/)을 대조한다(접근일: 2026-07-21).
