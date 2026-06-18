# 96-g1-moves-native-reference-tracker-probe — G1 Moves native reference tracking gate

> `experiments/96-g1-moves-native-reference-tracker-probe/README.md` — G1 Moves retargeted reference가 local G1 native dynamics에서 exp29 visible squat gate를 닫는지 검증한다.

## 1. 가설 (Hypothesis)

G1 Moves의 G1 retargeted motion은 local qpos[36] 계약으로 흡수됐으므로, root quaternion order와 stance support를 맞춘 native reference tracker가 exp29 visible squat gate를 통과할 수 있다.

## 2. 방법 (Method)

### 셋업
- 모델: local MuJoCo G1 model + 기존 stabilizer policy prior + stance qfrc helpers.
- 데이터: exp95가 만든 `J_Dance4_Broadway` 6s excerpt, 360 frames at 60Hz.
- 근거:
  - G1 Moves dataset: https://huggingface.co/datasets/exptech/g1-moves (accessed 2026-06-18)
  - G1 Moves Space ONNX note: https://huggingface.co/spaces/exptech/g1-moves (accessed 2026-06-18)
  - UniTracker whole-body tracking motivation: https://arxiv.org/html/2507.07356v3 (accessed 2026-06-18)

### 시나리오
- `as-recorded-open-loop`: CSV root quaternion을 기록 순서 그대로 두고 reference qpos를 open-loop로 재생.
- `converted-open-loop`: G1 Moves 문서의 `xyzw` root quaternion을 MuJoCo `wxyz`로 변환해 open-loop 재생.
- `converted-pd-{weak,medium,strong}`: 변환된 root quaternion, reference joint target, stance force, preload를 결합.
- `keyframe-joints-medium`: stabilizer keyframe base에서 시작해 reference joints만 medium tracking.

### 측정 metric
- exp29 visible gate: no-fall, pelvis drop >= 0.08m, knee delta >= 0.60rad, hip pitch delta >= 0.35rad, return-to-stand, contact >= 0.90, slip <= 0.08m, joint limit violation <= 0.05rad.
- 추가 metric: support/ZMP margin, max qfrc, max reference error, native rollout trajectory.

## 3. 결과 (Results)

### 데이터
| Run | Verdict | Drop | Knee | Hip | Contact | Slip | Fell | 비고 |
|-----|---------|------|------|-----|---------|------|------|------|
| as-recorded-open-loop | FAIL_FALL | 1.582m | 1.726 | 1.495 | 0.51 | 0.861m | 0.00s | quaternion/order mismatch branch는 즉시 붕괴 |
| converted-open-loop | FAIL_FALL | 1.583m | 1.821 | 1.494 | 0.60 | 0.741m | 1.20s | root quaternion 변환 후에도 open-loop는 불안정 |
| converted-pd-weak | FAIL_FALL | 1.575m | 1.158 | 0.672 | 0.88 | 0.473m | 1.12s | stance 유지 부족 |
| converted-pd-medium | FAIL_FALL | 1.567m | 1.228 | 0.988 | 0.87 | 0.353m | 1.42s | fall/contact/slip 미달 |
| converted-pd-strong | FAIL_FALL | 1.577m | 1.840 | 1.371 | 0.85 | 0.330m | 1.42s | best score지만 native visible gate 실패 |
| keyframe-joints-medium | FAIL_FALL | 1.521m | 1.110 | 1.077 | 0.88 | 0.393m | 0.88s | keyframe start도 fall |

### 박제 위치
- Runner: `run_g1_moves_native_reference_tracker_probe.py`
- Raw summary: `verify/g1-moves-native-reference-tracker-probe/result.json`
- Markdown summary: `verify/g1-moves-native-reference-tracker-probe/g1-moves-native-reference-tracker-summary.md`
- Per-variant native traces: `verify/g1-moves-native-reference-tracker-probe/*/native-eval.json`
- Per-variant web trajectory candidates: `verify/g1-moves-native-reference-tracker-probe/*/native_rollout_web_trajectory.json`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- exp95의 G1 Moves reference는 kinematic target으로는 충분히 깊고 knee/hip 조건도 넘지만, local raw PD/reference playback은 native dynamics에서 안정적으로 추적하지 못한다.
- `xyzw -> wxyz` 변환은 필요하지만 충분조건이 아니다. open-loop와 PD-tracking 모두 contact, slip, fall gate에서 무너진다.
- 웹 근거상 G1 Moves 쪽은 160-input/29-output ONNX policy를 함께 제공한다. 다음 단계는 CSV를 더 세게 재생하는 것이 아니라 ONNX policy loading contract 또는 learned whole-body tracker route다.

### 가설은 통과했나?
- [ ] PASS
- [x] FAIL — best run `converted-pd-strong`은 drop/knee/hip은 충분했지만 1.42s fall, contact 0.85, slip 0.330m로 exp29 visible gate를 통과하지 못했다.

### 정의에 반영
- M19 완료 조건은 그대로 유지한다. native rollout과 browser replay가 동시에 visible gate를 통과해야 한다.

### 다음 실험 후보
- G1 Moves ONNX policy bundle의 input/output normalization contract를 로컬 checker로 검증한다.
- policy 직접 실행이 가능하면 `160 obs -> 29 action`을 native rollout에 연결하고, 통과 후보에 대해서만 browser replay QA를 수행한다.
