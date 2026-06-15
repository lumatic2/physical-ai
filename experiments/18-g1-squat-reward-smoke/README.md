# 18-g1-squat-reward-smoke — G1 squat balance reward wrapper

> M19b. M19a의 open-loop squat 실패 뒤, G1 Joystick env를 얇게 상속해 balance-stabilized squat reward가 reset/step/PPO 루프에 들어가는지 확인한다.

## 1. 가설 (Hypothesis)

Upstream G1 Joystick env를 직접 수정하지 않고 repo-local subclass로 reward/reset/command를 바꾸면, `g1_squat` compiled target을 학습 가능한 MJX/Brax env로 만들 수 있다.

반증 기준:
- env reset/step에서 shape 또는 reward key가 깨진다.
- zero-action rollout이 즉시 termination된다.
- short PPO smoke가 컴파일 또는 학습 루프에 진입하지 못한다.

## 2. 방법 (Method)

### 셋업
- 모델: MuJoCo Playground `G1JoystickFlatTerrain`의 G1 MJX model.
- 데이터: M18 `g1_squat` target과 M22 squat reference에서 온 height/pose schedule.
- 하네스 구성: `g1_squat_env.py`, `smoke_squat_env.py`.

### 시나리오
- S1: deterministic reset, zero command, push/noise off.
- S2: custom reward terms: alive, pose tracking, height tracking, upright, feet contact, action smoothness, energy, termination.
- S3: 30-step zero-action rollout smoke.
- S4: 가능하면 short PPO smoke.

### 측정 metric
- observation shape
- reward first/last
- min/last base height
- termination 여부
- PPO eval reward curve

## 3. 결과 (Results)

### 데이터
| Run | Verdict | Cost | Retries | 비고 |
|-----|---------|------|---------|------|
| S1-S3 env rollout smoke | PASS | local WSL/JAX | 1 | JIT reset/step 후 obs state 103, privileged 216, 5-step no termination |
| S4 short PPO smoke | PASS | 100k timesteps / 5.00min | 0 | eval reward 1.524 -> 3.316 |

### 박제 위치
- `verify/g1-squat-env-smoke.json`
- `verify/train-smoke.log`
- `verify/train/rewards.txt`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- Repo-local subclass로 G1 squat reward wrapper를 만들 수 있다. Upstream `mujoco_playground` cache를 수정하지 않아도 reset/step/PPO loop에 들어간다.
- 5-step JIT rollout은 no termination으로 통과했다. obs shape도 기존 G1 policy 계약과 같다: state 103, privileged 216.
- 100k timestep short PPO smoke에서 eval reward가 1.524 -> 3.316으로 상승했다. 아직 skill 성공 증명은 아니지만 reward가 학습 신호로 작동한다.

### 가설은 통과했나?
- [x] PASS — custom reward wrapper가 reset/step/PPO 루프를 통과했고 short smoke reward가 상승했다.
- [ ] FAIL — 무엇이 어긋났나, 가설 수정

### 정의에 반영
- `ROADMAP.md` M19의 balance wrapper 항목을 완료로 갱신한다. Learned skill policy/export/browser는 다음 long-run 단계로 남긴다.

### 다음 실험 후보
- longer PPO run으로 actual squat success를 평가한다.
- trained params를 ONNX export/native verify/browser skill playback으로 연결한다.
