# 118-g1-longer-local-tracker-training-gate — G1 longer local tracker training gate

## 1. 가설 (Hypothesis)

Exp116의 512-step local retrain은 source 대비 drop/contact가 거의 변하지 않았고, exp117의 qfrc-applied full-order formulation smoke는 1.40~1.46초 fall로 붕괴했다. 같은 local scene에서 restored PPO를 20k-step 수준으로 늘리면, shallow attractor를 벗어나 M19 native visible gate에 의미 있게 가까워질 수 있다.

## 2. 방법 (Method)

- 기반: exp111 `ContactAwareReferenceSquat`, exp105 future-reference tracker checkpoint, exp29 native visible gate.
- 비교: source no-train baseline vs longer local tracker retrain.
- 학습 variant: target_drop 9cm, lookahead 0.70s, anticipatory action mix 0.50, contact action scale 0.80, slip limit 5cm.
- 판정: native gate가 PASS할 때만 browser replay를 시도한다.

### 웹 근거

- HybridRobotics whole-body tracking stack은 retargeted generalized-coordinate reference motion과 training registry를 전제로 한다. 접근일: 2026-06-18. https://github.com/HybridRobotics/whole_body_tracking
- UniTracker는 Unitree G1 29-DoF에서 8,100개 이상 motion sequence tracking을 목표로 한 unified tracker 접근을 제시한다. 접근일: 2026-06-18. https://arxiv.org/html/2507.07356v3
- Whole-body humanoid locomotion on Unitree G1은 motion generation, tracker, fine-tuning 조합을 사용한다. 접근일: 2026-06-18. https://arxiv.org/html/2604.17335v1
- GR00T WholeBodyControl 문서는 Unitree G1 중심의 재사용 가능한 WBC/teleoperation/data exporter stack을 전제로 한다. 접근일: 2026-06-18. https://nvlabs.github.io/GR00T-WholeBodyControl/references/decoupled_wbc.html
- Humanoid squat TP-MPC/WBC 연구는 squat를 CoM/ZMP/foot force/whole-body coordination 문제로 다룬다. 접근일: 2026-06-18. https://pmc.ncbi.nlm.nih.gov/articles/PMC11769464/

## 3. 결과 (Results)

| Run | Verdict | Drop | Knee | Hip | Contact | Slip | Final h | Fall |
|---|---|---:|---:|---:|---:|---:|---:|---|
| source-exp105-no-train | DEPTH_PENDING_7CM | 0.0200m | 0.480 | 0.345 | 0.39 | 3.305m | 0.7592m | never |
| longer-local-tracker-contact-tight | DEPTH_PENDING_7CM | 0.0262m | 0.482 | 0.341 | 0.43 | 3.236m | 0.7288m | never |

Verdict: `FAIL_LONGER_LOCAL_TRACKER_TRAINING_GATE`.
Best run: `longer-local-tracker-contact-tight` with drop `0.0262m`, knee `0.482`, hip `0.341`.

Trained-vs-source delta:
- drop `0.0062m`
- knee `0.002rad`
- hip `-0.004rad`
- contact `0.043`
- slip `-0.069m`
- score `-50.5`

### 박제 위치
- `verify/result.json`
- `verify/longer-local-tracker-training-summary.md`
- `verify/<run>/native-eval.json`
- `verify/<trained-run>/train/params.pkl`
- `verify/<trained-run>/train/rewards.txt`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- Longer local tracker training gate verdict는 `FAIL_LONGER_LOCAL_TRACKER_TRAINING_GATE`이다.
- Browser replay attempted: `False`.
- 20k-step급 restored PPO가 native gate를 닫지 못하면, 같은 짧은 local tracker sweep을 반복하는 것은 M19 완료와 정렬이 약하다.
- 이 실험은 “장기 학습 전체”가 아니라 next-route gate다. 실패 시 다음은 실제 WBC stack 통합 또는 훨씬 긴 tracker training budget으로 가야 한다.

### 가설은 통과했나?
- [ ] PASS — native exp29 visible gate를 통과했다.
- [x] FAIL — longer local tracker training gate만으로 native visible gate를 닫지 못했다.

### 정의에 반영
- M19 완료 기준은 그대로 native exp29 visible gate + browser replay다.
