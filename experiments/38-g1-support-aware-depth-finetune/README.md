# 38-g1-support-aware-depth-finetune — G1 support-aware depth finetune

## 1. 가설 (Hypothesis)

exp37에서 support breach가 fall보다 먼저 나타났으므로, staged depth finetune reward에 CoM support margin과 vertical velocity damping을 넣으면 exp22/25의 standing attractor보다 native depth가 개선된다.

## 2. 방법 (Method)

### 셋업
- 모델: local MuJoCo Playground G1 runtime (`C:\tmp\e34`).
- 데이터: exp22 stabilizer/depth params, exp25 staged curriculum runner.
- 하네스 구성: learning experiment 4-section README + raw evidence in `verify/`.

### 근거
- Learning-based humanoid WBC work uses ZMP/support-polygon ideas as stability constraints. URL: https://arxiv.org/html/2502.17219v1 (accessed 2026-06-18)
- Squat WBC work frames squat as a whole-body task with torso, feet, foot force, and dynamic constraints. URL: https://pmc.ncbi.nlm.nih.gov/articles/PMC11769464/ (accessed 2026-06-18)
- Task-based WBC squat-like motion combines CoM, relative feet pose, ZMP stabilizer, and joint-limit avoidance. URL: https://www.lirmm.fr/krut/pdf/2014_galdeano_ssd-0568454426/2014_galdeano_ssd.pdf (accessed 2026-06-18)

### 시나리오
- S1: support-aware env compatibility with exp22 source params.
- S2: zero-action rollout smoke confirms support/depth metrics are wired.
- S3: short 50k restored PPO fine-tune.
- S4: native MuJoCo diagnostic against M19 stage/depth/contact/return metrics.

### 측정 metric
- `min_height`, `visible_drop`
- `fell_at`, `foot_contact_ratio`, `foot_slip_distance`, `return_to_stand`
- `min_support_margin`, `max_downward_velocity`

## 3. 결과 (Results)

### 데이터
| Run | Verdict | Train | Drop | Fell at | Support min | 비고 |
|-----|---------|-------|------|---------|-------------|------|
| S1 compatibility | PASS | - | - | - | - | exp22 source params match target policy shape |
| S2 rollout smoke | PASS | - | - | none | 0.0164m | support/vertical metrics wired, zero rollout no termination |
| S3 50k finetune | PASS | 5.26min | - | - | - | eval reward 138.944 -> 142.595 |
| S4 native diagnostic | `DEPTH_PENDING` | 50k | 0.0062m | never | 0.0730m | contact 1.00, slip 0.025m, but visible gate requires >=0.08m |

### 박제 위치
- Summary: `verify/stage-0p74/support-aware-summary.md`
- Raw result: `verify/stage-0p74/g1-support-aware-depth-finetune.json`
- Train rewards: `verify/stage-0p74/train/rewards.txt`
- Params: `verify/stage-0p74/train/params.pkl`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- Support-aware reward is wired and trainable in the current Windows/JAX runtime after a small Brax/JAX compatibility shim plus `OPENBLAS_NUM_THREADS=1`.
- The 50k finetune improved eval reward and kept native stability: no fall, foot contact 1.00, support margin 0.0730m, slip 0.025m.
- It did not break the standing attractor. Native visible drop moved only from the exp22/25 0.49cm range to 0.62cm, far below the exp29 8cm visible gate.

### 가설은 통과했나?
- [ ] PASS
- [x] FAIL — support/vertical rewards alone did not produce staged squat depth in native rollout.

### 정의에 반영
- M19 ROADMAP에 support-aware finetune result를 반영한다.

### 다음 실험 후보
- Action/target architecture change: give the policy an explicit residual target toward IK/reference pose instead of hoping reward alone overcomes the stabilizer.
- Longer finetune only after action target leverage is changed; current reward-only path is low-yield.
