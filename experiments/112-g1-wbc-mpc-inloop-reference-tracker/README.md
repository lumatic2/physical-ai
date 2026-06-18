# 112-g1-wbc-mpc-inloop-reference-tracker — G1 WBC/MPC-in-loop reference tracker

## 1. 가설 (Hypothesis)

G1은 공개 자료와 연구 사례상 스쿼트 형태 자체는 가능하지만, 우리 local M19 실패는 자세 target 불가능성이 아니라 contact/slip/return을 동시에 보는 동적 controller 부재일 가능성이 크다. 매 control tick에서 여러 WBC primitive를 짧은 MuJoCo horizon으로 비교해 고르면 reward retrain이나 one-shot qfrc wrapper보다 exp29 visible gate에 가까워질 것이다.

## 2. 방법 (Method)

- 기반: exp91 contact-constrained pose qfrc wrapper와 exp67 native evaluator.
- 변경: `choose_blend`를 primitive MPC wrapper로 monkeypatch했다. 각 tick마다 safety-hold, visible-push, return-guard 계열 primitive를 각각 short-horizon으로 rollout하고, drop/knee/hip/support/ZMP/contact/slip/stand 비용으로 다시 고른다.
- 판정: exp29 native visible gate를 통과한 경우에만 browser replay를 시도한다.
- 실행: `python run_wbc_mpc_inloop_reference_tracker.py --seconds 6.0`.

### 웹 근거

- Unitree 공식 G1 설명은 큰 관절 가동 범위와 imitation/RL driven 특성을 내세운다. 접근일: 2026-06-18. https://www.unitree.com/g1
- Quadruped G1 operation docs에는 `Squat Mode`가 명시되어 있으며, 단 balance control 없는 slow transition이라고 설명한다. 접근일: 2026-06-18. https://docs.quadruped.de/projects/g1/html/operation_1.2.html
- IEEE Robots Guide의 Unitree G1 항목은 G1이 torso가 legs에 붙는 깊은 squat-like pose를 보인다고 설명한다. 접근일: 2026-06-18. https://robotsguide.com/robots/unitree-g1
- UniTracker는 Unitree G1 29-DoF에서 squat를 포함한 whole-body motion tracking을 다루며, future reference와 adaptation이 중요하다고 설명한다. 접근일: 2026-06-18. https://arxiv.org/html/2507.07356v3
- MuJoCo computation docs는 forward/inverse dynamics와 contact solver가 qfrc 기반 controller 실험의 물리 계산 근거임을 제공한다. 접근일: 2026-06-18. https://mujoco.readthedocs.io/en/stable/computation/index.html
- Floating-base humanoid motion tracking에서 strict contact force constraints가 필요하다는 연구는 contact force/torque를 함께 제한해야 함을 보인다. 접근일: 2026-06-18. https://la.disneyresearch.com/wp-content/uploads/PROJECT_Humanoids-mocap_IEEE-RAS-ICHR-2013_PAPER1.pdf

## 3. 결과 (Results)

| Run | Verdict | Drop | Knee | Hip | Contact | Slip | Final h | Return | Fall |
|---|---|---:|---:|---:|---:|---:|---:|---|---|
| mpc-return-biased-visible | POSE_GATE_PENDING | 0.2609m | 0.442 | 0.216 | 1.00 | 0.040m | 0.4941m | False | never |
| mpc-knee-contact-return | FAIL_FALL | 0.3760m | 0.413 | 0.401 | 0.92 | 0.091m | 0.3790m | False | 5.96s |
| mpc-braked-8cm-three-primitive | FAIL_FALL | 1.5287m | 0.552 | 0.349 | 0.95 | 0.357m | -0.3224m | False | 4.96s |

Best MPC run: `mpc-return-biased-visible` -> `POSE_GATE_PENDING`.

박제:
- `verify/result.json`
- `verify/wbc-mpc-inloop-reference-tracker-summary.md`
- `verify/<attempt>/native-eval.json`

## 4. 통찰 (Insights)

- Native verdict: `FAIL_VISIBLE_8CM_GATE`.
- Browser replay attempted: `False`.
- Best run은 drop `0.2609m`, knee `0.442rad`, hip `0.216rad`, contact `1.00`, slip `0.040m`이지만 return-to-stand는 실패했다.
- 공개 근거상 “G1이 스쿼트 자세를 취할 수 있나”의 답은 yes에 가깝다. 다만 우리 local M19 기준은 balance/contact/slip/return까지 포함한 dynamic visible squat라서, 내장 Squat Mode나 사진 evidence와 동일하지 않다.
- 이번 in-loop primitive MPC도 실패하면 다음은 primitive selector가 아니라 horizon-level full inverse-dynamics QP/MPC 또는 real reference tracker stack parity로 가야 한다.

### 가설은 통과했나?

- [ ] PASS — native exp29 visible gate를 통과했다.
- [x] FAIL — WBC/MPC-in-loop primitive selector만으로 native exp29 visible gate를 닫지 못했다.
