# 114-g1-squat-capability-gate — G1 squat capability gate

## 1. 가설 (Hypothesis)

웹 근거와 로컬 최신 evidence를 함께 보면 Unitree G1은 squat-like posture와 full-body tracking이 원리상 가능하지만, 현재 M19 controller는 아직 exp29 visible native gate를 통과하지 못한다.

## 2. 방법 (Method)

### 셋업
- 모델: 로컬 M19 evidence ledger + 최신 웹 검색 근거.
- 데이터: exp43 static feasibility, exp113 terminal stand IDQP/MPC 결과, Unitree G1 문서, G1 Moves, UniTracker, Isaac Lab issue.
- 하네스 구성: learning experiment 1개로 `verify/result.json`과 `verify/capability-gate-summary.md`를 박제한다.

### 웹 근거
- Unitree G1 controls documentation은 G1 `Squat Mode`를 제공하지만, “no balance control”인 자세 전환으로 설명한다. URL: https://docs.quadruped.de/projects/g1/html/operation_1.2.html (accessed 2026-06-18)
- Unitree G1 overview documentation은 leg당 6 DoF와 23 DoF basic / 확장 EDU 구성을 설명한다. URL: https://www.docs.quadruped.de/projects/g1/html/g1_overview.html (accessed 2026-06-18)
- IEEE Robots Guide는 G1 deep squat 자세 이미지를 싣고 flexibility를 언급한다. URL: https://robotsguide.com/robots/unitree-g1 (accessed 2026-06-18)
- G1 Moves는 Unitree G1 EDU 29DOF용 60개 모션, retargeted trajectories, RL training data, ONNX policies를 제공한다. URL: https://huggingface.co/datasets/exptech/g1-moves (accessed 2026-06-18)
- UniTracker는 29-DoF Unitree G1에서 8,100개 이상 motion tracking을 보고한다. URL: https://arxiv.org/html/2507.07356v2 (accessed 2026-06-18)
- Isaac Lab issue #3751은 학습된 G1 policy도 MuJoCo model/scene mismatch에서 즉시 collapse할 수 있음을 보여준다. URL: https://github.com/isaac-sim/IsaacLab/issues/3751 (accessed 2026-06-18)

### 시나리오
- V0: 웹 근거에서 “스쿼트 가능성”과 “stock Squat Mode의 한계”를 분리한다.
- V1: exp43 static feasibility로 로컬 G1 MJCF가 visible pose를 담는지 확인한다.
- V2: exp113 최신 native controller 결과로 현재 M19 controller가 바로 성공하는지 확인한다.

### 측정 metric
- public posture evidence: squat posture/mode 또는 full-body tracking 근거 존재.
- static gate: pelvis drop >= 0.08m, knee delta >= 0.60rad, hip pitch delta >= 0.35rad.
- native gate: exp29 visible gate pass 여부와 browser replay attempt 여부.

## 3. 결과 (Results)

### 데이터
| Run | Verdict | 핵심 수치 | 비고 |
|---|---|---|---|
| V0 | SUPPORTED_BUT_NOT_AUTONOMOUS | Squat Mode exists, but no balance control | stock mode는 M19 성공으로 취급하면 안 됨 |
| V1 | KINEMATICALLY_PLAUSIBLE | static 0.16m drop: foot error 0.0008m, knee 0.930rad, hip 0.444rad | local visible pose target은 가능 |
| V2 | CURRENT_CONTROLLER_FAILS | best stable drop 0.0553m; visible branches fall/slip | browser replay not attempted |

최종 verdict: `CAPABLE_IN_PRINCIPLE__CURRENT_CONTROLLER_FAILS`.

### 박제 위치
- `verify/result.json`
- `verify/capability-gate-summary.md`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- G1으로 스쿼트가 “원리상 가능한가?”에 대한 답은 yes에 가깝다. 공식/공개 문서와 데이터셋/연구가 posture feasibility와 full-body tracking route를 지지한다.
- 그러나 Unitree의 Squat Mode는 균형 제어 없는 자세 모드이므로, 우리가 원하는 M19의 “balanced lowering/hold/return skill”과 다르다.
- 현재 native controller는 아직 실패다. 최신 exp113 best stable branch는 return/contact/slip을 회복했지만 5.53cm shallow이고, visible-depth branch는 fall/slip으로 무너졌다.

### 가설은 통과했나?
- [x] PASS — 공개 근거와 static feasibility는 가능성을 지지하고, 최신 native 결과는 current-controller failure를 확인했다.
- [ ] FAIL — 실행 후 판단

### 정의에 반영
- M19 완료 기준은 유지한다. stock Squat Mode나 static pose만으로는 완료하지 않고, exp29 visible gate + native/browser replay를 모두 요구한다.

### 다음 실험 후보
- upstream/reference tracker parity: G1 Moves/UniTracker식 tracker가 요구하는 exact scene/action/observation contract를 먼저 맞춘다.
- full-order ID-QP/MPC: current qfrc proxy/primitive selector가 아닌 contact force와 floating-base dynamics를 함께 푸는 controller로 전환한다.
