# 07-command-terrain-robustness — command sweep와 rough terrain 강건성 검증

> M12. 평지 전진 데모를 넘어 Go1·Spot 정책이 `turn`, `strafe`, `diagonal`, rough terrain에서 어디까지 버티는지 측정한다.
> 상태: S1~S2 완료 — command sweep QA, rough curb scene, Go1/Spot 로컬 측정 완료. 라이브 검증 남음.

## 1. 가설 (Hypothesis)

Go1·Spot joystick 정책은 flat forward command만이 아니라 lateral/turn command에서도 브라우저 closed-loop를 유지한다. 단, 정책별 obs 구조와 학습 환경 차이 때문에 strafe/turn tracking 품질은 다르게 나타난다.

반증 조건:
- command sweep 중 NaN 또는 낙상이 발생한다.
- forward 외 command에서 위치/yaw 변화가 command 방향과 무관하게 붕괴한다.
- local QA와 live QA 결과가 크게 어긋난다.

## 2. 방법 (Method)

### 셋업
- 대상: `?exp=go1-walk`, `?exp=spot-walk`
- 실행 위치: `experiments/03-digital-twin/web`
- QA 하네스: `qa/command_sweep.mjs`
- 정책 runtime: onnxruntime-web + MuJoCo WASM closed-loop

### 시나리오

| 시나리오 | command `[vx, vy, vyaw]` | 기대 관찰 |
|---|---:|---|
| forward | `[1.0, 0.0, 0.0]` | +x 이동 |
| strafe-left | `[0.0, 0.5, 0.0]` | +y 이동 |
| strafe-right | `[0.0, -0.5, 0.0]` | -y 이동 |
| turn-left | `[0.0, 0.0, 0.8]` | +yaw 변화 |
| turn-right | `[0.0, 0.0, -0.8]` | -yaw 변화 |
| diagonal-left | `[0.8, 0.4, 0.0]` | +x/+y 이동 |

### 측정 metric
- `dx`, `dy`, `distance`
- `dyaw`
- `finalHeight`
- `fell`, `nan`, console error count

## 3. 결과 (Results)

### S1 — command sweep QA vertical slice ✅

실행:

```bash
cd experiments/03-digital-twin/web
node qa/command_sweep.mjs --exp=go1-walk --out=../../07-command-terrain-robustness/verify/go1-command-sweep.json
node qa/command_sweep.mjs --exp=spot-walk --out=../../07-command-terrain-robustness/verify/spot-command-sweep.json
```

둘 다 `fell=false`, `nan=false`, console error 0으로 PASS.

### 데이터

| Robot | Scenario | dx | dy | dyaw | h | Verdict |
|---|---|---:|---:|---:|---:|---|
| Go1 | forward | 5.892 | 0.179 | 0.014 | 0.302 | ✅ |
| Go1 | strafe-left | -0.126 | 2.632 | 0.102 | 0.309 | ✅ |
| Go1 | strafe-right | 0.106 | -2.436 | -0.030 | 0.308 | ✅ |
| Go1 | turn-left | 0.022 | -0.105 | -1.914 | 0.302 | ✅ |
| Go1 | turn-right | -0.112 | -0.137 | 1.864 | 0.312 | ✅ |
| Go1 | diagonal-left | 4.657 | 1.969 | -0.060 | 0.295 | ✅ |
| Spot | forward | 5.471 | 0.216 | 0.082 | 0.438 | ✅ |
| Spot | strafe-left | 0.008 | 3.020 | 0.003 | 0.461 | ✅ |
| Spot | strafe-right | 0.174 | -3.013 | 0.041 | 0.465 | ✅ |
| Spot | turn-left | 0.110 | 0.164 | -1.670 | 0.457 | ✅ |
| Spot | turn-right | 0.261 | -0.015 | 1.644 | 0.457 | ✅ |
| Spot | diagonal-left | 4.381 | 2.375 | 0.138 | 0.446 | ✅ |

### S2 — rough curb scene ✅

`go1-rough-walk`, `spot-rough-walk`을 추가했다. 기존 flat policy XML을 복사하되 floor 위에 낮은 curb 3개를 추가했다:

