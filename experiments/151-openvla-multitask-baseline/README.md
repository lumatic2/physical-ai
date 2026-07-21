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
python run_baseline.py --suite libero_spatial --task-id 0 --state-index 0 --execute
```

실제 실행은 기존 `experiments/01-vla-local-eval/run.py`의 server/client 프로세스 분리를 재사용한다. 결과 ledger와 canonical episode 저장은 GEN2 step-2와 step-3에서 연결한다.

## Sources

- [LIBERO repository at the frozen revision](https://github.com/Lifelong-Robot-Learning/LIBERO/tree/8f1084e3132a39270c3a13ebe37270a43ece2a01) (접근일: 2026-07-21)
- [OpenVLA LIBERO evaluation documentation](https://github.com/openvla/openvla/blob/main/experiments/robot/libero/README.md) (접근일: 2026-07-21)
- [OpenVLA LIBERO Spatial checkpoint](https://huggingface.co/openvla/openvla-7b-finetuned-libero-spatial/tree/962318cec55ac10993ff0f5f43eda9a270b4c873) (접근일: 2026-07-21)
- [OpenVLA LIBERO Object checkpoint](https://huggingface.co/openvla/openvla-7b-finetuned-libero-object/tree/287d6cfdf12d07b1449505f66d9bf3550257e9b3) (접근일: 2026-07-21)
- [OpenVLA LIBERO Goal checkpoint](https://huggingface.co/openvla/openvla-7b-finetuned-libero-goal/tree/fa5ae1e7509348889295bba8e08621d8b55e9baf) (접근일: 2026-07-21)
