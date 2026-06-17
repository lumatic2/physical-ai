# Experiment 63 - G1 CoM-feasible trajectory probe

## Hypothesis

M19가 exp62에서 막힌 이유가 actuator authority 부족만이 아니라 trajectory feasibility 문제라면, static IK target을 바로 미는 대신 CoM/ZMP support margin을 먼저 만족하는 foot-fixed target trajectory를 만들고 그 안에서 pose target을 따라가야 한다.

공개 근거도 같은 방향을 가리킨다. humanoid squat 연구는 TP-MPC가 rough reference trajectory를 만들고 WBC가 그 trajectory를 추종하는 구조를 썼으며, squat에는 torso/arm/foot/contact wrench task가 같이 필요하다고 설명한다. 또 biped MPC/WBC 계열은 ZMP 또는 support polygon boundary를 안정성 제약으로 다룬다. 즉 이번 실험의 가설은 "더 센 torque"가 아니라 "CoM/ZMP feasible reference first"이다.

Sources accessed 2026-06-18:
- Chen, Zhang, Zhao, "Squat Motion of a Humanoid Robot Using Three-Particle Model Predictive Control and Whole-Body Control", Sensors 2025: https://www.mdpi.com/1424-8220/25/2/435
- Kim, Lee, Park, "Real-time Whole-body Model Predictive Control for Bipedal Locomotion with a Novel Kino-dynamic Model and Warm-start Method": https://arxiv.org/html/2505.19540v1
- Galdeano et al., "Task-based whole body motion generation with ZMP planning": https://www.lirmm.fr/krut/pdf/2014_galdeano_ssd-0568454426/2014_galdeano_ssd.pdf

## Method

`run_com_feasible_trajectory_probe.py` reuses the exp62 stack and changes the planning layer:

1. Solve static foot-fixed lower-body targets for target drops `[0, 2, 4, 6, 8]cm`.
2. Add a CoM-centering residual toward the foot support center during static solve.
3. Track the final 8cm target through a rate-limited planned-drop envelope.
4. Gate envelope growth on support margin, approximate ZMP margin, vertical velocity, and foot slip.
5. Mix the trajectory with the existing stabilizer policy and optionally apply exp62 lower-body `qfrc_applied` PD torque.

Verification command:

```powershell
$env:OPENBLAS_NUM_THREADS='1'; C:\tmp\e34\Scripts\python.exe .\experiments\63-g1-com-feasible-trajectory-probe\run_com_feasible_trajectory_probe.py
```

Raw evidence:
- `verify/com-feasible-trajectory/result.json`
- `verify/com-feasible-trajectory/com-feasible-trajectory-summary.md`
- `verify/com-feasible-trajectory/*/native-eval.json`

## Results

Result: `FAIL_M19_NATIVE_GATE`.

| Attempt | Verdict | Drop | Planned | Knee | Hip | Contact | Slip | CoM min | ZMP min | Fell |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `com-envelope-slow` | `FAIL_FALL` | 1.5390m | 0.0496m | 0.618 | 0.368 | 0.86 | 0.916m | -0.6031m | -0.6063m | 2.22s |
| `com-envelope-torque` | `DEPTH_PENDING` | 0.0424m | 0.0800m | 0.246 | 0.168 | 1.00 | 0.016m | -0.1696m | -0.0479m | never |
| `com-envelope-fast-torque` | `FAIL_FALL` | 1.4982m | 0.0800m | 0.434 | 0.373 | 0.94 | 0.851m | -0.6124m | -0.6118m | 5.36s |
| `com-strong-center-torque` | `DEPTH_PENDING` | 0.0551m | 0.0800m | 0.253 | 0.168 | 1.00 | 0.016m | -0.1807m | -0.0522m | never |
| `com-strong-stabilizer-torque` | `DEPTH_PENDING` | 0.0167m | 0.0800m | 0.157 | 0.114 | 1.00 | 0.012m | 0.0474m | 0.0418m | never |

Best no-fall run: `com-strong-center-torque`, visible drop 5.51cm, contact 1.00, slip 1.6cm, but knee/hip pose and support/ZMP margins still fail the exp29 gate.

The static solver itself was not the blocker: all 0-8cm static targets solved with zero foot error and positive static CoM/support margin. The dynamic rollout is the blocker.

## Insights

Static CoM-feasible IK is not enough. The solver can place the pelvis and lower-body joints into a plausible 8cm squat target, but the native controller cannot turn that static sequence into a dynamically feasible transition.

The stabilizer mix recovers no-fall behavior, but it also pulls the motion back toward shallow standing. Reducing that mix allows knee/hip movement, but then support/ZMP margins collapse and the robot falls. This reproduces the exp59-62 pattern from a different planning angle: the stable corridor is still around 5-6cm, not the 8cm visible gate.

Next technical step should not be another static target interpolation. It should either implement a real short-horizon centroidal/WBC controller with contact-force and joint-torque constraints, or narrow M19 into an intermediate recoverable 6cm stance transition before attempting the full exp29 visible gate again.
