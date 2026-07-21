# OpenVLA multitask baseline

GEN1에서 고정한 60개 OpenVLA cell을 순서대로 검증·실행하는 로컬 baseline이다. 이 디렉터리의 dry-run은 identity와 실행 명령만 검증하며 rollout이나 성공률을 주장하지 않는다.

## Dry-run

```powershell
python run_baseline.py
python run_baseline.py --json
python run_baseline.py --suite libero_spatial --task-id 0 --state-index 0
```

전체 dry-run은 Spatial/Object/Goal 각 20개, 총 60개 cell을 출력한다. `runner-config.json`이 GEN1 manifest, initial-state contract, policy registry, denominator와 기존 OpenVLA orchestrator의 content hash를 고정한다. manifest 밖 task/state나 source·checkpoint·environment revision drift는 subprocess를 시작하기 전에 실패한다.

## 단일 cell 실행

Ubuntu WSL의 검증된 LIBERO/OpenVLA 환경에서 exact run key 또는 task/state selector로 한 cell만 실행한다.

```bash
export PYTHONPATH="$HOME/LIBERO"
export MUJOCO_GL=egl
python run_baseline.py --suite libero_spatial --task-id 0 --state-index 0 \
  --ledger /tmp/openvla-baseline.jsonl --execute
```

실제 실행은 append-only ledger 없이는 시작되지 않으며 기존 `experiments/01-vla-local-eval/run.py`의 server/client 프로세스 분리를 재사용한다. inference가 끝나도 step-3의 sealed canonical episode가 연결되기 전까지 attempt는 완료로 승격되지 않는다.

## 중단·재개 ledger

`run_ledger.py`는 각 event를 한 JSON line으로 append하고 `fsync`한다. valid policy result가 있는 cell은 `--resume`에서 건너뛰고, 중단된 active attempt는 `attempt_interrupted`를 먼저 기록한 뒤 `retry_of`로 연결한다. infrastructure error는 별도 집계해 retry할 수 있지만 success/timeout 뒤의 숨은 retry, 중복 terminal, partial artifact 승격은 거부한다.

```bash
python run_baseline.py --ledger /tmp/openvla-baseline.jsonl --resume
python verify_run_ledger.py
```

## Canonical episode seal

`episode_export.py`는 LAB1 LeRobot dataset/provenance와 LAB2 direct-VLA causal event를 같은 run key에 대조한다. dual camera, 8D state, 7D action, frame timestamp, raw policy action→executed action hash와 outcome이 모두 연결된 뒤에만 manifest를 `.partial`에서 `sealed`로 atomic rename하고 ledger terminal을 기록한다.

```bash
python episode_export.py \
  --run-key "$RUN_KEY" --dataset-root "$DATASET_ROOT" \
  --sidecar "$SIDECAR" --events "$EVENTS" \
  --artifact-ref "episodes/$CELL_ID" --manifest-output "$MANIFEST" \
  --ledger "$LEDGER" --attempt-id "$ATTEMPT_ID"
```

입력 경로는 local-only runtime argument이며 sealed manifest에는 상대 artifact ref와 content hash만 남는다.

## 60-cell 실행

`execute_baseline.py`는 suite별 server를 한 번만 로드하고 pending cell을 순차 실행한다. 각 attempt는 별도 디렉터리를 사용하며 client 종료로 parquet가 finalize된 뒤 causal event와 sealed manifest를 만든다.

```bash
export PYTHONPATH="$HOME/LIBERO"
export MUJOCO_GL=egl
python execute_baseline.py \
  --artifact-root "$HOME/physical-ai-runs/gen2-openvla" \
  --ledger "$HOME/physical-ai-runs/gen2-openvla/run-ledger.jsonl"

python verify_execution.py \
  --artifact-root "$HOME/physical-ai-runs/gen2-openvla" \
  --ledger "$HOME/physical-ai-runs/gen2-openvla/run-ledger.jsonl" \
  --assert-clean-processes
```

실제 raw LeRobot episode 60개는 local-only artifact root에 보존하고, repo에는 path-scrubbed 60-cell manifest와 append-only ledger snapshot을 추적한다. 현재 실측은 35 success, 25 timeout이며 infrastructure attempt 1건은 분모 밖에 별도 기록됐다.

## Baseline aggregate

```powershell
python aggregate_baseline.py --output verify/baseline-report.json
python test_aggregate_baseline.py
```

aggregate는 canonical 60-cell index만 입력으로 사용한다. 전체 성공률은 `35/60 = 58.33%`이며 Spatial `65%`, Object `60%`, Goal `50%`다. timeout 누락, 같은 run key의 retry success 덮어쓰기와 infrastructure error의 policy failure relabel은 거부한다.

## Sources

- [LIBERO repository at the frozen revision](https://github.com/Lifelong-Robot-Learning/LIBERO/tree/8f1084e3132a39270c3a13ebe37270a43ece2a01) (접근일: 2026-07-21)
- [OpenVLA LIBERO evaluation documentation](https://github.com/openvla/openvla/blob/main/experiments/robot/libero/README.md) (접근일: 2026-07-21)
- [OpenVLA LIBERO Spatial checkpoint](https://huggingface.co/openvla/openvla-7b-finetuned-libero-spatial/tree/962318cec55ac10993ff0f5f43eda9a270b4c873) (접근일: 2026-07-21)
- [OpenVLA LIBERO Object checkpoint](https://huggingface.co/openvla/openvla-7b-finetuned-libero-object/tree/287d6cfdf12d07b1449505f66d9bf3550257e9b3) (접근일: 2026-07-21)
- [OpenVLA LIBERO Goal checkpoint](https://huggingface.co/openvla/openvla-7b-finetuned-libero-goal/tree/fa5ae1e7509348889295bba8e08621d8b55e9baf) (접근일: 2026-07-21)
