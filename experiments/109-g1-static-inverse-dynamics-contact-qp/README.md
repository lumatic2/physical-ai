# 109-g1-static-inverse-dynamics-contact-qp — G1 static inverse-dynamics contact QP

> `experiments/109-g1-static-inverse-dynamics-contact-qp/README.md` — M19 visible squat target poses를 static inverse-dynamics contact-force QP로 평가해 full ID-QP/retrain 중 어느 쪽으로 가야 하는지 분리한다.

## 1. 가설 (Hypothesis)

Exp108의 QP-lite wrapper는 no-fall/contact/slip을 지키며 7.49cm까지 갔지만 knee/hip pose gate를 넘기지 못했다. 8cm visible target 자체가 static inverse-dynamics contact QP에서 plausible이면 controller/retrain 문제가 더 강하고, static 단계부터 residual/torque가 크면 full ID-QP도 target relaxation이 필요하다.

## 2. 방법 (Method)

### 셋업
- 모델: local MuJoCo G1.
- poses: exp108 best no-fall pose, exp29 visible minimum pose, soft/full visible pose.
- QP 변수: left/right foot contact force `(fx, fy, fz)`.
- 목적: floating-base inverse dynamics residual, actuator torque proxy, tangential force, normal force imbalance를 최소화한다.
- 제약: unilateral normal force, friction cone, total normal force cap.

### 웹 근거
- MuJoCo dynamics identity는 inverse dynamics에서 `tau = M*qacc + c - J^T*f` 형태로 contact force가 generalized force에 들어간다고 설명한다. 접근일: 2026-06-18. https://mujoco.readthedocs.io/en/3.2.2/computation/
- Strict contact-force humanoid tracking은 floating-base humanoid의 6DoF base motion이 contact forces와 friction constraints에 의해 실현된다고 설명한다. 접근일: 2026-06-18. https://la.disneyresearch.com/wp-content/uploads/PROJECT_Humanoids-mocap_IEEE-RAS-ICHR-2013_PAPER1.pdf
- Prioritized WBC with contact constraints는 floating-base dynamics와 reaction forces만 포함하는 QP를 효율적 중간 문제로 사용한다. 접근일: 2026-06-18. https://junhyeokahn.github.io/data/kim2018_wbdc.pdf
- Position-controlled robots can struggle to control contact force directly, motivating force-control/admittance layers or policy retraining. 접근일: 2026-06-18. https://arxiv.org/html/2312.16465v3

## 3. 결과 (Results)

### 데이터
| Pose | Verdict | Drop | Knee | Hip | CoM margin | Base residual | Lower tau | Friction ratio |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| exp108-best-no-fall | BASE_DYNAMICS_RESIDUAL_HIGH | 0.075m | 0.382 | 0.210 | 0.0837m | 94228.45 | 4996.91 | 0.000 |
| exp29-visible-min | STATIC_ID_QP_PLAUSIBLE | 0.080m | 0.600 | 0.350 | 0.0718m | 5.14 | 25.36 | 0.012 |
| visible-soft-pose | BASE_DYNAMICS_RESIDUAL_HIGH | 0.085m | 0.500 | 0.300 | 0.0693m | 53268.00 | 3487.92 | 0.000 |
| visible-full-pose | STATIC_ID_QP_PLAUSIBLE | 0.090m | 0.640 | 0.380 | 0.0674m | 4.28 | 25.75 | 0.010 |

Best static pose: `visible-full-pose` -> `STATIC_ID_QP_PLAUSIBLE`.

### 박제 위치
- `verify/result.json`
- `verify/static-id-contact-qp-summary.md`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- Static inverse-dynamics contact QP는 native rollout과 다른 gate다. 여기서 plausible해도 M19는 닫히지 않는다.
- Best static pose는 `visible-full-pose`이고 verdict는 `STATIC_ID_QP_PLAUSIBLE`이다.
- 이 결과는 다음 구현에서 full ID-QP controller를 만들지, reference-motion retrain으로 넘어갈지 판단하는 중간 증거다.
- Static qpos 구성과 ankle/pose 관계에 민감하므로 이 실험은 rollout proof가 아니라 route-selection diagnostic으로만 쓴다.

### 가설은 통과했나?
- [x] PASS — visible target 중 static ID-QP plausible 후보가 있다.
- [ ] FAIL — visible target이 static ID-QP에서도 바로 plausible하지 않다.

### 정의에 반영
- M19 완료는 여전히 native exp29 visible gate + browser replay다. Static ID-QP는 route selection evidence일 뿐이다.
