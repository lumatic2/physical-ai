# 94-g1-visible-reference-motion-tracking-probe — G1 visible reference tracking probe

> M19. exp93까지 scalar controller/action-wrapper 계열이 knee/contact/slip 동시 gate에서 포화됐기 때문에, 먼저 G1이 visible squat reference를 담을 수 있는지와 현재 stabilizer-conditioned tracker가 그 reference를 native에서 따라갈 수 있는지를 분리 검증한다.

## 1. 가설 (Hypothesis)

G1 reference motion / motion-tracking route는 squat 자체가 불가능해서 막힌 것이 아니라, 현재 stabilizer policy에 visible knee flexion reference를 안전하게 추종시키는 전용 tracking policy가 없어서 막혔을 것이다.

## 2. 방법 (Method)

### 셋업
- 모델: local MuJoCo G1 `ContactAwareSquat` + exp67 native evaluator.
- 데이터: static visible reference target + 6개 native tracking variants.
- 하네스 구성: `run_visible_reference_motion_tracking_probe.py`, raw evidence under `verify/visible-reference-motion-tracking-probe/`.

### 웹 근거
- Unitree official G1 specs: 23~43 joint motors, 6 DoF per leg, knee 0~165deg, hip pitch +/-154deg, knee torque 90/120 N.m. URL: https://www.unitree.com/g1/ accessed 2026-06-18.
- UniTracker reports 29-DoF Unitree G1 whole-body motion tracking and includes squatting among real-world tracked motions. URL: https://arxiv.org/html/2507.07356v2 accessed 2026-06-18.
- ASAP uses retargeted human motions to pre-train humanoid whole-body motion tracking policies and evaluates on Unitree G1. URL: https://agile.human2humanoid.com/ accessed 2026-06-18.
- G1 Moves provides retargeted Unitree G1 trajectories, RL training data, and trained ONNX policies. URL: https://huggingface.co/datasets/exptech/g1-moves accessed 2026-06-18.

### 시나리오
- V0: static reference probe. Intended base drop 9cm, knee delta 0.64rad, hip pitch delta 0.38rad.
- V1: `reference-open-loop` direct reference injection without stabilizer force.
- V2: stabilizer/reference blends from 0.25 to 0.55 with stance force and foot preload.
- V3: health-gated release and knee-priority reference variants.

### 측정 metric
- exp29 visible gate: no fall, pelvis drop >=8cm, knee >=0.60rad, hip >=0.35rad, return to stand, contact >=0.90, slip <=0.08m, joint limit violation <=0.05.
- Static reference feasibility: intended base drop, knee/hip deltas, foot site error.

## 3. 결과 (Results)

### 데이터
| Run | Verdict | Drop | Knee | Hip | Contact | Slip | Fall | 비고 |
|-----|---------|------|------|-----|---------|------|------|------|
| static reference | PASS reference intent | 0.090m intended | 0.640rad | 0.380rad | - | foot z err 0.008m | - | visible reference target exists |
| reference-open-loop | FAIL | 1.519m | 0.516rad | 0.363rad | 0.91 | 0.984m | 1.26s | direct reference collapses |
| stabilizer-reference-055-contact | FAIL pose gate | 0.255m | 0.401rad | 0.374rad | 0.99 | 0.046m | never | depth/contact/slip pass, knee short by 0.199rad |
| release-reference-050 | FAIL depth gate | 0.033m | 0.276rad | 0.205rad | 1.00 | 0.024m | never | release protects stance but returns to micro-dip |
| stabilizer-reference-040-contact | FAIL depth gate | 0.029m | 0.238rad | 0.154rad | 1.00 | 0.007m | never | safe but shallow |

### 박제 위치
- `verify/visible-reference-motion-tracking-probe/result.json`
- `verify/visible-reference-motion-tracking-probe/visible_reference_probe.json`
- `verify/visible-reference-motion-tracking-probe/visible-reference-motion-tracking-summary.md`
- Per-variant native rollouts: `verify/visible-reference-motion-tracking-probe/*/native-eval.json`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- 웹/논문 근거와 local static probe를 합치면 "G1로 squat reference가 원천적으로 불가능하다"는 결론은 맞지 않다.
- 현재 stabilizer-conditioned injection은 depth/contact/slip을 동시에 만들 수 있지만, knee flexion을 reference만큼 끌고 가지 못한다. best no-fall은 25.5cm drop, contact 0.99, slip 4.6cm인데 knee 0.401rad로 exp29 pose gate에 실패했다.
- open-loop reference는 1.26초 fall이므로 browser replay로 포장할 대상이 아니다. 다음은 controller sampling이 아니라 dedicated motion-tracking/reference-policy training 또는 G1 Moves/UniTracker류 retargeted policy ingestion이다.

### 가설은 통과했나?
- [x] PASS — static reference와 외부 사례는 squat 가능성을 지지하고, native failure는 robot kinematics보다 tracker/policy mismatch로 나타났다.

### 정의에 반영
- M19 완료 기준은 유지한다. exp94는 M19를 닫지 않고, 다음 route를 stabilizer-conditioned motion-tracking policy로 좁힌다.

### 다음 실험 후보
- exp95: retargeted G1 squat/motion clip ingestion 또는 짧은 reference-conditioned tracker fine-tune을 만들어, knee >=0.60rad를 직접 reward/observation target으로 학습한다.
