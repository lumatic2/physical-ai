# 41-g1-operational-space-soft-wbc — G1 operational-space soft WBC probe

## 1. 가설 (Hypothesis)

exp36/37의 visible-depth fall은 IK target 자체보다 depth command가 support margin과 vertical momentum을 무시하고 계속 들어가기 때문일 수 있다. hard guard가 아니라 support/velocity/contact cost로 IK blend를 연속적으로 줄이면, shallow micro-dip과 visible collapse 사이에서 더 깊고 안정적인 corridor를 찾을 수 있다.

## 2. 방법 (Method)

### 셋업
- 모델: local MuJoCo Playground G1 runtime (`C:\tmp\e34`).
- 입력: exp36 foot-fixed IK 8cm target, exp37 CoM/support polygon metric, exp22/21 stabilizer policy.
- 하네스: learning experiment 4-section README + raw evidence in `verify/`.

### 근거
- Humanoid squat는 TP-MPC + WBC처럼 whole-body coordination 문제로 다뤄진다. URL: https://pmc.ncbi.nlm.nih.gov/articles/PMC11769464/ (accessed 2026-06-18)
- WBC/task-space 문헌은 CoM, foot relative pose, ZMP/support polygon, joint limit을 함께 제어 대상으로 둔다. URL: https://www.lirmm.fr/krut/pdf/2014_galdeano_ssd-0568454426/2014_galdeano_ssd.pdf (accessed 2026-06-18)
- fall prevention 쪽도 CoM projection/support polygon과 variable-height inverted pendulum을 사용한다. URL: https://pmc.ncbi.nlm.nih.gov/articles/PMC11048354/ (accessed 2026-06-18)
- MuJoCo는 inverse dynamics/contact force 계산 경로를 제공하므로 다음 단계에서 더 진짜 WBC/QP로 확장할 수 있다. URL: https://mujoco.readthedocs.io/en/stable/computation/index.html (accessed 2026-06-18)

### 시나리오
- `baseline`: fixed IK blend, 기존 exp36과 같은 실패면 재현.
- `soft-wbc`: desired blend에 support margin, downward velocity, contact cost를 곱해 연속적으로 완화한다.
- `soft-wbc-deeper`: 더 큰 blend에서 cost shaping이 visible fall을 늦추거나 막는지 본다.

### 측정 metric
- `visible_drop >= 0.08m`
- `fell_at is None`
- `final_height >= 0.74m`
- `foot_contact_ratio >= 0.90`
- `foot_slip_distance <= 0.15m`
- `min_support_margin`, `max_downward_velocity`, `blend_reduction`

## 3. 결과 (Results)

### 데이터
| Run | Verdict | Drop | Fell at | Support min | Contact | Slip | 비고 |
|-----|---------|------|---------|-------------|---------|------|------|
| fixed-0p25 | DEPTH_PENDING | 0.0224m | never | 0.0227m | 1.00 | 0.013m | exp36 shallow stable 재현 |
| fixed-0p35 | FAIL_FALL | 1.5072m | 4.02s | -0.6053m | 0.86 | 0.816m | fixed blend는 visible collapse |
| support-0p45 | DEPTH_PENDING | 0.0225m | never | 0.0284m | 1.00 | 0.013m | support cost가 blend를 0.25 수준으로 제한 |
| support-velocity-0p45 | DEPTH_PENDING | 0.0225m | never | 0.0284m | 1.00 | 0.013m | velocity cost 추가 효과는 작음 |
| support-velocity-0p60 | DEPTH_PENDING | 0.0256m | never | 0.0179m | 1.00 | 0.015m | 가장 깊은 no-fall corridor |
| support-velocity-0p80 | FAIL_FALL | 1.5029m | 4.66s | -0.5714m | 0.84 | 0.912m | cost shaping도 high blend collapse는 못 막음 |
| support-velocity-1p00 | FAIL_FALL | 1.5074m | 3.88s | -0.5722m | 0.81 | 0.895m | 더 빠른 collapse |

### 박제 위치
- `verify/soft-wbc-summary.md`
- `verify/attempts/*/soft-wbc-native-eval.json`
- `verify/attempts/*/result.json`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- Soft operational-space proxy는 fixed blend보다 안정 corridor를 넓힌다. `support-velocity-0p60`은 fall/contact/slip을 유지하면서 drop을 `2.56cm`까지 키웠다.
- 하지만 visible squat gate인 `8cm`에는 아직 부족하다. support/velocity/contact cost가 blend를 약 `0.28~0.32`에서 포화시키며, 그 이상으로 밀면 support breach와 slip이 커져 collapse한다.
- fixed 0.35는 `4.02s` fall, support-velocity 0.80은 `4.66s` fall로 collapse를 늦추기는 했지만 막지는 못했다.
- 다음 단계는 soft blend scale을 조절하는 heuristic이 아니라, foot pose equality, pelvis height, CoM/ZMP, vertical momentum을 동시에 푸는 inverse dynamics/QP 또는 MPC+WBC 형태가 필요하다.

### 가설은 통과했나?
- [ ] PASS
- [x] FAIL

### 정의에 반영
- M19 ROADMAP 상태에 반영한다. soft WBC proxy는 shallow corridor를 넓혔지만 native visible gate는 실패했다.

### 다음 실험 후보
- MuJoCo inverse dynamics/contact force를 읽어 stance/contact force evidence를 추가한다.
- QP-lite: pelvis-height acceleration objective + foot pose equality + CoM support inequality + joint damping을 풀어 motor target 또는 qacc target으로 변환한다.
- native visible gate가 통과할 때까지 browser replay는 만들지 않는다.
