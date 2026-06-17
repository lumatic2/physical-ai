# 36-g1-wbc-ik-squat-prototype — G1 foot-fixed IK squat probe

## 1. 가설 (Hypothesis)

G1의 visible squat 실패가 단순 시간 블렌드 문제가 아니라 발 위치/지지다각형 제약 누락 때문이라면, 발을 고정한 IK target을 먼저 만들 때 기존 reference blend보다 foot slip/contact가 개선된다.

## 2. 방법 (Method)

### 셋업
- 모델: local MuJoCo Playground G1 runtime (`C:\tmp\e34`).
- 데이터: exp28/34/35의 G1 native model, walking stabilizer policy, `knees_bent` keyframe.
- 하네스 구성: learning experiment 4-section README + raw evidence in `verify/`.

### 근거
- Unitree G1-Comp는 knee range `0~165deg`, knee torque `120 N.m`, thigh+calf `0.6m`를 공개해 깊은 무릎 굴곡 자체는 기구적으로 가능한 후보임을 보인다. URL: https://www.unitree.com/robocup/ (accessed 2026-06-18)
- HuB는 Unitree G1에서 `Deep Squat`을 extreme balance task 예시로 공개했다. URL: https://hub-robot.github.io/ (accessed 2026-06-18)
- ZMP/whole-body control 문헌은 humanoid balance에서 ZMP가 foot-ground support polygon 안에 있어야 하며, squat는 torso/feet/contact force/joint constraint를 동시에 다뤄야 한다고 설명한다. URLs: https://arxiv.org/html/2502.17219v1, https://www.mdpi.com/1424-8220/25/2/435 (accessed 2026-06-18)
- Task-based WBC 문헌은 foot relative pose를 높은 우선순위로 두고 CoM/ZMP/joint limit을 함께 제어한다. URL: https://www.lirmm.fr/krut/pdf/2014_galdeano_ssd-0568454426/2014_galdeano_ssd.pdf (accessed 2026-06-18)

### 시나리오
- V0: static IK feasibility. root height를 낮추면서 양발 site position을 초기 위치에 유지하는 lower-body target을 least-squares로 찾는다.
- V1: native PD/policy blend rollout. IK target을 descend/hold/return schedule로 추적하고 visible depth, fall, foot contact, foot slip, return height를 측정한다.

### 측정 metric
- `ik_rms_foot_error`, `ik_max_foot_error`
- `visible_drop >= 0.08m`
- `fell_at is None`
- `foot_contact_ratio >= 0.90`
- `foot_slip_distance <= 0.15m`
- `final_height >= 0.74m`

## 3. 결과 (Results)

### 데이터
| Run | Verdict | Drop | Fell at | Contact | Slip | 비고 |
|-----|---------|------|---------|---------|------|------|
| `ik-drop-0p08-blend-0p25` | `DEPTH_PENDING` | 0.0224m | never | 1.00 | 0.013m | stable but micro-dip |
| `ik-drop-0p08-blend-0p35` | `FAIL_FALL` | 1.5072m | 4.02s | 0.86 | 0.816m | visible depth then collapse |
| `ik-drop-0p06-blend-0p55` | `FAIL_FALL` | 1.5202m | 3.00s | 0.90 | 0.774m | over-descends |
| `ik-drop-0p08-blend-0p55` | `FAIL_FALL` | 1.5142m | 2.94s | 0.90 | 0.701m | over-descends |
| `ik-drop-0p08-blend-0p75` | `FAIL_FALL` | 1.5179m | 2.50s | 0.92 | 0.707m | higher blend fails earlier |
| `ik-drop-0p08-no-policy` | `FAIL_FALL` | 1.5298m | 1.26s | 0.91 | 0.975m | pure IK/PD is worst |

Static IK feasibility passed: 6cm/8cm target solves reached `0.0005m` to `0.0006m` max foot-site error. Native rollout gate failed: low blend keeps stance/contact but only produces 2.2cm drop, while deeper blends cross visible depth and then collapse below the floor frame.

### 박제 위치
- Summary: `verify/ik-squat-summary.md`
- Raw attempts: `verify/attempts/*/result.json`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- 이 로봇/모델에서 스쿼트 geometry 자체는 가능하다. 8cm pelvis drop target이 양발 site error 0.7mm 미만으로 풀린다.
- 지금까지의 position blend 실패 원인은 target pose 부족이 아니라 제어 방식이다. CoM/ZMP, vertical momentum, ground reaction force를 닫지 않으면 발이 거의 고정돼 보여도 pelvis가 목표를 지나쳐 무너진다.
- learned stabilizer residual은 여전히 필요하다. `no-policy` variant는 1.26s fall로 가장 빨리 실패했다.

### 가설은 통과했나?
- [ ] PASS
- [x] FAIL — foot-fixed IK target만으로 native contact/return gate를 닫지 못했다. shallow blend는 micro-dip, visible blend는 fall이다.

### 정의에 반영
- M19 ROADMAP에 `WBC/IK prototype exhausted`와 다음 방향을 반영한다.

### 다음 실험 후보
- CoM projection/support polygon reward를 넣은 stance-aware finetune.
- Torque-level or operational-space WBC prototype: pelvis height target + foot pose equality + CoM/support constraint + damping/vertical velocity limit.
