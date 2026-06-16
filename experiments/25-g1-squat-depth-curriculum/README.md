# 25-g1-squat-depth-curriculum — staged G1 squat depth curriculum

> M19h. exp24 design gate를 구현한다. exp21 stabilizer prior에서 시작해 squat target height를 stage별로 낮추고, native no-fall/depth/return metric을 확인한다.

## 1. 가설 (Hypothesis)

exp21 walking stabilizer prior를 유지한 채 target height를 `0.74 -> 0.72 -> 0.70 -> 0.66`으로 단계적으로 낮추면, G1은 native MuJoCo에서 6초 no-fall을 유지하면서 standing attractor보다 낮은 squat-like posture를 학습할 수 있다.

반증 기준:
- stage env가 reset/step/PPO/native diagnostic에 들어가지 않는다.
- source policy와 target policy shape가 맞지 않는다.
- stage 0.74에서도 6초 no-fall을 잃는다.
- no-fall은 유지하지만 min base height가 exp22 수준인 0.750m 근처에 머문다.

## 2. 방법 (Method)

planning_gate:
  team_validation_mode: manual-pass
  spec_delta: "exp24 design gate를 exp25 staged depth curriculum 실험으로 구체화한다."
  perspectives:
    product: "M19를 브라우저 데모 이전의 native skill acquisition evidence로 닫는다."
    architecture: "exp22 runner/env 패턴을 유지하되 stage height와 verify output을 명시적으로 분리한다."
    security: "secret, network, external authority 없음. 로컬 WSL/JAX/MuJoCo만 사용한다."
    qa: "compatibility + rollout smoke + native diagnostic JSON을 stage별 verify 폴더에 보존한다."
    skeptic: "curriculum도 standing attractor에 머물 수 있으므로 첫 run은 성공보다 실패 분류가 중요하다."
  dod:
    - "stage env reset/step smoke PASS"
    - "source policy shape compatibility PASS"
    - "native diagnostic JSON 생성"

### 셋업
- 모델: G1 native MuJoCo digital twin, `scene_g1_policy.xml`.
- 데이터: exp17 squat reference motion, exp21/22 stabilizer params.
- 하네스 구성: `g1_squat_curriculum_env.py`, `run_curriculum.py`.

### 시나리오
- S0: env smoke. 각 stage target height가 reward/metric에 들어가는지 확인한다.
- S1: source params compatibility. exp22 또는 exp21 params와 network shape를 확인한다.
- S2: stage 0.74 native diagnostic. 짧은 PPO fine-tune 후 no-fall/depth/return을 평가한다.
- S3: stage PASS 시 다음 stage source로 이전 stage params를 사용한다.

### 측정 metric
- `fell_at`
- `upright_s`
- `stage_height`
- `min_height`
- `hold_duration_at_or_below_stage`
- `final_height`
- `return_to_stand`
- `torso_up_min`
- `foot_contact_ratio`
- `foot_slip_distance`
- `max_reference_error`
- `mean_action_delta`
- `stage_passed`

## 3. 결과 (Results)

### 데이터
| Run | Verdict | Cost | Retries | 비고 |
|-----|---------|------|---------|------|
| S0 env/shape/native scaffold | PASS_SCAFFOLD | local WSL/JAX + native MuJoCo | 1 | stage target metrics, shape compatibility, native JSON/log 생성 |
| S1 stage 0.74 source diagnostic | NO_FALL_DEPTH_PENDING | 6.0s native MuJoCo | 0 | no-fall 유지, min height 0.7501m, stage 0.74 depth 미달 |
| S2 stage 0.74 50k fine-tune | TIMEOUT | 7min wall timeout | 1 | train path는 시작됐지만 제한 시간 안에 완료되지 않아 PID 종료 |

### 박제 위치
- `verify/stage-0p74/g1-squat-depth-curriculum.json`
- `verify/stage-*/native-eval.log`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- exp25 runner는 exp24 design gate를 코드로 옮겼다. stage height가 env reward/metric과 native diagnostic에 들어가고, source policy shape도 target env와 맞는다.
- exp22 source policy는 stage 0.74에서 6초 no-fall, 양발 접촉 1.0, return-to-stand를 유지했다.
- 하지만 min height는 0.750064m이고 `hold_duration_at_or_below_stage`는 0.0s다. 즉 stabilizer는 유지되지만 stage 0.74조차 아직 실제 squat depth로 내려가지 않는다.
- zero-action JAX rollout은 target height 0.74 metric을 만들지만 native closed-loop policy는 standing attractor에 머문다. 다음 병목은 metric wiring이 아니라 PPO fine-tune 시간/강도 또는 residual controller 설계다.
- 50k fine-tune은 7분 제한 안에 끝나지 않았다. stage별 full training은 더 긴 timebox로 별도 실행해야 한다.

### 가설은 통과했나?
- [ ] PASS — 어떤 근거로
- [x] FAIL_PARTIAL — curriculum scaffold는 통과했지만, 아직 학습으로 stage depth 개선을 보이지 못했다. 현재 증거는 `NO_FALL_DEPTH_PENDING`이다.

### 정의에 반영
- M19의 다음 문장은 "curriculum 구현"이 아니라 "stage 0.74에서도 standing attractor를 벗어나는 controller/fine-tune 필요"로 좁힌다.

### 다음 실험 후보
- stage 0.74를 더 긴 timebox로 학습한다. 50k step이 7분 제한을 넘겼으므로 최소 15분 이상을 잡는다.
- reward만 키우기보다 residual action scale schedule 또는 stabilizer/follower head 분리를 추가한다.
- stage 0.74가 native `min_height <= 0.745m`와 hold 0.5s를 통과하기 전에는 0.72/0.70으로 내려가지 않는다.
