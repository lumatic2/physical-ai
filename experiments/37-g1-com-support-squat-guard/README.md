# 37-g1-com-support-squat-guard — G1 CoM/support squat guard

## 1. 가설 (Hypothesis)

exp36 visible-depth IK rollout이 foot target 부족이 아니라 balance constraint 부족으로 무너진다면, CoM projection/support polygon margin과 vertical velocity를 native rollout에 넣었을 때 fall 이전의 조기 실패 신호가 잡히고 guard가 collapse를 늦추거나 shallow-safe로 되돌린다.

## 2. 방법 (Method)

### 셋업
- 모델: local MuJoCo Playground G1 runtime (`C:\tmp\e34`).
- 데이터: exp36 foot-fixed IK target generator, exp22 walking stabilizer policy.
- 하네스 구성: learning experiment 4-section README + raw evidence in `verify/`.

### 근거
- Humanoid WBC/ZMP 문헌은 ZMP가 support polygon 안에 있어야 동적 균형 조건이 된다고 설명한다. URL: https://arxiv.org/html/2502.17219v1 (accessed 2026-06-18)
- Squat motion WBC 논문은 squat가 torso, arms/feet, foot force, dynamic constraints를 동시에 다루는 whole-body task라고 설명한다. URL: https://pmc.ncbi.nlm.nih.gov/articles/PMC11769464/ (accessed 2026-06-18)
- Task-based WBC squat-like motion은 CoM, relative feet pose, ZMP stabilizer, joint-limit avoidance를 함께 제어 대상으로 둔다. URL: https://www.lirmm.fr/krut/pdf/2014_galdeano_ssd-0568454426/2014_galdeano_ssd.pdf (accessed 2026-06-18)

### 시나리오
- V0: exp36 baseline과 같은 IK blend를 support metric으로 재계측한다.
- V1: support margin 또는 downward velocity가 위험하면 blend를 낮추고 return으로 전환하는 guard를 비교한다.

### 측정 metric
- `min_support_margin`: whole-body CoM projection이 양발 foot geom support bbox 안에 남는 최소 여유.
- `first_support_breach_at`, `first_fast_drop_at`, `fell_at`.
- M19 native gate: visible drop, no-fall, contact, stance, return.

## 3. 결과 (Results)

### 데이터
| Run | Verdict | Drop | Fell at | Support min | First breach | Slip | 비고 |
|-----|---------|------|---------|-------------|--------------|------|------|
| `baseline-0p25` | `DEPTH_PENDING` | 0.0224m | never | 0.0227m | never | 0.013m | stable micro-dip |
| `baseline-0p35` | `FAIL_FALL` | 1.5072m | 4.02s | -0.6053m | 3.10s | 0.816m | support breach precedes visible/fall |
| `support-guard-0p35` | `FAIL_FALL` | 1.5194m | 4.06s | -0.6031m | 3.10s | 0.837m | guard at 2.90s, no recovery |
| `support-guard-0p45` | `FAIL_FALL` | 1.5110m | 3.46s | -0.6082m | 2.60s | 0.806m | guard at 2.44s, still falls |
| `velocity-guard-0p45` | `FAIL_FALL` | 1.5132m | 3.44s | -0.6128m | 2.60s | 0.807m | velocity guard also too late/weak |

Baseline `0p35` crossed visible depth at 3.74s, support breach appeared at 3.10s, fast downward velocity at 3.80s, and fall at 4.02s. The support signal is therefore useful as an early failure metric, but a post-hoc blend reduction is not a controller.

### 박제 위치
- Summary: `verify/support-guard-summary.md`
- Raw attempts: `verify/attempts/*/result.json`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- CoM/support margin is a real leading indicator in this setup: baseline visible fall breaches support about 0.64s before visible depth and 0.92s before fall.
- Heuristic return guards do not solve M19. Once the state approaches visible depth, the system needs continuous balance authority, not a late reduction of IK blend.
- The next reward/WBC target should penalize support margin breach and downward velocity before visible depth, while preserving learned stabilizer residual.

### 가설은 통과했나?
- [ ] PASS
- [x] FAIL — guard did not improve the M19 gate. It did confirm support margin as a useful training/control signal.

### 정의에 반영
- M19 ROADMAP에 support-margin diagnostic과 heuristic guard failure를 반영한다.

### 다음 실험 후보
- Stance-aware finetune with support-margin, vertical-velocity, and return-height rewards.
- Torque/operational-space WBC where pelvis-height target is constrained by foot pose, CoM support margin, and vertical damping.
