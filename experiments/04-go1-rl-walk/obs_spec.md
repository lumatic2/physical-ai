# Go1JoystickFlatTerrain — obs_spec (진실원천)

> 출처: `mujoco_playground/_src/locomotion/go1/joystick.py` + `base.py` + `go1_constants.py`
> (설치 패키지 직접 정독, 2026-06-13). ADR 0005가 지정한 "웹 parity 진실원천" — Phase 2 데스크탑·웹
> closed-loop가 *이 문서와 바이트 단위로 일치*해야 함.

## 정책 입력 = obs["state"], **48차원**

`jp.hstack` 순서 (joystick.py `_get_obs`):

| 슬롯 | 내용 | 차원 | 출처 |
|---|---|---|---|
| 0:3   | local linear velocity (body frame) | 3 | 센서 `local_linvel` |
| 3:6   | gyro (body angular velocity) | 3 | 센서 `gyro` |
| 6:9   | projected gravity (body frame) | 3 | `get_gravity` (upvector 계열 센서) |
| 9:21  | joint angles − default_pose | 12 | `qpos[7:]` − home keyframe `qpos[7:]` |
| 21:33 | joint velocities | 12 | `qvel[6:]` |
| 33:45 | last_act (이전 스텝 action) | 12 | info["last_act"] |
| 45:48 | command (vx, vy, vyaw) | 3 | info["command"] |

- **critic용 privileged_state(48+α)는 배포 불필요** — actor는 `state`(48)만 입력.
- **noise**: 학습 중에만 `noise_config.level=1.0`로 각 항에 uniform 노이즈. **배포/검증(play)에서는 노이즈 0** — clean obs 구성.
- **정규화**: brax PPO running obs normalizer(mean/std)가 정책 *앞단*에 있음. ONNX export 시 정규화를 네트워크에 baking → onnx 입력은 **raw 48-d obs**, 내부에서 정규화. (export 시 normalizer mean/std 함께 박제)

## 제어 (joystick.py `default_config` + `step`)

| 항목 | 값 |
|---|---|
| ctrl_dt | 0.02 → **50 Hz** 제어 |
| sim_dt | 0.004 → n_substeps = 5 |
| action_scale | 0.5 |
| action 적용 | `motor_targets = default_pose + action * 0.5` → ctrl, `mj_step` ×5 |
| Kp / Kd | 35.0 / 0.5 (MJCF position actuator) |
| nu (액추에이터) | 12 |
| default_pose | MJCF `keyframe("home").qpos[7:]` (12) |
| command 범위 | a=[1.5, 0.8, 1.2] (vx,vy,vyaw 최대 진폭) |

## 센서 이름 (go1_constants.py)
- `GYRO_SENSOR = "gyro"`, `LOCAL_LINVEL_SENSOR = "local_linvel"`, `GLOBAL_LINVEL_SENSOR = "global_linvel"`, `UPVECTOR_SENSOR`(gravity용)
- **native parity 전략**: 손계산 대신 동일 MJCF의 named 센서를 `data.sensordata`에서 읽음 → 학습 sim과 자동 일치.

## 종료(넘어짐) 판정
- `get_upvector(data)[-1] < 0.0` → fall (몸통 z축이 아래로 뒤집힘). native 검증의 "안 넘어짐" 기준과 동일하게 사용.
