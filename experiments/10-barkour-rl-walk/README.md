# 10-barkour-rl-walk — Barkour policy end-to-end absorption

> `experiments/10-barkour-rl-walk/README.md` — M15. 새 Playground policy 1종을 학습부터 live QA까지 흡수한다.

## 1. 가설 (Hypothesis)

MuJoCo Playground `BarkourJoystick` env와 Menagerie/MJCF asset 경로가 확보되어 있다면, 기존 Go1/Spot 4족 파이프라인을 재사용해 Barkour policy를 `train -> ONNX -> native parity -> browser bundle -> local/live QA`까지 end-to-end로 흡수할 수 있다.

반증 기준:
- `BarkourJoystick` env가 학습/export 가능한 형태가 아니다.
- native rollout에서 golden obs/ONNX parity 또는 scene byte-parity가 맞지 않는다.
- web bundle에서 WASM load, visual QA, command sweep 중 하나가 실패한다.

## 2. 방법 (Method)

### 셋업
- 모델: MuJoCo Playground PPO policy, target env `BarkourJoystick`.
- 데이터: 새 학습 checkpoint, exported ONNX, golden obs, command sweep raw JSON.
- 하네스 구성: exp04/06의 train/export/verify 패턴, exp03 digital twin registry, web QA scripts.

### 시나리오
- S1/probe: WSL의 Playground source/env 목록과 Barkour asset availability 확인. Go2는 asset만 있고 registry env가 없어 제외.
- S2/train: Barkour env를 단시간 학습하고 reward log/checkpoint를 `verify/`에 보존.
- S3/export: ONNX export 및 JAX/ONNX parity 확인.
- S4/native: bundled scene 기준 golden obs와 native rollout 안정성 확인.
- S5/web: `experiments.json` 등록, web bundle 생성, local visual QA/command sweep.
- S6/live: Vercel deploy 후 live visual QA/command sweep.

### 측정 metric
- train reward trend, ONNX max abs diff, obs/golden byte-parity, rollout distance/fall/NaN, command sweep pass/fail.

## 3. 결과 (Results)

### 데이터
| Run | Verdict | Cost | Retries | 비고 |
|-----|---------|------|---------|------|
| S1 env registry | PASS | - | 0 | `Go2*` env 없음. `BarkourJoystick` env/config/assets 확인 |
| S2 train | PASS | 6.5분 | 0 | 100M step, reward 1.759 -> 38.249 |
| S3 export | PASS | - | 0 | ONNX vs JAX max abs err 2.95e-6 |
| S4 native | PASS | - | 1 | +vx는 world -x로 이동해 convention fail. `cmd_vx=-1.0`에서 8s 5.93m, no fall |
| S5 local web | PASS | - | 1 | manifest 누락으로 첫 app load 실패 후 재생성. visual 400 step x=3.60m, console error 0 |
| S6 live web | PASS | - | 0 | live visual 400 step x=3.70m, command sweep PASS |

### 박제 위치
- `verify/` 폴더에 env probe, train log, obs spec, golden obs, native rollout, local/live QA raw 출력 보존.

## 4. 통찰 (Insights)

- Go2는 Menagerie asset은 있지만 현재 Playground registry에는 trainable env가 없어 M15 타겟으로 부적합했다.
- Barkour는 obs 구조가 Go1/Spot과 다르다. 현재 31-d obs를 15-frame history로 roll한 465-d 입력을 쓰므로 web runtime에 history obs builder가 필요했다.
- Barkour의 env command x축은 이 데모의 world-forward convention과 반대다. 웹에서는 user-facing `vx=+1`을 policy input `vx=-1`로 sign flip한다.
- ADR 0007 규칙이 다시 필요했다. Playground env가 contact sensors, joint damping, actuator gain/bias를 런타임에 바꾸므로 static XML에 bake해야 browser byte-parity가 맞는다.
- manifest 기반 WASM FS staging은 새 embodiment 추가의 실제 gate다. scene 단독 loadtest가 통과해도 `manifest.json`을 재생성하지 않으면 app에서는 로드 실패한다.

### 가설은 통과했나?
- [x] PASS — `BarkourJoystick`을 새 학습부터 ONNX/native/web/live QA까지 end-to-end로 흡수했다.
- [ ] FAIL — 무엇이 어긋났나, 가설 수정

### 정의에 반영
- M16 policy-addition checklist에 `obs history`, `command convention`, `runtime XML mutation bake`, `manifest regen`을 필수 gate로 반영한다.

### 다음 실험 후보
- M16: policy addition routine 일반화.
- M17: Go1/G1/Spot/Barkour command-terrain 비교표.
