# 97-g1-moves-onnx-policy-contract-probe — G1 Moves ONNX policy contract gate

> `experiments/97-g1-moves-onnx-policy-contract-probe/README.md` — G1 Moves public ONNX policy가 M19의 learned tracker route로 쓸 수 있는지 입출력 계약을 검증한다.

## 1. 가설 (Hypothesis)

G1 Moves가 제공하는 public ONNX policy는 exp96에서 실패한 raw reference playback을 대체할 수 있는 learned tracker 후보이며, 로컬 native rollout으로 넘어가기 전에 `obs -> action` 계약과 sidecar observation 구성을 기계적으로 확인할 수 있다.

## 2. 방법 (Method)

### 셋업
- 모델: G1 Moves `J_Dance4_Broadway` public ONNX artifacts.
- 데이터: Hugging Face dataset tree, `policy/`, `policy_154/`, `training/J_Dance4_Broadway.npz`.
- 실행: `onnx.checker` + `onnxruntime` CPU smoke. ONNX 바이너리는 임시 디렉터리에만 내려받고, 레포에는 SHA/shape/smoke 결과만 저장한다.
- 근거:
  - G1 Moves dataset: https://huggingface.co/datasets/exptech/g1-moves (accessed 2026-06-18)
  - G1 Moves Space: https://huggingface.co/spaces/exptech/g1-moves (accessed 2026-06-18)

### 시나리오
- `policy/J_Dance4_Broadway.onnx`: `obs[1,160] + time_step[1,1] -> actions[1,29] + joint/body trajectory outputs`.
- `policy/J_Dance4_Broadway_policy.onnx`: pure actor `obs[batch,160] -> actions[batch,29]`.
- `policy_154/J_Dance4_Broadway_policy.onnx`: deployment actor `obs[1,154] + time_step[1,1] -> actions[1,29] + joint/body trajectory outputs`.

### 측정 metric
- Hugging Face tree listing contains expected policy/training sidecars.
- ONNX checker passes.
- `onnxruntime` inference is finite and deterministic for zero, small-ramp, and unit-ramp inputs.
- actor observation terms can be inferred from `env.yaml`.
- native rollout readiness is not claimed unless local observation adapter can be built.

## 3. 결과 (Results)

### 데이터
| Artifact | Input | Output | Time step | Smoke | Unit-ramp action range |
|----------|-------|--------|-----------|-------|------------------------|
| `policy/J_Dance4_Broadway.onnx` | `[1,160]` | `[1,29]` | yes | PASS | -2.047..3.033 |
| `policy/J_Dance4_Broadway_policy.onnx` | `[batch,160]` | `[batch,29]` | no | PASS | -2.440..3.083 |
| `policy_154/J_Dance4_Broadway_policy.onnx` | `[1,154]` | `[1,29]` | yes | PASS | -2.896..2.665 |

Actor observation inference:
- 160-d policy: `command 58 + motion_anchor_pos_b 3 + motion_anchor_ori_b 6 + base_lin_vel 3 + base_ang_vel 3 + joint_pos 29 + joint_vel 29 + actions 29`.
- 154-d policy: `command 58 + motion_anchor_ori_b 6 + base_ang_vel 3 + joint_pos 29 + joint_vel 29 + actions 29`.

Verdict: `PASS_ONNX_CONTRACT__NATIVE_ADAPTER_PENDING`.

### 박제 위치
- Runner: `run_g1_moves_onnx_policy_contract_probe.py`
- Raw result: `verify/g1-moves-onnx-policy-contract-probe/result.json`
- Summary: `verify/g1-moves-onnx-policy-contract-probe/g1-moves-onnx-policy-contract-summary.md`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- public ONNX 자체는 유효하다. shape, finite inference, determinism은 모두 PASS다.
- M19에 바로 연결되지 않는 이유도 명확해졌다. 이 actor는 local exp05 G1 walking policy의 103-d locomotion obs가 아니라, 58-d generated motion command를 포함한 mjlab tracking obs를 본다.
- `policy_154`는 no-state-estimation deployment 계약으로 보이며 `motion_anchor_pos_b`와 `base_lin_vel`을 제거한 154-d actor다. 그래도 58-d motion command는 필요하다.

### 가설은 통과했나?
- [x] PASS — ONNX policy contract는 검증됐다.
- [ ] FAIL

단, native adapter는 아직 pending이다. 이 실험 하나로 M19를 닫을 수 없다.

### 정의에 반영
- M19의 다음 작업은 “더 강한 PD tracking”이 아니라 `mjlab motion-command observation adapter`다.

### 다음 실험 후보
- training NPZ와 local MuJoCo body state에서 58-d motion command를 재구성하는 adapter probe.
- adapter가 만들어지면 154-d no-state-estimation actor부터 native rollout에 붙이고 exp29 visible gate를 평가한다.
