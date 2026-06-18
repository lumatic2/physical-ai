# 123-g1-reference-vs-rollout-viewer — M22 browser comparison gate

> M22. Compiled reference motion and measured rollout are both useful, but the public browser had no way to compare them frame-by-frame.

## 1. 가설 (Hypothesis)

G1 squat reference motion을 기존 web qpos trajectory contract로 변환하고, measured WBC rollout과 같은 브라우저 실험에서 비교할 수 있으면, M22의 남은 viewer gate를 닫을 수 있다.

반증 기준:
- compiled reference motion을 full G1 qpos trajectory로 변환하지 못한다.
- browser registry가 reference trajectory와 rollout trajectory를 함께 로드하지 못한다.
- QA hook이 frame count, height error, joint RMS error를 raw JSON으로 박제하지 못한다.

## 2. 방법 (Method)

### 셋업
- reference: `experiments/17-motion-to-policy-loop/verify/g1_squat_reference.compiled.json`
- rollout: `experiments/03-digital-twin/g1_decoupled_wbc_squat_trajectory.json`
- viewer: `experiments/03-digital-twin/web/src/main.js`

### 시나리오
- S1: reference samples를 50Hz full qpos trajectory로 변환한다.
- S2: `g1-squat-reference-vs-wbc` registry entry에 rollout + reference compare trajectory를 묶는다.
- S3: browser QA hook `qaCompare()`가 비교 metric을 반환하고 evidence JSON으로 저장한다.

### 측정 metric
- frame count
- max/mean pelvis height error
- max lower-body joint RMS error
- browser compare hook status

## 3. 결과 (Results)

### 데이터
| Run | Verdict | Cost | Retries | 비고 |
|-----|---------|------|---------|------|
| S1-S2 artifact build | PASS | local Python | 0 | reference qpos trajectory + registry entry |
| S3 browser compare QA | PASS | Playwright + local web | 0 | `qaCompare()` evidence |

### 박제 위치
- `verify/reference-vs-rollout-summary.json`
- `verify/browser-reference-vs-rollout.json`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- compiled reference motion은 web qpos trajectory contract로 변환 가능했다.
- measured WBC rollout과 reference target의 frame-level 비교는 browser 안에서 바로 계산된다.
- viewer gate는 새로운 physics engine이 아니라, 기존 replay contract에 compare trajectory와 QA hook을 추가하는 작은 확장으로 충분했다.

### 가설은 통과했나?
- [x] PASS — reference와 rollout을 브라우저에서 같은 계약으로 비교했다.
- [ ] FAIL — 무엇이 어긋났나, 가설 수정.

### 정의에 반영
- M22의 남은 viewer gate를 `reference vs rollout browser comparison`으로 닫는다.

### 다음 실험 후보
- M21 ball/kick learned external-object skill.
