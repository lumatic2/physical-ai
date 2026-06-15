# 16-ball-skill-sandbox — G1 ball scene and metric gate

> M21. 축구/라보나슛 전 단계로 G1 + ball scene을 만들고, `ball_tap` reward가 쓸 공 위치·속도·goal metric을 먼저 검증한다.

## 1. 가설 (Hypothesis)

G1 scene에 free ball body와 ball velocity sensor를 추가하면, `g1_ball_tap` behavior spec의 `ball_distance`와 `ball_direction_error` metric을 native MuJoCo에서 계산할 수 있다.

반증 기준:
- G1 + ball scene이 MuJoCo에서 로드되지 않는다.
- 공 freejoint 위치/속도를 읽을 수 없다.
- goal direction metric이 raw JSON으로 박제되지 않는다.

## 2. 방법 (Method)

### 셋업
- 모델: `experiments/03-digital-twin/web/assets/scenes/g1/scene_g1_ball.xml`
- 데이터: `experiments/14-skill-authoring/verify/g1_ball_tap.compiled.json`
- 하네스 구성: `evaluate_ball_scene.py`

### 시나리오
- S1: G1 feetonly model에 soccer ball freejoint body를 추가한다.
- S2: 공 초기 위치, 선속도 sensor, goal direction metric을 로드한다.
- S3: controlled x velocity를 주입해 metric path가 살아 있는지 확인한다.

### 측정 metric
- scene load `nq/nv/nu/nsensor`
- `ball_distance`
- `ball_direction_error_rad`

## 3. 결과 (Results)

### 데이터
| Run | Verdict | Cost | Retries | 비고 |
|-----|---------|------|---------|------|
| S1-S3 ball scene smoke | PASS | local MuJoCo | 0 | G1+ball scene load, ball distance/direction metric 산출 |

### 박제 위치
- `verify/g1-ball-scene-smoke.json`
- `verify/g1-ball-scene-smoke.md`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- M21의 scene/metric gate는 닫혔다. 이제 ball skill은 최소한 공 위치와 goal-direction reward를 계산할 수 있다.
- 이 실험은 kick policy 검증이 아니다. 공에 속도를 주입해 metric path만 확인했다.
- 다음 단계는 foot-ball contact reward와 G1 balance reward를 결합하는 것이다.

### 가설은 통과했나?
- [x] PASS — G1+ball scene이 로드되고 ball distance/direction metric이 raw evidence로 남았다.
- [ ] FAIL — 무엇이 어긋났나, 가설 수정

### 정의에 반영
- `ROADMAP.md` M21을 scene/metric gate 완료로 갱신한다.

### 다음 실험 후보
- `front_kick` balance-stabilized policy가 선행된 뒤, foot-ball contact reward를 붙인다.
