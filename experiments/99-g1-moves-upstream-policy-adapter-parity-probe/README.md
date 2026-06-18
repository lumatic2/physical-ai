# 99-g1-moves-upstream-policy-adapter-parity-probe — upstream G1 Moves adapter choices

> `experiments/99-g1-moves-upstream-policy-adapter-parity-probe/README.md` — upstream `run_policy.py`의 observation/control 선택을 local G1 MuJoCo model에 적용해 exp98의 OOD 원인을 좁힌다.

## 1. 가설 (Hypothesis)

exp98의 실패는 README layout 자체가 아니라 hand-rolled adapter 세부 차이 때문일 수 있다. upstream `run_policy.py`의 pelvis anchor, 6D orientation flatten order, zero default pose, raw sensor velocity, PD control choices를 반영하면 native visible gate에 가까워질 수 있다.

## 2. 방법 (Method)

### 셋업
- 모델: local G1 MuJoCo model + public G1 Moves pure actor ONNX.
- 데이터: `policy/J_Dance4_Broadway_policy.onnx`, `training/J_Dance4_Broadway.npz`.
- 기준 코드: https://raw.githubusercontent.com/experientialtech/g1-moves/main/run_policy.py (accessed 2026-06-18)
- 외부 근거:
  - G1 Moves GitHub: https://github.com/experientialtech/g1-moves (accessed 2026-06-18)
  - G1 Moves dataset: https://huggingface.co/datasets/exptech/g1-moves (accessed 2026-06-18)

### 시나리오
- `upstream-exact-position`: pelvis anchor index 0, upstream 6D flatten, raw sensor velocity, zero default pose, local position actuator target.
- `upstream-exact-position-smooth0p25`: same, but action target smoothing.
- `upstream-exact-torque-pd`: upstream PD torque equation, clipped through local ctrl range.
- `named-vel-position`: local named sensors instead of raw first six `sensordata` entries.
- `rowmajor-ablation`: exp98-style row-major 6D orientation ablation.
- `torso-anchor-ablation`: exp98-style torso anchor index 7 ablation.
- `keyframe-default-position`: local keyframe default/start ablation.

### 측정 metric
- exp29 visible gate: no-fall, drop >= 0.08m, knee >= 0.60rad, hip >= 0.35rad, return, contact >= 0.90, slip <= 0.08m, joint limit <= 0.05rad.
- adapter health: first action, full action range, obs absolute max, MuJoCo instability/fall time.

## 3. 결과 (Results)

### 데이터
| Attempt | Verdict | Drop | Contact | Slip | Fell | Action range | Obs max |
|---------|---------|------|---------|------|------|--------------|---------|
| upstream-exact-position | FAIL_FALL | 117.892m | 0.08 | 7.924m | 0.24s | -585051.88..1169843.12 | 18343466.00 |
| upstream-exact-position-smooth0p25 | FAIL_FALL | 5.739m | 0.14 | 1.208m | 0.30s | -5426.99..5304.48 | 203755.59 |
| upstream-exact-torque-pd | FAIL_FALL | 2082.724m | 0.07 | 6.237m | 0.26s | -1772875.00..1150729.25 | 27135424.00 |
| named-vel-position | FAIL_FALL | 28.896m | 0.06 | 4.579m | 0.24s | -43531.12..42912.03 | 701410.25 |
| rowmajor-ablation | FAIL_FALL | 626.332m | 0.08 | 4.867m | 0.58s | -133480.81..118367.23 | 5800519.00 |
| torso-anchor-ablation | FAIL_FALL | 438.134m | 0.06 | 4.042m | 0.24s | -129668.98..83949.15 | 2225772.75 |
| keyframe-default-position | FAIL_FALL | 1.106m | 0.09 | 1.877m | 0.60s | -284964.06..511987.56 | 8339152.00 |

Verdict: `FAIL_VISIBLE_NATIVE`.

### 박제 위치
- Runner: `run_g1_moves_upstream_policy_adapter_parity_probe.py`
- Raw result: `verify/g1-moves-upstream-policy-adapter-parity-probe/result.json`
- Summary: `verify/g1-moves-upstream-policy-adapter-parity-probe/g1-moves-upstream-policy-adapter-parity-summary.md`
- Per-variant native traces: `verify/g1-moves-upstream-policy-adapter-parity-probe/*/native-eval.json`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- upstream first action itself is not absurd: first six values for `upstream-exact-position` were about `[1.36, -0.17, -0.11, -0.49, 2.48, 0.01]`.
- The rollout becomes unstable immediately in the local model. After the first steps, obs/action explode to huge values, and MuJoCo reports unstable QACC. This points to local XML/actuator semantics mismatch rather than just observation flattening.
- Browser replay remains gated off because no native visible run passed.

### 가설은 통과했나?
- [ ] PASS
- [x] FAIL — upstream adapter choices did not make local native rollout stable.

### 정의에 반영
- M19 learned route now needs model parity, not another hand-coded observation tweak. The next target is upstream `g1_mode15_square.xml` or RoboJuDo/Unitree G1 XML compatibility.

### 다음 실험 후보
- Fetch/compile upstream-compatible `g1_29dof_rev_1_0.xml`/`g1_mode15_square.xml` candidate and run the same ONNX policy against that model.
- Compare local `scene_g1_policy.xml` actuator type/range/gain against upstream `run_policy.py` torque-control expectation.
