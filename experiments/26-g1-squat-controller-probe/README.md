# 26-g1-squat-controller-probe — stabilizer-preserving squat controller probe

> M19i. exp25가 stage 0.74에서 no-fall은 유지했지만 standing attractor에 머물렀기 때문에, 추가 PPO 전에 stabilizer policy와 staged squat reference를 어떻게 섞어야 실제 depth가 생기는지 native MuJoCo에서 분리 검증한다.

## 1. 가설 (Hypothesis)

exp22 stabilizer policy의 closed-loop action을 유지하되 stage 0.74 reference pose를 작은 비율로 섞으면, G1은 direct target처럼 즉시 넘어지지 않으면서 standing height보다 낮은 controlled lowering을 만들 수 있다.

반증 기준:
- policy-only와 모든 blend variant가 6초 no-fall을 유지하지만 min height가 0.745m보다 높다.
- blend가 height drop을 만들지만 exp23처럼 fall한다.
- reference blend가 joint limit, foot contact, return-to-stand metric을 크게 망가뜨린다.

## 2. 방법 (Method)

planning_gate:
  team_validation_mode: manual-pass
  spec_delta: "exp25 depth curriculum 다음 단계로 stabilizer-preserving controller probe를 추가한다."
  perspectives:
    product: "M19의 다음 의사결정을 장시간 PPO가 아니라 눈으로 확인 가능한 native evidence로 좁힌다."
    architecture: "exp25 env와 source params를 재사용하고, 새 실험은 controller arbitration만 분리한다."
    security: "secret, network, 외부 권한 없음. 로컬 WSL/JAX/MuJoCo만 사용한다."
    qa: "py_compile + 6초 native probe JSON/MD를 verify에 보존한다."
    skeptic: "blend가 안정성을 깨거나 깊이를 못 만들면, 학습 전에 controller 구조를 다시 정해야 한다."
  dod:
    - "policy-only baseline과 blend variants가 같은 metric으로 평가된다."
    - "verify/g1-squat-controller-probe.json 생성"
    - "stable depth 후보 또는 다음 병목 verdict가 명시된다."

### 셋업
- 모델: exp25 `G1SquatCurriculum(stage_height=0.74)`.
- source params: exp22 depth fine-tune params, 없으면 exp21 stabilizer params.
- engine: native MuJoCo 50Hz closed-loop rollout.

### 시나리오
- S0: `policy_only` - exp22/21 policy action만 사용한다.
- S1: `blend_0p10` - policy motor target과 stage reference pose를 10% blend한다.
- S2: `blend_0p20` - 20% blend.
- S3: `blend_0p35` - 35% blend.
- S4: `blend_0p50` - 50% blend.

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
- `mean_action_delta`

## 3. 결과 (Results)

### 데이터
| Run | Verdict | Cost | Retries | 비고 |
|-----|---------|------|---------|------|
| py_compile | PASS | local Python | 0 | syntax/import path 확인 |
| native controller probe | CONTROLLER_DEPTH_NEEDS_CONTACT | local WSL/JAX + native MuJoCo / 6.0s x 5 variants | 1 | 첫 판정은 contact gate 누락으로 과대 판정되어 strict criterion으로 재실행 |

| Variant | Verdict | Min height | Fell at | Hold <= stage | Final height | Foot contact |
|---|---|---:|---:|---:|---:|---:|
| policy_only | NO_FALL_DEPTH_PENDING | 0.7501 | never | 0.00s | 0.7512 | 1.00 |
| blend_0p10 | NO_FALL_DEPTH_PENDING | 0.7501 | never | 0.00s | 0.7502 | 0.87 |
| blend_0p20 | STABLE_DEPTH_CONTACT_GAP | 0.7412 | never | 0.86s | 0.7430 | 0.71 |
| blend_0p35 | DEPTH_WITH_FALL | -0.7640 | 2.36s | 3.28s | -0.7561 | 0.71 |
| blend_0p50 | DEPTH_WITH_FALL | -0.7886 | 1.54s | 4.98s | -0.7443 | 0.88 |

### 박제 위치
- `verify/g1-squat-controller-probe.json`
- `verify/g1-squat-controller-probe.md`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- exp25의 standing attractor는 controller arbitration으로 깰 수 있다. `blend_0p20`은 6초 동안 fall 없이 stage 0.74 근처까지 내려가고, 0.86초 동안 stage band를 유지했다.
- 하지만 `blend_0p20`의 foot contact ratio는 0.71이다. exp24/25 success gate의 양발 접촉 기준 0.90에는 못 미치므로 아직 controlled squat PASS가 아니다.
- `blend_0p10`은 너무 약해서 policy-only와 거의 같은 0.750m 근처에 머문다.
- `blend_0p35`와 `blend_0p50`은 깊이를 만들지만 1.54~2.36초에 fall한다. direct target 강제보다 낫지만, reference blend를 너무 크게 주면 안정성이 무너진다.

### 가설은 통과했나?
- [ ] PASS — stage depth, hold, return, foot contact를 모두 통과한다.
- [x] FAIL_PARTIAL — depth와 hold 후보는 찾았지만 contact/stance gate가 미달이다.

### 정의에 반영
- 다음 M19 실험은 target height를 더 낮추는 것이 아니라 `blend_0p20` 주변에서 stance/contact reward 또는 foot-contact-preserving controller를 추가해야 한다.

### 다음 실험 후보
- exp27: `blend_0p15~0p25` 좁은 sweep + stance/contact penalty를 추가해 `foot_contact_ratio >= 0.90`을 먼저 닫는다.
- contact gate가 닫히면 stage 0.72로 낮추고, 그 뒤에 ONNX/browser playback으로 연결한다.
