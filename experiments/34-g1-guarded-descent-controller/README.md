# 34-g1-guarded-descent-controller - guarded descent controller probe

> M19 follow-up after exp30. Web research says Unitree G1 can plausibly perform squat-like motions, but exp30 showed the existing controller cannot combine visible depth with stability. This experiment tests a guarded descent controller before more reward-scale training.

## 1. 가설 (Hypothesis)

If G1 squat is blocked by an over-aggressive reference blend rather than by impossible kinematics, then a native controller that caps descent rate and backs off on torso/foot-slip guards should increase visible pelvis drop without reproducing the exp30 2.06s fall.

M19 success is still strict:
- pelvis/base drop from start >= 0.08m
- `fell_at is None`
- foot contact ratio >= 0.90
- final height returns to >= 0.74m
- browser replay must pass the same visible gate before the skill is called showable

반증 기준:
- guarded blend remains stable but only produces another 1cm micro-dip.
- guarded blend reaches visible depth but still falls.
- guard backoff prevents both descent and return, proving this controller family is insufficient.

## 2. 방법 (Method)

planning_gate:
  team_validation_mode: manual-pass
  spec_delta: "M19 moves from raw reference blend to guarded descent with explicit stability backoff."
  perspectives:
    product: "사용자가 보는 스쿼트는 최소 8cm 이상 내려가는 visible motion이어야 한다."
    architecture: "exp28 native controller path를 재사용하되, blend schedule만 guarded state machine으로 분리한다."
    security: "secret 없음. local/WSL MuJoCo/JAX runtime만 사용한다."
    qa: "attempt별 native JSON과 summary를 verify/에 보존한다."
    skeptic: "guard가 conservative하면 안정성은 얻어도 depth가 다시 micro-dip으로 돌아갈 수 있다."
  dod:
    - "web feasibility sources are cited with access date."
    - "guarded variants preserve raw JSON evidence."
    - "summary states whether M19 is closed or still pending."

### 외부 근거
- Unitree G1-Comp specs, accessed 2026-06-18: knee range is listed as 0 to 165 degrees, knee torque as 120 N.m, and thigh+calf length as 0.6m. URL: https://www.unitree.com/robocup/
- Weston Robot Unitree G1 developer guide, accessed 2026-06-18: G1 has 29 joints, 6 per leg, and publishes joint limits including hip pitch, knee, ankle pitch, and waist pitch. URL: https://docs.westonrobot.com/tutorial/unitree/g1_dev_guide/
- Unitree `unitree_mujoco`, accessed 2026-06-18: official simulator supports G1 and LowCmd/LowState style low-level controller verification in MuJoCo. URL: https://github.com/unitreerobotics/unitree_mujoco
- HuB project, accessed 2026-06-18: the published G1 balance work lists "Deep Squat" as a humanoid balance task and validates on Unitree G1. URL: https://hub-robot.github.io/
- HuB paper, accessed 2026-06-18: the paper describes validation on Unitree G1 and includes Deep Squat among the showcased balance tasks. URL: https://arxiv.org/html/2505.07294v2
- G1 Controls documentation, accessed 2026-06-18: built-in Squat Mode slowly transitions to a squat position but explicitly has no balance control. URL: https://docs.quadruped.de/projects/g1/html/operation_1.2.html
- HumanUP paper, accessed 2026-06-18: Unitree G1 can bend into squat/get-up related poses, but unstable squatting can fail under nonideal support conditions. URL: https://arxiv.org/html/2502.12152v1

### 셋업
- Base runner/env: `experiments/28-g1-controlled-squat-stage0p74/run_controlled_squat.py`
- New runner: `experiments/34-g1-guarded-descent-controller/run_guarded_descent.py`
- Source params: `experiments/22-g1-squat-depth-finetune/verify/train/params.pkl` if present, else exp21 stabilizer params through the exp28 helper.
- Target stage: `0.67m`
- Reference scale: `1.0`
- Freeze phase: `true`
- Native duration: `6s`