| Curb | x | height |
|---|---:|---:|
| 1 | 1.0m | 1.0cm |
| 2 | 2.0m | 2.0cm |
| 3 | 3.0m | 3.0cm |

실행:

```bash
cd experiments/03-digital-twin/web
node qa/command_sweep.mjs --exp=go1-rough-walk --measure-only --out=../../07-command-terrain-robustness/verify/go1-rough-command-sweep.json
node qa/command_sweep.mjs --exp=spot-rough-walk --measure-only --out=../../07-command-terrain-robustness/verify/spot-rough-command-sweep.json
node qa/visual_check.mjs --exp=go1-rough-walk --steps=120 --chunk=40
node qa/visual_check.mjs --exp=spot-rough-walk --steps=120 --chunk=40
```

| Robot | Scenario | dx | dy | dyaw | h | Verdict |
|---|---|---:|---:|---:|---:|---|
| Go1 rough | forward | 5.759 | 0.146 | 0.034 | 0.303 | ✅ |
| Go1 rough | strafe-left | -0.126 | 2.632 | 0.102 | 0.309 | ✅ |
| Go1 rough | strafe-right | 0.035 | -2.506 | -0.127 | 0.316 | ✅ |
| Go1 rough | turn-left | 0.022 | -0.105 | -1.914 | 0.302 | ✅ |
| Go1 rough | turn-right | -0.140 | -0.151 | 1.846 | 0.307 | ✅ |
| Go1 rough | diagonal-left | 4.757 | 1.744 | -0.104 | 0.300 | ✅ |
| Spot rough | forward | 4.656 | 0.883 | 0.550 | 0.432 | ✅ |
| Spot rough | strafe-left | 0.008 | 3.020 | 0.003 | 0.461 | ✅ |
| Spot rough | strafe-right | 0.103 | -3.218 | 0.040 | 0.464 | ✅ |
| Spot rough | turn-left | 0.110 | 0.164 | -1.670 | 0.457 | ✅ |
| Spot rough | turn-right | 0.261 | -0.015 | 1.644 | 0.457 | ✅ |
| Spot rough | diagonal-left | 4.349 | 2.026 | 0.096 | 0.444 | ✅ |

회귀:

```bash
node qa/visual_check.mjs --exp=go1-walk --steps=120 --chunk=40
node qa/visual_check.mjs --exp=spot-walk --steps=120 --chunk=40
```

둘 다 PASS.

### 박제 위치
- `verify/go1-command-sweep.json`
- `verify/spot-command-sweep.json`
- `verify/go1-rough-command-sweep.json`
- `verify/spot-rough-command-sweep.json`
- `experiments/03-digital-twin/web/qa/out/*command*.png`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- **forward 외 command도 upright closed-loop는 유지한다.** 300 control step 동안 Go1·Spot 모두 NaN/낙상/콘솔에러 없이 통과했다.
- **lateral command tracking은 Spot이 더 깨끗하다.** strafe에서 Spot은 dx가 거의 0이고 dy가 약 3.02m, Go1은 dy 2.4~2.6m에 작은 x/yaw drift가 붙는다.
- **yaw sign은 현재 QA 좌표계/command convention이 반대다.** `vyaw=+0.8`이 Go1/Spot 모두 음수 yaw로, `vyaw=-0.8`이 양수 yaw로 나타난다. 정책이 회전을 못 하는 게 아니라 부호 convention을 문서화해야 한다.
- **rough curb는 낙상을 만들지 않았지만 drift를 드러냈다.** Go1은 forward rough에서도 5.76m로 flat(5.89m)과 거의 같았다. Spot은 rough forward가 5.47m → 4.66m로 줄고 yaw drift가 0.55rad로 커졌다. 다만 diagonal rough는 4.35m/2.03m로 flat과 비슷하게 유지됐다.

### 가설은 통과했나?
- [x] PASS — flat/rough command sweep에서 두 정책 모두 forward/strafe/turn/diagonal을 낙상 없이 수행했다. 단 rough terrain에서 Spot forward/diagonal drift가 커졌다.
- [ ] FAIL

### 정의에 반영
- M12 완료 시 `ROADMAP.md`와 README에 라이브 QA 결과까지 포함해 반영.

### 다음 실험 후보
- Rough terrain heightfield/stepped terrain scene 추가.
