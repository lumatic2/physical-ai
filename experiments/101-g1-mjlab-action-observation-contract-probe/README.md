# 101-g1-mjlab-action-observation-contract-probe — mjlab action/observation contract probe

> `experiments/101-g1-mjlab-action-observation-contract-probe/README.md` — G1 Moves ONNX 실패 원인이 anchor/order/action-scale 해석 차이인지 `mjlab` tracking source와 대조해 native sweep으로 검증한다.

## 1. 가설 (Hypothesis)

exp98-100 실패는 exact XML뿐 아니라 policy action/observation contract mismatch 때문일 수 있다. `mjlab` tracking task의 torso anchor, `base_lin_vel -> base_ang_vel` observation order, `default_joint_pos + raw_action * G1_ACTION_SCALE` target 해석을 적용하면 local G1 scene에서도 rollout 안정성이 개선될 수 있다.

## 2. 방법 (Method)

### 셋업
- 모델: local web policy scene `experiments/03-digital-twin/web/assets/scenes/g1/scene_g1_policy.xml`.
- 정책/데이터: G1 Moves `J_Dance4_Broadway_policy.onnx` + `J_Dance4_Broadway.npz`.
- 외부 source:
  - G1 Moves `run_policy.py`: https://raw.githubusercontent.com/experientialtech/g1-moves/main/run_policy.py (accessed 2026-06-18)
  - `mjlab` G1 tracking cfg: https://raw.githubusercontent.com/mujocolab/mjlab/main/src/mjlab/tasks/tracking/config/g1/env_cfgs.py (accessed 2026-06-18)
  - `mjlab` base tracking cfg: https://raw.githubusercontent.com/mujocolab/mjlab/main/src/mjlab/tasks/tracking/tracking_env_cfg.py (accessed 2026-06-18)
  - `mjlab` G1 constants/action scale: https://raw.githubusercontent.com/mujocolab/mjlab/main/src/mjlab/asset_zoo/robots/unitree_g1/g1_constants.py (accessed 2026-06-18)
  - G1 Moves HF `CLAUDE.md` exact XML note: https://huggingface.co/datasets/exptech/g1-moves/blob/fce747a1677d5e6ffbc45e04f9fbdc0252b276f5/CLAUDE.md (accessed 2026-06-18)

### 시나리오
- `run-policy-baseline`: G1 Moves standalone runner semantics: pelvis anchor index 0, ang->lin velocity order, direct target.
- `mjlab-obs-direct-zero`: torso anchor index 7, lin->ang velocity order, direct target.
- `mjlab-obs-scaled-zero`: torso anchor, lin->ang, `raw_action * G1_ACTION_SCALE`.
- `mjlab-obs-scaled-knees-bent`: torso anchor, lin->ang, `KNEES_BENT_KEYFRAME + raw_action * G1_ACTION_SCALE`.

### 측정 metric
- exp29 visible gate proxy: no-fall, drop >=8cm, knee >=0.60rad, hip >=0.35rad, return, foot slip <=8cm.
- Adapter health: action range, target range, obs absolute max, fall time.
- Browser replay는 native pass가 없으면 실행하지 않는다.

## 3. 결과 (Results)

### 데이터
| Attempt | Verdict | Drop | Knee | Hip | Slip | Fell | Action range | Target range | Obs max |
|---|---|---:|---:|---:|---:|---|---|---|---:|
| run-policy-baseline | FAIL_FALL | 4867.261m | 6124.635 | 63684.124 | 22.843m | 0.24s | -2332887.25..1569893.62 | -2332887.25..1569893.62 | 47811868.00 |
| mjlab-obs-direct-zero | FAIL_FALL | 122.707m | 815.000 | 1319.120 | 2.875m | 0.32s | -153986.00..122235.44 | -153986.00..122235.44 | 5347656.50 |
| mjlab-obs-scaled-zero | FAIL_FALL | 1.565m | 6.447 | 52.135 | 1.072m | 0.46s | -2290.23..1531.73 | -1004.44..453.34 | 34666.80 |
| mjlab-obs-scaled-knees-bent | FAIL_FALL | 1.576m | 10797.212 | 1212.632 | 20.393m | 0.36s | -587944.69..439764.66 | -257859.00..192870.61 | 18065534.00 |

Verdict: `FAIL_VISIBLE_NATIVE`.

### 박제 위치
- Runner: `run_g1_mjlab_action_observation_contract_probe.py`
- Raw result: `verify/g1-mjlab-action-observation-contract-probe/result.json`
- Summary: `verify/g1-mjlab-action-observation-contract-probe/g1-mjlab-action-observation-contract-summary.md`
- Per-variant evals: `verify/g1-mjlab-action-observation-contract-probe/*/native-eval.json`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- `mjlab` source 기준으로 보면 current tracking task는 torso anchor, lin-before-ang observation order, per-joint action scale/default offset을 사용한다.
- 이 계약을 적용하면 `mjlab-obs-scaled-zero`에서 direct target 대비 action/obs 폭주는 크게 줄지만, 0.46초 fall과 1.07m slip으로 native gate는 실패한다.
- `KNEES_BENT_KEYFRAME` offset은 첫 target은 그럴듯하지만 곧 action 폭주가 재발한다. 현재 공개 ONNX가 current `mjlab` source contract 그대로라고 가정하면 안 된다.
- 남은 병목은 단순 adapter field ordering이 아니라 exact `g1_mode15_square.xml`/sensor/dynamics 또는 local scene 재학습이다.

### 가설은 통과했나?
- [ ] PASS
- [x] FAIL — mjlab action/observation contract variants alone did not stabilize native rollout.

### 정의에 반영
- M19의 G1 Moves route는 exact training-scene acquisition 없이는 계속 소모적이다. 다음 유효 작업은 `g1_mode15_square.xml` 확보 시도 또는 local scene에서 visible squat tracker 재학습이다.

### 다음 실험 후보
- G1 Moves authoring source의 exact `g1_mode15_square.xml`을 별도 경로로 확보할 수 있는지 확인한다.
- 확보가 안 되면 public ONNX adapter를 멈추고, local `scene_g1_policy.xml` 기준으로 squat reference tracker를 새로 학습한다.
