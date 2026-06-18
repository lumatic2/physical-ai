# 98-g1-moves-standalone-onnx-native-adapter-probe — G1 Moves ONNX native adapter attempt

> `experiments/98-g1-moves-standalone-onnx-native-adapter-probe/README.md` — G1 Moves README의 160-d observation map을 local MuJoCo state와 public NPZ로 재구성해 ONNX actor를 native rollout에 직접 붙여본다.

## 1. 가설 (Hypothesis)

G1 Moves README가 공개한 observation layout만으로도 local native MuJoCo에서 `J_Dance4_Broadway_policy.onnx`를 실행해 exp29 visible squat gate 후보를 만들 수 있다.

## 2. 방법 (Method)

### 셋업
- 모델: local G1 MuJoCo model + public G1 Moves pure actor ONNX.
- 데이터: `policy/J_Dance4_Broadway_policy.onnx`, `training/J_Dance4_Broadway.npz`, exp95 qpos reference excerpt.
- 외부 근거:
  - G1 Moves GitHub README observation map: https://github.com/experientialtech/g1-moves (accessed 2026-06-18)
  - G1 Moves dataset: https://huggingface.co/datasets/exptech/g1-moves (accessed 2026-06-18)

### 시나리오
- `reference-anchor-step{1.0,0.5,0.25}`: reference start pose, README layout anchor reconstruction, action target smoothing.
- `zero-anchor-step0p5`: anchor terms zero/control orientation으로 둔 ablation.
- `keyframe-anchor-step0p5`: local `knees_bent` keyframe에서 시작.
- `reference-anchor-step0p5-refblend0p15`: ONNX action target에 kinematic reference를 약하게 섞은 branch.

### 측정 metric
- exp29 visible gate: no-fall, drop >= 0.08m, knee >= 0.60rad, hip >= 0.35rad, return, contact >= 0.90, slip <= 0.08m, joint limit <= 0.05rad.
- adapter health: action range, obs absolute max, fall time, contact/slip.

## 3. 결과 (Results)

### 데이터
| Attempt | Verdict | Drop | Knee | Hip | Contact | Slip | Fell | Action range |
|---------|---------|------|------|-----|---------|------|------|--------------|
| reference-anchor-step1p0 | FAIL_FALL | 1.512m | 2.738 | 2.448 | 0.16 | 1.564m | 0.36s | -11.62..23.59 |
| reference-anchor-step0p5 | FAIL_FALL | 1.531m | 2.919 | 2.410 | 0.22 | 3.840m | 0.84s | -9.87..18.65 |
| reference-anchor-step0p25 | FAIL_FALL | 1.568m | 2.734 | 2.396 | 0.67 | 1.568m | 0.62s | -9.61..11.40 |
| zero-anchor-step0p5 | FAIL_FALL | 1.496m | 2.892 | 3.202 | 0.18 | 3.855m | 0.30s | -13.90..22.97 |
| keyframe-anchor-step0p5 | FAIL_FALL | 1.523m | 2.325 | 2.272 | 0.22 | 1.591m | 0.40s | -10.02..16.03 |
| reference-anchor-step0p5-refblend0p15 | FAIL_FALL | 1.558m | 2.907 | 2.063 | 0.44 | 1.207m | 0.56s | -12.08..17.37 |

Verdict: `FAIL_VISIBLE_NATIVE`.

### 박제 위치
- Runner: `run_g1_moves_standalone_onnx_native_adapter_probe.py`
- Raw result: `verify/g1-moves-standalone-onnx-native-adapter-probe/result.json`
- Summary: `verify/g1-moves-standalone-onnx-native-adapter-probe/g1-moves-standalone-onnx-native-adapter-summary.md`
- Per-variant native traces: `verify/g1-moves-standalone-onnx-native-adapter-probe/*/native-eval.json`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- README-level obs reconstruction is not enough. obs absolute max reached about 42-51 and ONNX actions exploded to roughly -14..23rad, far outside the calm smoke-test range from exp97.
- Failure is therefore adapter distribution mismatch, not evidence that the learned G1 Moves policy itself cannot track the motion.
- Browser replay remains gated off because no native visible run passed.

### 가설은 통과했나?
- [ ] PASS
- [x] FAIL — all approximate adapter variants fell within 0.30-0.84s.

### 정의에 반영
- M19 learned route requires exact upstream `run_policy.py` / RoboJuDo-style observation construction, not a hand-rolled README approximation.

### 다음 실험 후보
- Analyze and port upstream `run_policy.py` from `experientialtech/g1-moves` or run it against local G1 XML to compare obs/action distributions.
- Add an adapter parity fixture: same timestep, same NPZ, same qpos/qvel, upstream obs vs local obs max-diff.
