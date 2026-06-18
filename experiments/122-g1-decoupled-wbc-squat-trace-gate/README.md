# 122-g1-decoupled-wbc-squat-trace-gate

## 1. Hypothesis

GR00T/SONIC C++ deployment path가 TensorRT 없이 막히더라도, GR00T Decoupled WBC의 G1 Balance ONNX를 WSL-native MuJoCo에서 돌리면 M19가 요구한 "동등한 deployable WBC trace"를 얻을 수 있다. 그 measured qpos trace가 exp29 visible squat gate와 기존 browser replay QA를 동시에 통과하면 M19의 humanoid skill baseline을 닫을 수 있다.

## 2. Method

- WSL-native `/home/yusun/gr00t-wbc-native`에서 GR00T WBC model assets를 다운로드하고, Decoupled WBC G1 MuJoCo loop를 headless로 실행했다.
- `GR00T-WholeBodyControl-Balance.onnx`에 pelvis height command schedule을 넣고 `low_0p70`, `low_0p68`, `low_0p66`, `low_0p64` 네 변형을 50Hz로 기록했다.
- 첫 1초 settle 구간은 제외하고 6초 measured qpos trace를 평가했다.
- PASS 기준은 exp29 visible squat gate와 stance gate를 합쳤다: pelvis drop >=0.08m, knee flexion delta >=0.60rad, hip pitch delta >=0.35rad, final height error <=0.015m, bilateral foot contact ratio >=0.95, max foot slip <=0.05m.
- PASS trace를 `physical-ai-web-trajectory-v1`로 변환해 `g1-decoupled-wbc-squat` browser replay에 등록하고 Playwright visual QA를 실행했다.

Sources accessed 2026-06-18:
- https://nvlabs.github.io/GR00T-WholeBodyControl/references/decoupled_wbc.html
- https://nvlabs.github.io/GR00T-WholeBodyControl/getting_started/download_models.html

## 3. Results

Verdict: ✅ `M19_NATIVE_TRACE_PASS__BROWSER_REPLAY_QA_PASS`

Best variant: `low_0p64`

| Metric | Result | Gate |
|---|---:|---:|
| Pelvis drop | 0.1159m | >=0.0800m |
| Knee flexion delta | 0.7069rad | >=0.6000rad |
| Hip pitch delta | 0.4272rad | >=0.3500rad |
| Final height error | 0.0036m | <=0.0150m |
| Bilateral contact ratio | 1.000 | >=0.950 |
| Max foot slip | 0.0028m | <=0.0500m |

Browser replay QA:

```bash
node qa/visual_check.mjs --exp=g1-decoupled-wbc-squat
```

Result: PASS, replay mode, 300 frames, `nq=36`, console errors 0.

Artifacts:
- `verify/result.json`
- `verify/summary.md`
- `verify/raw_decoupled_wbc_rollouts.json`
- `verify/low_0p64_web_trajectory.json`
- `verify/low_0p64_web_contract_summary.json`
- `verify/browser_replay_qa.txt`
- `../03-digital-twin/g1_decoupled_wbc_squat_trajectory.json`
- `../03-digital-twin/web/g1_decoupled_wbc_squat_trajectory.json`

## 4. Insights

- M19의 병목은 "G1 geometry가 squat를 못 담는다"가 아니라 local controller/reward family가 contact, slip, return을 동시에 못 닫는 문제였다. Decoupled WBC는 같은 G1 29-DOF browser contract에서 visible depth와 stance safety를 동시에 통과했다.
- C++ GEAR-SONIC deployment path는 여전히 TensorRT runtime이 필요하다. 이 실험은 real-robot telemetry가 아니라 measured MuJoCo WBC trace이므로, real robot twin이나 DDS telemetry는 별도 future work로 남긴다.
- Public gallery에는 기존 `g1-controlled-squat` micro-dip을 남기고, 새 `g1-decoupled-wbc-squat`를 별도 visible squat evidence로 추가했다. 이전 실패 증거를 지우지 않고 비교 가능하게 둔다.
