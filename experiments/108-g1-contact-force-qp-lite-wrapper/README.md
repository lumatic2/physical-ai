# 108-g1-contact-force-qp-lite-wrapper — G1 contact-force QP-lite wrapper

> `experiments/108-g1-contact-force-qp-lite-wrapper/README.md` — exp91 WBC-lite planner 위에 foot contact-force `(fx, fy, normal)` decision variable을 둔 QP-lite wrapper를 얹어 M19 visible squat gate를 다시 검증한다.

## 1. 가설 (Hypothesis)

Exp107은 no-fall 후보도 shallow 상태에서 friction limit에 붙고, visible 후보는 late fall/slip으로 무너진다는 것을 contact-force audit으로 보였다. 각 foot의 anchoring force와 normal preload를 QP로 풀어 qfrc에 더하면 WBC-lite score tuning보다 contact/slip을 직접 제한하면서 visible pose를 더 밀 수 있을 것이다.

## 2. 방법 (Method)

### 셋업
- 모델: local MuJoCo G1 + exp91 contact-constrained pose qfrc planner.
- wrapper: 매 control step에서 각 foot의 `(fx, fy, normal)`을 SLSQP QP-lite로 풀고 `Jacobian.T @ force`를 qfrc에 더했다.
- 비교 후보: exp91 visible-depth 계열 3개, exp106 friction 계열 4개.
- 판정: exp29 native visible gate가 통과할 때만 browser replay를 시도한다.

### 웹 근거
- Heavy-limb humanoid WBC는 generalized acceleration과 contact force를 함께 최적화하고 friction cone 제약을 둔다. 접근일: 2026-06-18. https://arxiv.org/html/2506.14278v1
- MuJoCo API는 `mj_contactForce`가 contact frame의 6D force/torque를 반환하고 `mj_applyFT`/Jacobian 방식으로 Cartesian force를 generalized force에 매핑할 수 있음을 제공한다. 접근일: 2026-06-18. https://mujoco.readthedocs.io/en/stable/APIreference/APIfunctions.html
- Strict contact force constrained tracking은 floating-base humanoid에서 contact forces와 joint torques를 제약 하에 계산해야 함을 보인다. 접근일: 2026-06-18. https://la.disneyresearch.com/wp-content/uploads/PROJECT_Humanoids-mocap_IEEE-RAS-ICHR-2013_PAPER1.pdf
- Prioritized WBC with contact constraints는 floating-base dynamics와 reaction forces만 포함하는 QP로 효율성과 friction-cone robustness를 얻는다고 설명한다. 접근일: 2026-06-18. https://junhyeokahn.github.io/data/kim2018_wbdc.pdf

## 3. 결과 (Results)

### 데이터
| Run | Verdict | Drop | Knee | Hip | Contact | Slip | qfrc | Fall |
|---|---|---:|---:|---:|---:|---:|---:|---|
| qp-lite-friction-medium-braked | DEPTH_PENDING_8CM | 0.0749m | 0.382 | 0.210 | 1.00 | 0.042m | 84.9 | never |
| qp-lite-braked-knee-conservative | DEPTH_PENDING_8CM | 0.0592m | 0.420 | 0.218 | 1.00 | 0.026m | 102.8 | never |
| qp-lite-braked-8cm-balanced | DEPTH_PENDING_8CM | 0.0597m | 0.421 | 0.209 | 0.99 | 0.026m | 127.1 | never |
| qp-lite-friction-minimal-depth-push | DEPTH_PENDING_8CM | 0.0513m | 0.380 | 0.237 | 0.99 | 0.015m | 108.0 | never |
| qp-lite-friction-medium-visible-push | FAIL_FALL | 1.5303m | 0.501 | 0.286 | 0.95 | 0.279m | 336.1 | 5.18s |
| qp-lite-friction-medium-depth-push | FAIL_FALL | 1.5288m | 0.478 | 0.283 | 0.94 | 0.288m | 327.5 | 4.76s |
| qp-lite-braked-knee-pose-push | FAIL_FALL | 1.5294m | 0.459 | 0.287 | 0.93 | 0.287m | 326.4 | 4.72s |

Best QP-lite run: `qp-lite-friction-medium-braked` -> `DEPTH_PENDING_8CM`.

### 박제 위치
- `verify/result.json`
- `verify/contact-force-qp-lite-summary.md`
- `verify/<attempt>/native-eval.json`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- Contact-force decision variable을 qfrc wrapper로 넣어도 native exp29 gate는 닫히지 않았다.
- Best run은 drop `0.0749m`, knee `0.382rad`, hip `0.210rad`, contact `1.00`, slip `0.042m`이다.
- 이 실험은 full inverse-dynamics QP가 아니라 foot-force wrapper이므로, 실패 원인은 QP route 전체 폐기가 아니라 wrapper 수준의 한계로 해석한다.

### 가설은 통과했나?
- [ ] PASS — native exp29 visible gate를 통과했다.
- [x] FAIL — foot-force QP-lite wrapper만으로 native exp29 visible gate를 닫지 못했다.

### 정의에 반영
- 다음 단계는 qfrc wrapper가 아니라 floating-base dynamics equality, torque limits, contact forces를 함께 푸는 full inverse-dynamics QP이거나, reference-motion policy retrain이다.
