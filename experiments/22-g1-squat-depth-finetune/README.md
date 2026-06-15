# 22-g1-squat-depth-finetune — G1 squat depth from stabilizer

> M19f. exp21에서 walking stabilizer init이 native 6초 no-fall을 처음 달성한 뒤, 안정성을 유지하면서 실제 base height를 squat reference 쪽으로 낮출 수 있는지 확인한다.

## 1. 가설 (Hypothesis)

exp21은 안정성은 해결했지만 base height가 0.752m 이상으로 유지되어 squat depth가 부족했다. exp21 params를 출발점으로 삼고 height/reference reward를 강하게 조정하면, native no-fall을 유지하면서 min base height를 0.70m 아래로 낮출 수 있다.

반증 기준:
- exp21 params와 depth fine-tune network shape가 맞지 않는다.
- fine-tune이 실행되지 않는다.
- native diagnostic에서 fall하거나, no-fall이어도 min height가 0.70m 이상에 머문다.

## 2. 방법 (Method)

### 셋업
- source params: `experiments/21-g1-stabilizer-init-probe/verify/train/params.pkl`.
- 기반: exp20 reference trajectory + exp21 same-shape restored PPO loop.
- 변경: height tracking/depth progress reward 강화, height floor는 완화.

### 시나리오
- S1: depth env rollout smoke.
- S2: exp21 params restore fine-tune.
- S3: native MuJoCo diagnostic.

### 측정 metric
- native fall time
- min/final base height
- max height error
- max reference error
- joint limit violation

## 3. 결과 (Results)

### 데이터
| Run | Verdict | Cost | Retries | 비고 |
|-----|---------|------|---------|------|
| S1 depth env rollout smoke | PASS | local WSL/JAX | 0 | 20-step no termination, height min 0.722 |
| S2 restored depth fine-tune | PASS | 150k target / 163840 eval steps / 5.46min | 0 | eval reward 80.491 -> 83.340 |
| S3 native diagnostic | IMPROVED_DEPTH_PENDING | 6.0s native MuJoCo | 0 | no-fall, min height 0.7523 -> 0.7501, target <0.70 not reached |

### 박제 위치
- `verify/g1-squat-depth-finetune.json`
- `verify/train-native.log`
- `verify/train/rewards.txt`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- exp21 stabilizer를 유지한 depth fine-tune은 no-fall을 유지했다. native 6초 diagnostic에서 fall은 없고 joint limit violation도 0이다.
- height/reference reward를 강하게 올려도 base height는 0.7523m에서 0.7501m로 아주 조금만 내려갔다. 목표인 0.70m 아래에는 도달하지 못했다.
- 즉 stabilizer prior가 안정성은 주지만, 현재 reward만으로는 squat depth를 충분히 만들지 못한다. 다음은 reward scale 반복이 아니라 curriculum 또는 target/action 구조 재설계가 필요하다.

### 가설은 통과했나?
- [ ] PASS — no-fall을 유지하며 min height가 0.70m 아래로 내려갔다.
- [x] FAIL — 안정성은 유지했지만 squat depth가 실패했다.

### 정의에 반영
- `ROADMAP.md` M19를 "depth 개선 미미 / curriculum 필요"로 갱신한다. native no-fall은 유지됐지만 아직 showable squat skill은 아니다.

### 다음 실험 후보
- squat depth curriculum: target min height를 0.74 -> 0.70 -> 0.66 -> 0.62로 단계적으로 낮춘다.
- action/pose target 구조 점검: reference joint targets가 실제 base height drop을 충분히 만들 수 있는지 native scripted closed-loop에서 확인한다.
- height drop이 native에서 확인된 뒤 ONNX/browser playback으로 넘어간다.
