# 08-policy-expansion — G1 rough policy package absorption

> M13. M10/M11 정책 플랫폼이 새 policy package를 반복적으로 흡수하는지 확인한다.
> 상태: 완료 — G1 rough scene + registry + native/web/local/live QA PASS.

## 1. 가설 (Hypothesis)

G1 humanoid policy도 Go1/Spot과 같은 절차로 rough terrain 변형을 흡수할 수 있다. 즉 새 scene XML과 `experiments.json` 항목만 추가하고, G1 전용 런타임은 exp 인자만 받도록 일반화하면 native parity와 browser closed-loop가 유지된다.

반증 조건:
- G1 rough scene이 MuJoCo WASM에서 로드되지 않는다.
- bundled scene 첫 obs가 golden fixture와 어긋난다.
- browser closed-loop에서 NaN, 낙상, console error가 발생한다.
- 기존 Go1/G1/Spot 정책 회귀가 발생한다.

## 2. 방법 (Method)

### 후보 선정

- Barkour/Go2/H1 후보는 현재 작업트리에 Playground 소스, trained checkpoint, ONNX artifact가 없다.
- 따라서 이번 M13 pass는 새 학습이 아니라 **G1 policy package 변형 흡수**를 선택했다.
- M12에서 Go1/Spot rough만 닫혔으므로, G1 rough는 obs layout(103-d + gait phase clock)이 다른 정책군의 반복성 검증이다.

### 변경

- `g1/scene_g1_rough.xml`: flat G1 policy scene에 1/2/3cm curb 3개 추가.
- `experiments.json`: `g1-rough-walk` 추가.
- `rollout_g1.py`: `python rollout_g1.py [experiment] [seconds]` 지원. 기존 `python rollout_g1.py 12`는 `g1-walk`로 유지.
- `manifest.json`, `web/experiments.json`: canonical registry에서 재동기화.

### 게이트

```bash
python experiments/03-digital-twin/rollout_g1.py g1-rough-walk 12
cd experiments/03-digital-twin/web
node qa/loadtest.mjs g1/scene_g1_rough.xml
node qa/visual_check.mjs --exp=g1-rough-walk --steps=120 --chunk=40
node qa/command_sweep.mjs --exp=g1-rough-walk --measure-only --out=../../08-policy-expansion/verify/g1-rough-command-sweep.json
node qa/visual_check.mjs --live --exp=g1-rough-walk --steps=120 --chunk=40
node qa/command_sweep.mjs --live --exp=g1-rough-walk --measure-only --out=../../08-policy-expansion/verify/g1-rough-command-sweep-live.json
node qa/visual_check.mjs --exp=go1-walk --steps=80 --chunk=40
node qa/visual_check.mjs --exp=g1-walk --steps=80 --chunk=40
node qa/visual_check.mjs --exp=spot-walk --steps=80 --chunk=40
```

## 3. 결과 (Results)

### Native parity ✅

- layout parity: `0.00e+00`
- scene parity vs training golden first 5 obs: `0.00e+00`
- 12s rollout: fell `never`, upright `12.0s`, forward `9.37m`

### Web local QA ✅

- WASM load: `nq=36`, `nu=29`, `nsensor=22`
- `g1-rough-walk` visual QA: 120 steps, x `1.832m`, height `0.758m`, fell false, nan false, console errors 0
- 기존 policy 회귀:
  - `go1-walk`: PASS, 80 steps, x `1.525m`, console errors 0
  - `g1-walk`: PASS, 80 steps, x `1.135m`, console errors 0
  - `spot-walk`: PASS, 80 steps, x `1.423m`, console errors 0

### Command sweep local ✅

| Scenario | dx | dy | dyaw | h | Verdict |
|---|---:|---:|---:|---:|---|
| forward | 5.032 | 0.056 | 0.103 | 0.743 | PASS |
| strafe-left | -1.062 | 1.360 | 0.774 | 0.758 | PASS |
| strafe-right | -0.218 | -1.464 | -0.279 | 0.762 | PASS |
| turn-left | -0.009 | -0.187 | 2.317 | 0.759 | PASS |
| turn-right | 0.039 | 0.046 | -1.745 | 0.763 | PASS |
| diagonal-left | 1.981 | 3.025 | 1.304 | 0.751 | PASS |

Raw: [`verify/g1-rough-command-sweep.json`](verify/g1-rough-command-sweep.json)

### Live QA ✅

- Live URL: [`https://physical-ai-arm.askewly.com/?exp=g1-rough-walk`](https://physical-ai-arm.askewly.com/?exp=g1-rough-walk)
- visual QA: 120 steps, x `1.832m`, height `0.758m`, fell false, nan false, console errors 0
- command sweep: all 6 scenarios PASS, fell false, nan false, console errors 0
- Raw: [`verify/g1-rough-command-sweep-live.json`](verify/g1-rough-command-sweep-live.json)

## 4. 통찰 (Insights)

- **G1 rough는 새 JS 분기 없이 붙었다.** 정책 런타임의 핵심은 `obs_layout`, `policy.indices`, `gait` metadata였고, scene 변경은 registry data로 흡수됐다.
- **G1의 rough command tracking은 upright는 강하지만 drift가 크다.** forward는 안정적이고 turn도 수행하지만, strafe/diagonal에서 yaw drift가 커진다. M12의 Spot strafe보다 추종 품질은 낮다.
- **Barkour/Go2/H1은 별도 학습 pass가 필요하다.** 현재 레포에 해당 checkpoint/artifact가 없어서, 다음 정책 확장은 Playground source 확보 → train/export → native golden 생성부터 시작해야 한다.

### 정의에 반영

- M13 완료 기준은 `g1-rough-walk` live QA까지 통과해 충족했다.
- Barkour/Go2/H1은 M15 후보로 내린다. 이번 M13은 플랫폼 반복성 검증에 초점을 둔다.
