# 117-g1-full-order-idqp-mpc-smoke — G1 full-order ID-QP/MPC formulation smoke

## 1. 가설 (Hypothesis)

Exp109는 exp29 visible target이 static inverse-dynamics contact QP에서는 plausible하다고 보였지만, exp110/112/113/116은 direct dynamic tracking, primitive MPC, terminal assist, short retrain이 모두 실패했다. 이번에는 `M*qacc + bias` residual, foot contact-force generalized force, short-horizon support/slip/pose score를 한 chooser 안에 같이 넣으면 qfrc wrapper보다 exp29 native visible gate에 가까워질 수 있다.

## 2. 방법 (Method)

- 기반: exp67 native evaluator, exp110 lower-body target/contact-force QP helpers.
- controller: 각 tick마다 fraction 후보를 만들고 lower-body target, joint qfrc, foot contact-force qfrc를 계산했다.
- full-order term: MuJoCo `mj_fullM`으로 mass matrix를 얻고 desired lower-body acceleration에 대해 floating-base residual과 actuated residual을 계산해 horizon score에 넣었다.
- MPC term: 각 후보를 MuJoCo clone에서 짧게 rollout하고 support, ZMP, slip, contact loss, drop, knee, hip을 함께 점수화했다.
- 판정: native exp29 visible gate가 통과할 때만 browser replay를 시도한다.

### 웹 근거

- MuJoCo computation docs는 forward/inverse dynamics와 mass matrix/contact generalized force 계산의 근거를 제공한다. 접근일: 2026-06-18. https://mujoco.readthedocs.io/en/stable/computation/index.html
- Strict contact-force humanoid tracking은 floating-base humanoid tracking에서 contact force constraints가 핵심임을 보인다. 접근일: 2026-06-18. https://la.disneyresearch.com/wp-content/uploads/PROJECT_Humanoids-mocap_IEEE-RAS-ICHR-2013_PAPER1.pdf
- Whole-body humanoid locomotion on Unitree G1은 G1 계열 whole-body tracking에서 정책과 dynamics-aware stabilization이 함께 필요함을 보인다. 접근일: 2026-06-18. https://arxiv.org/html/2604.17335v1
- Squat motion TP-MPC/WBC 연구는 squat가 CoM/ZMP/contact를 함께 다루는 전신 제어 문제임을 뒷받침한다. 접근일: 2026-06-18. https://pmc.ncbi.nlm.nih.gov/articles/PMC11769464/

## 3. 결과 (Results)

| Run | Verdict | Drop | Knee | Hip | Contact | Slip | Final h | Return | Fall |
|---|---|---:|---:|---:|---:|---:|---:|---|---|
| full-order-pose-push | FAIL_FALL | 1.5064m | 0.644 | 0.446 | 0.95 | 0.594m | -0.7514m | False | 1.46s |
| full-order-balanced-visible | FAIL_FALL | 1.5103m | 0.596 | 0.454 | 0.96 | 0.595m | -0.7553m | False | 1.40s |
| full-order-safety-first | FAIL_FALL | 1.5105m | 0.605 | 0.402 | 0.95 | 0.691m | -0.7552m | False | 1.40s |

Best full-order MPC smoke run: `full-order-pose-push` -> `FAIL_FALL`.

박제:
- `verify/result.json`
- `verify/full-order-idqp-mpc-smoke-summary.md`
- `verify/<attempt>/native-eval.json`

## 4. 통찰 (Insights)

- Native verdict: `FAIL_VISIBLE_8CM_GATE`.
- Browser replay attempted: `False`.
- Best run은 drop `1.5064m`, knee `0.644rad`, hip `0.446rad`, contact `0.95`, slip `0.594m`이다.
- 세 후보가 모두 1.40~1.46초에 fall했기 때문에 큰 drop/knee/hip 수치는 showable squat가 아니라 collapse 이후 geometry다.
- 이 실험은 deployable WBC가 아니라 full-order formulation smoke다. 다만 이전 direct qfrc/primitive selector보다 명시적으로 floating-base residual, contact force, short-horizon gate를 같은 목적함수에 넣었다.

### 가설은 통과했나?

- [ ] PASS — native exp29 visible gate를 통과했다.
- [x] FAIL — full-order ID-QP/MPC formulation smoke만으로 native exp29 visible gate를 닫지 못했다.

### 정의에 반영

- M19 완료 조건은 그대로 native exp29 visible gate + browser replay다. 본 실험이 실패하면 다음은 더 많은 hand adapter sweep이 아니라 deployable whole-body controller 또는 장기 tracker training으로 넘어가야 한다.
