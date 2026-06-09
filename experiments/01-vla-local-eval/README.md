# vla-eval — 컨슈머 GPU에서 1커맨드로 VLA 정책 평가

소비자용 단일 GPU(RTX 5090, Windows/WSL2)에서 **VLA(Vision-Language-Action) 정책을 LIBERO 시뮬로 평가**하는 최소 하네스.
대부분의 VLA 평가 코드가 datacenter/Linux 를 가정하는 것과 달리, 이 도구는 **세그폴트·의존성 마찰의 해법을 내장**한다.

- **모델(서버) ↔ 시뮬(클라이언트) 프로세스 분리** — `import tensorflow` 한 프로세스에서 robosuite EGL 컨텍스트 생성이
  세그폴트 나는 문제를 REST `/act` 경계로 구조적으로 회피 (워크어라운드가 아니라 서빙 정석).
- **검증된 의존성 핀** — Blackwell(sm_120) + 2024년 OpenVLA 스택의 시간차 마찰(torchvision ABI, transformers 5.x
  호환 등)을 `setup.sh` 에 박제.
- **기본 정책 = OpenVLA 7B** (LIBERO finetuned). 2번째 정책은 `server.py` 에 어댑터 1개 추가로 드롭인.

> 실측: RTX 5090 단일 GPU, OpenVLA 7B = **15GB 적재 · /act p50 168ms · libero_spatial 73%(11/15)**.
> 측정 근거·가설·마찰 체인 전문은 [`EXPERIMENT.md`](EXPERIMENT.md).

## 요구사항

- NVIDIA GPU (Blackwell 기준 — 다른 아키텍처면 `setup.sh` 의 cu128 인덱스만 조정)
- WSL2 Ubuntu-24.04 (또는 동급 Linux), Python 3.10+, EGL 가능한 드라이버
- 디스크 ~30GB (OpenVLA 7B 체크포인트 + LIBERO)

## 설치 (1커맨드)

```bash
bash setup.sh
```

`venv(~/.venvs/vla-eval)` 생성 → torch cu128 → `requirements.txt` → LIBERO(`--no-deps`) → config 시드까지 자동.
완료 시 스모크/전체 실행 명령을 출력한다.

## 평가 (1커맨드)

```bash
PYTHONPATH=$HOME/LIBERO MUJOCO_GL=egl ~/.venvs/vla-eval/bin/python run.py \
    --suite libero_spatial --tasks 3 --trials 5
```

`run.py` 가 서버(모델) 기동 → 포트 대기 → 클라이언트(시뮬) rollout → 종료까지 오케스트레이션.
결과는 stdout + `verify/eval.json` (success rate, per-task, latency).

### 기대 출력

```
[client] task0 '...': 4/5
...
[client] RESULT {"success_rate": 0.733, "total_episodes": 15, ...}
```

## CLI

| 플래그 | 기본값 | 설명 |
|---|---|---|
| `--policy` | `openvla` | 정책 어댑터 (현재 openvla) |
| `--suite` | `libero_spatial` | LIBERO 스위트: `libero_spatial`/`object`/`goal`/`10`/`90` |
| `--ckpt` | (자동) | HF 체크포인트. 비우면 `openvla/openvla-7b-finetuned-<suite>` |
| `--tasks` | 2 | 스위트 내 태스크 수 |
| `--trials` | 5 | 태스크당 rollout 수 |
| `--port` | 8000 | `/act` 포트 |

## 구조

```
run.py        오케스트레이터 (stdlib만 — numpy/tf/torch import 안 함)
  ├─ server.py   모델 프로세스: /act REST, tf 전처리 + OpenVLA 추론 (robosuite import X)
  └─ client.py   시뮬 프로세스: LIBERO EGL rollout, raw 관측을 /act 로 POST (tf import X)
requirements.txt / setup.sh   검증된 의존성 스택
verify/       박제된 raw 출력 (m4-*.json = M4 실험 기록, eval.json = 최신 런)
legacy/       M1~M3 마일스톤 스크래치 (mock·load·latency 단계 기록)
EXPERIMENT.md 실험 기록 (가설·방법·결과·통찰 4섹션)
```

## 2번째 정책 추가

`server.py` 의 `load()` 에 분기를 더하고, `/act` 가 동일 계약(이미지+instruction → 7-dim action ndarray)을
반환하도록 어댑터를 맞추면 된다. 클라이언트·오케스트레이터는 정책을 모른다 (REST 경계로 분리).
`run.py --policy <name>` 의 `choices` 에 이름 추가.
