# 12-policy-gallery-comparison — comparable policy gallery

> M17. 기존 command sweep raw JSON을 같은 표로 묶어 policy gallery를 비교 가능한 실험판으로 만든다.

## 1. 가설 (Hypothesis)

Go1, Spot, G1, Barkour policy를 같은 command sweep schema로 요약하면, 단순히 "많이 넣었다"가 아니라 어떤 embodiment/policy가 forward, strafe, turn, diagonal 명령에서 어떻게 다른지 5분 안에 비교할 수 있다.

반증 기준:
- raw sweep schema가 달라서 같은 metric으로 묶을 수 없다.
- 표가 pass/fail만 보여주고 실제 차이(거리, yaw, drift)를 드러내지 못한다.

## 2. 방법 (Method)

### 셋업
- 입력: exp07, exp08, exp10의 `*-command-sweep*.json`.
- 출력: `verify/policy-gallery-summary.json`, `verify/policy-gallery-report.md`.

### 시나리오
- S1: 대표 policy/terrain sweep JSON을 수집한다.
- S2: scenario별 `dx`, `dy`, `distance`, `dyaw`, height, fall/NaN/error를 추출한다.
- S3: policy별 forward/strafe/turn/diagonal 요약표와 주의점을 만든다.

### 측정 metric
- forward `dx`, strafe `dy`, turn `dyaw`, diagonal distance, fall/NaN/console error count.

## 3. 결과 (Results)

### 데이터
| Run | Verdict | Cost | Retries | 비고 |
|-----|---------|------|---------|------|
| S1-S3 aggregate | PASS | 6 sweep reports | 0 | Go1/Spot/G1/Barkour, flat/rough, local/live report를 같은 schema로 요약 |

### 요약표
| Policy | Terrain | Live | forward dx | drift y | diagonal dist | failures |
|---|---|---:|---:|---:|---:|---:|
| go1-walk | flat | no | 5.89 | 0.18 | 5.06 | 0 |
| spot-walk | flat | no | 5.47 | 0.22 | 4.98 | 0 |
| go1-rough-walk | rough | yes | 5.83 | 0.11 | 4.98 | 0 |
| spot-rough-walk | rough | yes | 5.20 | 0.54 | 4.99 | 0 |
| g1-rough-walk | rough | yes | 5.03 | 0.06 | 3.62 | 0 |
| barkour-walk | flat | yes | 2.75 | 0.50 | 5.34 | 0 |

### 박제 위치
- `verify/policy-gallery-summary.json`
- `verify/policy-gallery-report.md`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- 비교 대상 sweep 6개 모두 failures=0이다. 낙상, NaN, console error 없이 같은 schema에 들어왔다.
- Go1은 forward baseline이 가장 깔끔하고, rough에서도 forward progress가 거의 유지된다.
- Spot은 안정적이지만 기존 rough report에서는 Go1보다 drift가 더 크다.
- G1 rough는 humanoid 축을 추가한다. protocol 비교는 가능하지만 morphology 차이 때문에 거리 수치만으로 4족과 직접 우열을 말하면 안 된다.
- Barkour는 465-d history observation policy까지 흡수했지만, lateral/yaw convention은 user-facing teleop 문구 전에 별도 라벨링이 필요하다.

### 가설은 통과했나?
- [x] PASS — 서로 다른 raw sweep JSON을 같은 metric 표로 묶었고, policy별 강점/주의점이 5분 안에 드러난다.
- [ ] FAIL — 무엇이 어긋났나, 가설 수정

### 정의에 반영
- README/live demo 메시지에서 "policy count"보다 "same protocol comparison"을 강조한다.

### 다음 실험 후보
- rough terrain을 Barkour/G1에도 추가해 flat-vs-rough 비교를 넓힌다.
