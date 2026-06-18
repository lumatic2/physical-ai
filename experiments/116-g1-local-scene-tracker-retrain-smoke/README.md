# 116-g1-local-scene-tracker-retrain-smoke — G1 local-scene tracker retrain smoke

## 1. 가설 (Hypothesis)

Exp115가 public upstream scene parity를 막았으므로, local `scene_g1_policy.xml` 기준 future-reference tracker를 짧게 restored PPO retrain하면 source baseline보다 exp29 visible gate에 가까워질 수 있다.

## 2. 방법 (Method)

### 셋업
- 모델: local MuJoCo G1 scene via exp111 `ContactAwareReferenceSquat`.
- 초기 checkpoint: exp105 future-reference tracker params.
- 실행: source no-train baseline과 short local retrain을 같은 native exp29 gate로 비교한다.
- 판정: native gate가 통과할 때만 browser replay를 시도한다.

### 웹 근거
- General Motion Retargeting은 foot sliding, self-penetration, infeasible motion artifact가 downstream RL tracking을 해친다고 설명한다. 접근일: 2026-06-18. https://arxiv.org/html/2510.02252v1
- Whole-body humanoid locomotion work는 Unitree G1에서 generated/reference motion과 RL-based tracking을 결합한다. 접근일: 2026-06-18. https://arxiv.org/html/2604.17335v1
- Humanoid squat TP-MPC/WBC 연구는 squat를 CoM/ZMP/foot-force/whole-body coordination 문제로 다룬다. 접근일: 2026-06-18. https://pmc.ncbi.nlm.nih.gov/articles/PMC11769464/
- Strict contact-force tracking은 floating-base humanoid motion tracking에서 contact force constraints가 핵심이라고 설명한다. 접근일: 2026-06-18. https://la.disneyresearch.com/wp-content/uploads/PROJECT_Humanoids-mocap_IEEE-RAS-ICHR-2013_PAPER1.pdf

### 시나리오
- `source-exp105-no-train`: exp105 source checkpoint를 retrain 없이 native gate 평가.
- `short-local-retrain-contact-tight`: contact/slip/action prior를 강화한 local scene restored PPO short retrain 후 native gate 평가.

### 측정 metric
- exp29 visible native gate: no fall, pelvis drop >=8cm, knee >=0.60rad, hip >=0.35rad, return, contact >=0.90, slip <=0.08m.
- browser replay attempted flag.

## 3. 결과 (Results)

### 데이터
| Run | Verdict | Drop | Knee | Hip | Contact | Slip | Final h | Fall |
|---|---|---:|---:|---:|---:|---:|---:|---|
| source-exp105-no-train | DEPTH_PENDING_7CM | 0.0200m | 0.480 | 0.345 | 0.39 | 3.305m | 0.7592m | never |
| short-local-retrain-contact-tight | DEPTH_PENDING_7CM | 0.0207m | 0.484 | 0.339 | 0.42 | 3.219m | 0.7379m | never |

Verdict: `FAIL_LOCAL_TRACKER_RETRAIN_SMOKE`.
Best run: `short-local-retrain-contact-tight` with drop `0.0207m`, knee `0.484`, hip `0.339`.

### 박제 위치
- `verify/result.json`
- `verify/local-scene-tracker-retrain-summary.md`
- `verify/<run>/native-eval.json`
- `verify/<run>/train/params.pkl` for trained variants

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- Local-scene tracker retrain smoke는 M19 native visible gate를 닫지 못했다.
- Source baseline과 short retrain을 같은 gate로 비교해, shallow attractor를 단기 PPO로 벗어나는지 확인했다.
- native gate가 PASS하지 않았으므로 browser replay는 시도하지 않았다.

### 가설은 통과했나?
- [ ] PASS — native exp29 visible gate를 통과했다.
- [x] FAIL — short local-scene tracker retrain만으로 native visible gate를 닫지 못했다.

### 정의에 반영
- M19 완료 기준은 유지한다. native visible gate와 browser replay가 모두 필요하다.

### 다음 실험 후보
- full-order ID-QP/MPC: exp109 static target을 contact force/floating-base dynamics decision variable과 함께 추종한다.
- longer local motion-tracking training: short retrain이 아닌 longer tracker training으로 shallow attractor 탈출 여부를 별도 검증한다.
