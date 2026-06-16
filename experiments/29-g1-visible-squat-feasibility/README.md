# 29-g1-visible-squat-feasibility — G1 visible squat feasibility gate

> M19 correction. exp28 closed a weak numeric stage gate, but the browser replay is visually a micro-dip. This experiment resets the next target to a visible squat gate before more PPO or browser publishing.

## 1. 가설 (Hypothesis)

Unitree G1 hardware/model is a reasonable candidate for a squat-like lower-body transition, but the current `g1-controlled-squat` artifact is not a visible squat; a visible squat must first pass an explicit kinematic and replay-audit gate.

반증 기준:
- current replay already has >=8cm pelvis drop and meaningful knee/hip flexion.
- local G1 MJCF lower-body joint ranges cannot contain a candidate visible squat target.
- source/license provenance is too unclear to keep using the model in a public portfolio demo.

## 2. 방법 (Method)

planning_gate:
  team_validation_mode: manual-pass
  spec_delta: "M19 is downgraded from controlled squat PASS to micro-dip/balance probe; next M19 work is a visible squat feasibility gate."
  perspectives:
    product: "사용자가 눈으로 봤을 때 스쿼트라고 납득해야 showable skill이다."
    architecture: "웹 replay, native controller, behavior spec을 같은 measurable gate로 묶는다."
    security: "secret 없음. 단, 모델 출처/라이선스 attribution은 public demo risk로 별도 점검한다."
    qa: "audit script가 current replay와 local MJCF joint limits를 수치로 판정한다."
    skeptic: "joint range가 가능해도 동역학/토크/접촉 안정성은 아직 증명되지 않았다."
  dod:
    - "current replay visible squat gate FAIL을 수치로 박제한다."
    - "local G1 lower-body joint range와 candidate target margin을 JSON/MD로 박제한다."
    - "ROADMAP and web copy no longer call exp28 a visible squat success."

### 외부 근거
- Unitree official G1 page, accessed 2026-06-16: G1/G1 EDU list 23 to 43 joint motors, knee range 0~165 degrees, and knee torque 90/120 N.m depending on configuration. URL: https://www.unitree.com/g1/
- MuJoCo Menagerie, accessed 2026-06-16: Menagerie is a curated MuJoCo model library; each model directory has its own `LICENSE`, and model XML/assets are subject to model-specific license terms. URL: https://github.com/google-deepmind/mujoco_menagerie
- MuJoCo Playground paper, accessed 2026-06-16: published G1 result is joystick-based humanoid locomotion, not a demonstrated squat skill. URL: https://arxiv.org/html/2502.08844v1
- Unitree mujoco, accessed 2026-06-16: official Unitree simulator integrates Unitree SDK2/ROS2/Python control programs with MuJoCo for simulation-to-physical development. URL: https://github.com/unitreerobotics/unitree_mujoco

### 측정 metric
- visible replay gate:
  - pelvis/base drop >= 0.08m
  - max knee flexion delta >= 0.60rad
  - max hip pitch delta >= 0.35rad
- static target probe:
  - candidate visible squat target stays inside lower-body MJCF joint limits
  - result is only kinematic plausibility, not dynamic success

## 3. 결과 (Results)

### 데이터
| Run | Verdict | Cost | Retries | 비고 |
|-----|---------|------|---------|------|
| replay-audit | FAIL_VISIBLE_SQUAT_MICRO_DIP | local Python | 0 | exp28 web trajectory drops only about 1cm |
| static-target-probe | KINEMATICALLY_PLAUSIBLE_UNPROVEN_DYNAMICALLY | local XML/JSON parse | 0 | proposed hip/knee/ankle target is inside local MJCF limits |

### 박제 위치
- `verify/visible-squat-feasibility.json`
- `verify/visible-squat-feasibility.md`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- exp28 is useful as a balance/controller micro-dip artifact, not as a visible squat skill.
- The current G1 model is still worth using for the next squat experiment: local lower-body joint limits can contain a deeper visible target, and Unitree's public specs do not rule out squat-like leg flexion.
- The strongest already-proven G1 learning baseline remains joystick locomotion. Squat must be proven by our own controller/RL evidence.
- The immediate next task is not "more reward scaling"; it is a deeper foot-anchored reference target plus native MuJoCo controller probe with the visible gate above.

### 가설은 통과했나?
- [x] PASS — current replay failed visible-squat criteria, while local joint-limit audit says a deeper target is plausible enough to try.

### 정의에 반영
- M19 must be judged by visible squat criteria, not a threshold that only produces a 1cm height change.
- Browser labels must say `micro-dip` or `balance probe` until a replay passes the visible gate.

### 다음 실험 후보
- `g1-visible-squat-controller`: generate a foot-anchored target with >=8cm pelvis drop, run native controller sweep, and publish only if visual + native gates pass.
