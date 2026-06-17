# 61-g1-contact-wbc-selector-probe — Contact-aware WBC selector probe

## 1. 가설 (Hypothesis)

exp60의 5.73cm 안정 경계는 residual scale 자체가 아니라 stance foot/contact constraint를 target 선택 전에 보지 못해서 생긴다. 한 스텝 MuJoCo rollout으로 support, ZMP, slip, contact wrench, inverse torque를 비용화하면 8cm visible squat 쪽으로 안정 corridor가 넓어질 수 있다.

외부 근거는 이 방향을 지지한다. humanoid squat 전용 연구는 TP-MPC로 trajectory를 다듬고 WBC로 추종하면 WBC 단독보다 tracking과 knee torque spike가 개선된다고 보고한다. 접근일: 2026-06-18. <https://www.mdpi.com/1424-8220/25/2/435>

또 다른 WBC/MPC 연구는 ZMP constraint만으로는 접촉 충격과 수직 contact force를 충분히 제어하지 못하므로 z-directional contact force constraint를 추가한다고 설명한다. 접근일: 2026-06-18. <https://arxiv.org/html/2505.19540v1>

task-based humanoid WBC 연구도 foot relative pose를 highest priority task로 두고, CoM tracking에 ZMP regulation을 넣어 squat-like motion을 만든다. 접근일: 2026-06-18. <https://www.lirmm.fr/krut/pdf/2014_galdeano_ssd-0568454426/2014_galdeano_ssd.pdf>

## 2. 방법 (Method)

### 셋업
- 모델: local Unitree G1 MuJoCo policy sandbox.
- 시작점: exp60 `safe_combo` residual과 exp42 contact/inverse-force diagnostics.
- 실행: `run_contact_wbc_selector_probe.py`.
- raw evidence: `verify/contact-wbc-selector/`.

### selector
- 매 control step마다 blend 후보와 residual scale 후보를 만든다.
- 각 후보를 clone된 MuJoCo state에서 한 스텝 rollout한다.
- 비용에는 height/pose target, support margin, ZMP margin, foot slip, both-feet contact, left/right normal force imbalance, normal force excess, inverse torque gap, uprightness, smoothness를 넣는다.
- pass gate는 기존 M19 native gate를 유지한다: pelvis drop >=8cm, knee >=0.60rad, hip >=0.35rad, no-fall, return, contact, slip, joint limit.

### variants
- `stance-ultra-0p08-r0p06`: stance/ZMP/contact/slip을 매우 강하게 둔다.
- `stance-strict-0p08-r0p08`: exp60 stable residual 근처에서 contact-aware selection을 적용한다.
- `pose-balanced-0p08-r0p09`: pose/depth와 stance를 균형시킨다.
- `pose-push-0p08-r0p10`: pose/depth를 더 강하게 민다.
- `pose-balanced-0p10-r0p09`: 10cm target으로 확장한다.

## 3. 결과 (Results)

### 데이터
| Run | Verdict | Drop | Knee | Hip | Contact | Slip | Support/ZMP min | 비고 |
|---|---|---:|---:|---:|---:|---:|---:|---|
| stance-ultra-0p08-r0p06 | DEPTH_PENDING | 0.0082m | 0.104 | 0.022 | 1.00 | 0.015m | 0.0795 / 0.0525m | 안전하지만 micro-dip으로 후퇴 |
| stance-strict-0p08-r0p08 | FAIL_FALL | 1.5107m | 0.575 | 0.344 | 0.88 | 0.930m | -0.5697 / -0.5716m | pose gate 근처에서 collapse |
| pose-balanced-0p08-r0p09 | FAIL_FALL | 1.5117m | 0.576 | 0.343 | 0.88 | 0.943m | -0.5697 / -0.5708m | 동일 collapse |
| pose-push-0p08-r0p10 | FAIL_FALL | 1.5180m | 0.615 | 0.390 | 0.86 | 0.820m | -0.5723 / -0.5729m | pose gate는 닿지만 fall |
| pose-balanced-0p10-r0p09 | FAIL_FALL | 1.5099m | 0.699 | 0.470 | 0.84 | 0.890m | -0.6058 / -0.6053m | 10cm target은 더 빨리 collapse |

### 박제 위치
- Summary: `verify/contact-wbc-selector/contact-wbc-selector-summary.md`
- Aggregate JSON: `verify/contact-wbc-selector/result.json`
- Per-run JSON: `verify/contact-wbc-selector/*/native-eval.json`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- contact-aware one-step selector는 safety를 강하게 두면 안전해지지만, 그 대가는 0.8cm micro-dip이다. exp60의 5.73cm보다도 얕다.
- pose/depth를 비용에 넣으면 knee/hip visible pose gate에는 접근한다. 그러나 support/ZMP margin이 -0.57m 수준으로 무너지고 fall한다.
- 따라서 M19 병목은 “더 똑똑한 position target selector”보다 아래에 있다. 실제 torque/contact-aware WBC, contact force distribution, stance foot acceleration constraint, 또는 dynamics-level optimizer가 필요하다.

### 가설은 통과했나?
- [ ] PASS
- [x] FAIL — one-step contact-aware target selection만으로는 stable corridor를 8cm로 넓히지 못했고, exp60의 5.73cm 안정 경계도 보존하지 못했다.

### 정의에 반영
- ROADMAP M19에 exp61을 추가하고, 다음 작업을 target selector가 아니라 dynamics-level torque/contact WBC prototype으로 좁힌다.

### 다음 실험 후보
- exp62: position target 후보 선택을 중단하고, stance foot acceleration/contact wrench equality를 둔 작은 QP 또는 MuJoCo actuator-space torque feasibility probe로 내려간다.
