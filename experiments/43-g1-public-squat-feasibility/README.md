# 43-g1-public-squat-feasibility — G1 squat public feasibility refresh

## 1. 가설 (Hypothesis)

Unitree G1로 visible/deep squat가 가능한지 먼저 물리적으로 따져보면, 공개 하드웨어 근거와 로컬 MJCF 정적 후보는 가능성을 지지하지만 현재 M19 정책의 동적 성공은 별도 WBC/contact-force 문제로 남는다.

## 2. 방법 (Method)

### 셋업
- 모델: local MuJoCo G1 model via exp36/exp28 loader.
- 데이터: Unitree G1 공개 스펙, IEEE Robots Guide 공개 사진/스펙, HuB G1 extreme-balance 연구 페이지, local G1 MJCF.
- 하네스 구성: learning experiment 1개로 `verify/public-squat-feasibility.json`과 요약 markdown을 박제한다.

### 외부 근거
- Unitree G1-Comp 공식 페이지는 standing height `1320mm`, folded height `690mm`, single leg `6 DoF`, knee joint `0~165deg`, hip pitch `P±154deg`, knee maximum torque `120N.m`, thigh+calf length `0.6m`를 공개한다. URL: https://www.unitree.com/robocup/ (accessed 2026-06-18)
- IEEE Robots Guide의 Unitree G1 항목은 G1이 다리와 몸통이 거의 맞닿는 deep squat 자세를 취한 이미지를 싣고, height `130cm`, weight `35kg`, knee torque `90Nm`, EDU `120Nm`를 함께 정리한다. URL: https://robotsguide.com/robots/unitree-g1 (accessed 2026-06-18)
- HuB는 Unitree G1에서 extreme humanoid balance task를 검증했다고 밝히며 `Deep Squat`을 task 목록에 포함한다. URL: https://hub-robot.github.io/ (accessed 2026-06-18)

### 시나리오
- V0: 공개 evidence refresh. G1 하드웨어/공개 데모가 deep squat 가능성을 지지하는지 정리한다.
- V1: local static IK probe. foot-fixed pelvis drop `0.08m`, `0.12m`, `0.16m` target이 local MJCF에서 풀리는지 확인한다.
- V2: M19 decision. 정적 가능성과 동적 정책 성공을 분리해 다음 실험을 정한다.

### 측정 metric
- IK max foot error `<= 0.002m`
- visible pose gate: pelvis drop `>= 0.08m`, knee delta `>= 0.60rad`, hip pitch delta `>= 0.35rad`
- dynamic policy gate는 이번 실험의 완료 조건이 아니다. 기존 exp30-42 native 결과를 근거로 WBC 필요 여부만 판단한다.

## 3. 결과 (Results)

### 데이터
| Run | Verdict | 핵심 수치 | 비고 |
|-----|---------|----------|------|
| V0 | SUPPORTED | official knee `0~165deg`, knee torque `120N.m`, public deep squat evidence | G1-class hardware posture feasibility는 지지됨 |
| V1 | KINEMATICALLY_PLAUSIBLE | 0.12m drop: foot error `0.0007m`, knee delta `0.750rad`, hip pitch delta `0.359rad`; 0.16m drop: foot error `0.0008m`, knee delta `0.930rad`, hip pitch delta `0.444rad` | 0.08m는 pelvis drop만 통과하고 관절 delta gate는 부족했다. 0.12m 이상 target은 visible pose gate 통과 |
| V2 | WBC_REQUIRED | dynamic policy는 아직 unproven | exp30-42의 shallow/fall 결과와 합쳐 보면 다음은 QP-lite WBC가 맞다 |

### 박제 위치
- `verify/public-squat-feasibility.json`
- `verify/public-squat-feasibility.md`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- G1 하드웨어/공개 evidence는 deep squat 자세 가능성을 지지한다. official G1-Comp 스펙은 knee `0~165deg`, hip pitch `P±154deg`, knee torque `120N.m`를 공개하고, IEEE Robots Guide/HuB는 G1 deep squat 사례를 공개한다.
- 로컬 MJCF도 foot-fixed visible target을 담을 수 있다. 0.12m와 0.16m pelvis drop target은 foot error 1mm 미만으로 풀렸고, exp29 visible gate의 knee/hip delta 기준도 통과했다.
- 하지만 이 실험은 정적 가능성만 닫는다. M19 완료에는 native rollout no-fall/contact/return과 browser replay가 여전히 필요하다.

### 가설은 통과했나?
- [x] PASS — 공개 근거와 local static IK가 모두 G1 visible/deep squat 가능성을 지지했다.
- [ ] FAIL — 실행 후 판단

### 정의에 반영
- M19 완료 기준은 바꾸지 않는다. 이 실험은 visible squat gate의 전제를 갱신할 뿐, native/browser replay gate를 대체하지 않는다.

### 다음 실험 후보
- QP-lite WBC: pelvis height, foot pose, CoM/support, vertical momentum, foot force balance, inverse torque penalty를 한 step lookahead solve로 묶는다.
