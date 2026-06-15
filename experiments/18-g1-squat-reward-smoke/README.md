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
- S3: 5-step zero-action rollout smoke.
- S4: short PPO smoke.
- S5: saved params native MuJoCo closed-loop diagnostic.

### 측정 metric
- observation shape
- reward first/last
- min/last base height
- termination 여부
- PPO eval reward curve
- native fall time, height, joint-limit violation, action/energy proxy, target error

## 3. 결과 (Results)

### 데이터
| Run | Verdict | Cost | Retries | 비고 |
|-----|---------|------|---------|------|
| S1-S3 env rollout smoke | PASS | local WSL/JAX | 1 | JIT reset/step 후 obs state 103, privileged 216, 5-step no termination |
| S4 short PPO smoke | PASS | 100k timesteps / 5.00min | 0 | eval reward 1.524 -> 3.316 |
| S5 trained params native diagnostic | FAIL_DIAGNOSTIC | 6.0s native MuJoCo | 1 | 1.24s fall, min height -0.763, max pose error 0.1459, max joint-limit violation 0.0631 |

### 박제 위치
- `verify/g1-squat-env-smoke.json`
- `verify/train-smoke.log`
- `verify/native-eval.log`
- `verify/train/rewards.txt`
- `verify/g1-squat-trained-native-eval.json`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- Repo-local subclass로 G1 squat reward wrapper를 만들 수 있다. Upstream `mujoco_playground` cache를 수정하지 않아도 reset/step/PPO loop에 들어간다.
- 5-step JIT rollout은 no termination으로 통과했다. obs shape도 기존 G1 policy 계약과 같다: state 103, privileged 216.
- 100k timestep short PPO smoke에서 eval reward가 1.524 -> 3.316으로 상승했다. 아직 skill 성공 증명은 아니지만 reward가 학습 신호로 작동한다.
- saved params를 native MuJoCo closed-loop로 돌리면 1.24초에 fall한다. 즉 short PPO smoke는 "학습 루프 진입" 증거일 뿐, 실제 squat skill 성공 증거가 아니다.

### 가설은 통과했나?
- [x] PASS — custom reward wrapper가 reset/step/PPO 루프를 통과했고 short smoke reward가 상승했다.
- [x] FAIL_DIAGNOSTIC — short-trained params는 native closed-loop에서 1.24초에 fall한다. 다음 단계는 export가 아니라 longer PPO/reward shaping/recovery term 보강이다.

### 정의에 반영
- `ROADMAP.md` M19의 balance wrapper와 trained-params diagnostic 항목을 완료로 갱신한다. Learned skill policy/export/browser는 short PPO 실패 원인을 줄인 뒤 진행한다.

### 다음 실험 후보
- longer PPO run 또는 recovery/upright reward 재조정으로 actual squat success를 다시 평가한다.
- native diagnostic이 최소 6초 no-fall을 만족한 뒤 ONNX export/browser skill playback으로 연결한다.