### 시나리오
- A: conservative guard, max blend 0.65, descent rate cap 0.035m/s.
- B: medium guard, max blend 0.85, descent rate cap 0.055m/s.
- C: assertive guard, max blend 1.0, descent rate cap 0.075m/s.

### 측정 metric
- start height, min height, visible drop
- fall time
- contact ratio and max foot slip
- final height / return
- max observed blend and number of guard trips
- joint limit violation

## 3. 결과 (Results)

### 데이터
| Run | Verdict | Cost | Retries | 비고 |
|-----|---------|------|---------|------|
| smoke | DEPTH_PENDING | local Windows CPU JAX/MuJoCo 0.2s | 0 | import/env/params smoke passed; drop 0.0015m |
| conservative | FAIL_FALL | local Windows CPU JAX/MuJoCo 6s | 0 | max blend 0.65, rate cap 0.035; fall at 4.80s after foot slip/contact loss |
| medium | FAIL_FALL | local Windows CPU JAX/MuJoCo 6s | 0 | max blend 0.85, rate cap 0.055; fall at 2.66s |
| assertive | FAIL_FALL | local Windows CPU JAX/MuJoCo 6s | 0 | max blend 1.00, rate cap 0.075; visible depth reached but fall at 2.44s |
| strict-low | RETURN_PENDING | local Windows CPU JAX/MuJoCo 6s | 0 | visible drop 0.0872m and no fall, but contact 0.85, final height 0.7034m, foot slip 1.267m |
| strict-mid | DEPTH_PENDING | local Windows CPU JAX/MuJoCo 6s | 0 | no fall, but visible drop 0.0555m, contact 0.88, final height 0.7366m |

| Variant | Max blend | Rate cap | Drop | Fell at | Contact | Final height | Foot slip | Verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| conservative | 0.65 | 0.035m/s | 1.5283m | 4.80s | 0.73 | -0.7430m | 2.220m | FAIL_FALL |
| medium | 0.85 | 0.055m/s | 1.5272m | 2.66s | 0.82 | -0.7415m | 0.791m | FAIL_FALL |
| assertive | 1.00 | 0.075m/s | 1.5392m | 2.44s | 0.83 | -0.7530m | 0.850m | FAIL_FALL |
| strict-low | 0.45 | 0.020m/s | 0.0872m | never | 0.85 | 0.7034m | 1.267m | RETURN_PENDING |
| strict-mid | 0.55 | 0.025m/s | 0.0555m | never | 0.88 | 0.7366m | 1.304m | DEPTH_PENDING |

### 박제 위치
- `verify/attempts/*/guarded-native-eval.json`
- `verify/guarded-descent-summary.md`
- `verify/guarded-descent-trajectory-*.json`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- Web research supports continuing the squat attempt: G1 hardware/model is not the blocker, and external G1 work demonstrates deep-squat-like balance tasks.
- exp30's failure mode was reproduced: bigger reference blend can reach visible depth, but it falls without stance control.
- Guarded descent improved the tradeoff but did not close M19. `strict-low` reached the 8cm visible-depth threshold and did not fall, but it lost the stance/contact/return gates.
- The first failure signal is foot slip/contact loss, not joint limit violation. Guarding the blend after slip is too late because the stabilizer cannot recover once the feet have drifted.
- The next M19 work should not be another reward-scale-only loop or a stronger blend. It should add stance anchoring / foot placement control, then test return-to-stand from the deepest stable point.

### 가설은 통과했나?
- [ ] PASS — guarded descent closes visible squat.
- [x] FAIL — guarded descent found a no-fall visible-depth candidate, but it failed contact and return gates, so M19 remains open.

### 정의에 반영
- M19 remains pending. Completion still requires visible depth, no-fall, contact, return, and browser replay gates together.
- A numeric visible drop alone is insufficient if the robot slides away from its initial stance.

### 다음 실험 후보
- `g1-stance-anchored-squat-controller`: keep foot XY within a tight support window while descending, then only ramp down the squat target after stance is stable.
