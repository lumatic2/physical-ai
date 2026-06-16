# 27-g1-squat-contact-controller — contact-preserving stage 0.74 controller probe

> M19j. exp26에서 `blend_0p20`이 stage 0.74 depth/hold 후보를 만들었지만 foot contact ratio가 0.71에 그쳤다. 이번 실험은 같은 native MuJoCo rollout에서 좁은 blend sweep과 contact guard를 비교해 contact gate를 닫을 수 있는지 확인한다.

## 1. 가설 (Hypothesis)

stage 0.74 reference blend를 0.15~0.25 범위로 좁히고, 양발 접촉이 끊긴 직후 blend를 낮추는 contact guard를 넣으면 `min_height <= 0.745m`, hold 0.5s, return-to-stand, foot contact ratio 0.90을 동시에 만족하는 controller 후보를 찾을 수 있다.

반증 기준:
- 모든 narrow blend가 exp26처럼 contact ratio 0.90에 못 미친다.
- contact guard가 contact ratio는 높이지만 depth를 다시 standing attractor로 되돌린다.
- contact guard가 fall 또는 excessive foot slip을 만든다.

## 2. 방법 (Method)

planning_gate:
  team_validation_mode: manual-pass
  spec_delta: "exp26의 contact gap을 exp27 contact-preserving controller probe로 좁힌다."
  perspectives:
    product: "M19의 다음 결정을 '더 깊게'가 아니라 'contact 유지'로 분명히 한다."
    architecture: "exp26 native evaluator를 확장하되 새 실험 폴더에서 독립 evidence를 만든다."
    security: "secret, network, 외부 권한 없음. 로컬 WSL/JAX/MuJoCo만 사용한다."
    qa: "py_compile + 6초 native probe JSON/MD를 verify에 보존한다."
    skeptic: "guard는 contact를 올리는 대신 depth를 없앨 수 있으므로 depth/contact trade-off를 그대로 기록한다."
  dod:
    - "narrow blend와 contact-guard variants가 같은 metric으로 비교된다."
    - "verify/g1-squat-contact-controller.json 생성"
    - "contact gate PASS 여부와 다음 병목 verdict가 명시된다."

### 셋업
- 모델: exp25 `G1SquatCurriculum(stage_height=0.74)`.
- source params: exp22 depth fine-tune params, 없으면 exp21 stabilizer params.
- engine: native MuJoCo 50Hz closed-loop rollout.

### 시나리오
- S0: `policy_only`.
- S1-S5: `blend_0p15`, `blend_0p18`, `blend_0p20`, `blend_0p22`, `blend_0p25`.
- S6-S8: `guard_0p20_floor_0p05`, `guard_0p22_floor_0p08`, `guard_0p25_floor_0p10`.

### 측정 metric
- `fell_at`
- `upright_s`
- `min_height`
- `hold_duration_at_or_below_stage`
- `final_height`
- `return_to_stand`
- `torso_up_min`
- `foot_contact_ratio`
- `foot_slip_distance`
- `max_joint_limit_violation`
- `mean_effective_blend`

## 3. 결과 (Results)

### 데이터
| Run | Verdict | Cost | Retries | 비고 |
|-----|---------|------|---------|------|
| py_compile | PASS | local Python | 0 | syntax/import path 확인 |
| native contact controller probe | CONTACT_CONTROLLER_DEPTH_NEEDS_CONTACT | local WSL/JAX + native MuJoCo / 6.0s x 9 variants | 0 | depth/hold는 blend corridor에서 가능하지만 contact gate는 미달 |

| Variant | Verdict | Min height | Fell at | Hold <= stage | Final height | Foot contact | Mean blend |
|---|---|---:|---:|---:|---:|---:|---:|
| policy_only | NO_FALL_DEPTH_PENDING | 0.7501 | never | 0.00s | 0.7512 | 1.00 | 0.000 |
| blend_0p15 | NO_FALL_DEPTH_PENDING | 0.7458 | never | 0.00s | 0.7470 | 0.78 | 0.150 |
| blend_0p18 | STABLE_DEPTH_CONTACT_GAP | 0.7437 | never | 0.54s | 0.7445 | 0.73 | 0.180 |
| blend_0p20 | STABLE_DEPTH_CONTACT_GAP | 0.7412 | never | 0.86s | 0.7422 | 0.72 | 0.200 |
| blend_0p22 | STABLE_DEPTH_CONTACT_GAP | 0.7395 | never | 1.08s | 0.7406 | 0.68 | 0.220 |
| blend_0p25 | STABLE_DEPTH_CONTACT_GAP | 0.7320 | never | 1.48s | 0.7437 | 0.63 | 0.250 |
| guard_0p20_floor_0p05 | NO_FALL_DEPTH_PENDING | 0.7478 | never | 0.00s | 0.7489 | 0.78 | 0.160 |
| guard_0p22_floor_0p08 | NO_FALL_DEPTH_PENDING | 0.7452 | never | 0.00s | 0.7473 | 0.76 | 0.179 |
| guard_0p25_floor_0p10 | STABLE_TOUCH_DEPTH | 0.7441 | never | 0.10s | 0.7463 | 0.73 | 0.202 |

### 박제 위치
- `verify/g1-squat-contact-controller.json`
- `verify/g1-squat-contact-controller.md`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- stage 0.74에서 depth/hold가 가능한 corridor는 `blend_0p18~0p25`다. 이 구간은 fall 없이 min height 0.7437m -> 0.7320m까지 내려간다.
- 하지만 blend를 키울수록 foot contact ratio가 0.73 -> 0.63으로 떨어진다. depth와 contact가 현재 controller에서 trade-off 관계다.
- `guard_*` variants는 contact를 0.73~0.78 수준으로만 유지했고, 대부분 depth/hold를 다시 잃었다. 단순 “접촉 끊기면 blend 낮추기” heuristic으로는 contact gate 0.90을 닫지 못한다.
- policy-only는 contact 1.00이지만 depth가 없고, blend corridor는 depth가 있지만 contact가 없다. 다음 병목은 reference target 크기가 아니라 stance/contact-aware learning objective다.

### 가설은 통과했나?
- [ ] PASS — stage depth, hold, return, foot contact 0.90을 모두 만족한다.
- [x] FAIL_PARTIAL — depth/hold corridor는 좁혀졌지만 contact-preserving controller는 실패했다.

### 정의에 반영
- M19의 다음 step은 heuristic controller 추가가 아니라 `blend_0p18~0p22` 주변에서 stance/contact reward를 명시적으로 학습하는 fine-tune이다.

### 다음 실험 후보
- exp28: exp25 env에 foot contact 유지, foot slip 억제, return-to-stand를 강화한 reward를 넣고 `blend_0p18~0p22` reference corridor로 짧은 PPO fine-tune을 실행한다.
- fine-tune이 contact gate를 닫기 전에는 stage 0.72로 내려가지 않는다.
