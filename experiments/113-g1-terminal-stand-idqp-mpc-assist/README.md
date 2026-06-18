# 113-g1-terminal-stand-idqp-mpc-assist — G1 terminal stand IDQP/MPC assist

## 1. 가설 (Hypothesis)

Exp112는 primitive MPC로 no-fall/contact/slip/depth를 만들었지만 return-to-stand와 knee/hip gate가 남았다. Return phase에서 stand target, lower-body inverse-dynamics-style PD torque, foot anchoring, floating-base recovery assist를 함께 넣으면 deep crouch에서 stand-up 가능한 corridor가 열릴 수 있다.

## 2. 방법 (Method)

- 기반: exp112 WBC/MPC primitive selector.
- 변경: return phase 또는 낮은 base height에서 terminal stand assist를 추가했다.
- assist 구성: default stand target, lower-body joint qfrc, foot-site stance qfrc, base vertical/upright qfrc proxy.
- 판정: exp29 native visible gate를 통과한 경우에만 browser replay를 시도한다.
- 실행: `python run_terminal_stand_idqp_mpc_assist.py --seconds 6.0`.

### 웹 근거

- Whole-body inverse-dynamics MPC는 torque/contact force를 하나의 predictive layer에서 같이 최적화해야 한다고 설명한다. 접근일: 2026-06-18. https://arxiv.org/html/2511.19709v1
- Contact-force constrained humanoid tracking은 floating-base humanoid motion이 joint torques뿐 아니라 friction-constrained contact force에 의해 좌우된다고 설명한다. 접근일: 2026-06-18. https://la.disneyresearch.com/wp-content/uploads/PROJECT_Humanoids-mocap_IEEE-RAS-ICHR-2013_PAPER1.pdf
- Humanoid squat TP-MPC/WBC 연구는 squat motion을 CoM planning과 whole-body control 결합 문제로 다룬다. 접근일: 2026-06-18. https://pmc.ncbi.nlm.nih.gov/articles/PMC11769464/
- Constrained whole-body tracking 연구는 contact mode를 존중하는 QP/CBF filter가 humanoid tracking safety에 필요하다고 설명한다. 접근일: 2026-06-18. https://arxiv.org/html/2606.00374v1
- MuJoCo computation docs는 qfrc와 contact solver를 통해 local controller 실험을 재현할 수 있는 dynamics 기반을 제공한다. 접근일: 2026-06-18. https://mujoco.readthedocs.io/en/stable/computation/index.html

## 3. 결과 (Results)

| Run | Verdict | Drop | Knee | Hip | Contact | Slip | Final h | Return | Fall |
|---|---|---:|---:|---:|---:|---:|---:|---|---|
| terminal-stand-soft | DEPTH_PENDING_8CM | 0.0553m | 0.395 | 0.216 | 1.00 | 0.029m | 0.7409m | True | never |
| terminal-stand-earlier | DEPTH_PENDING_8CM | 0.0394m | 0.325 | 0.283 | 0.99 | 0.029m | 0.7442m | True | never |
| terminal-stand-strong | DEPTH_PENDING_8CM | 0.0318m | 0.267 | 0.241 | 0.99 | 0.029m | 0.7479m | True | never |
| terminal-depth-fast-return | FAIL_FALL | 1.5204m | 0.432 | 0.298 | 0.92 | 0.331m | -0.4094m | False | 4.68s |
| terminal-depth-preserve-delayed | FAIL_FALL | 1.5189m | 0.441 | 0.426 | 0.92 | 0.336m | -0.5906m | False | 5.28s |
| terminal-depth-late-pop | FAIL_FALL | 1.5138m | 0.389 | 0.874 | 0.86 | 0.415m | -0.7189m | False | 5.38s |
| terminal-knee-return | FAIL_FALL | 1.5188m | 0.397 | 0.206 | 0.89 | 0.394m | -0.7075m | False | 4.54s |

Best terminal assist run: `terminal-stand-soft` -> `DEPTH_PENDING_8CM`.

박제:
- `verify/result.json`
- `verify/terminal-stand-idqp-mpc-assist-summary.md`
- `verify/<attempt>/native-eval.json`

## 4. 통찰 (Insights)

- Native verdict: `FAIL_VISIBLE_8CM_GATE`.
- Browser replay attempted: `False`.
- Best run은 drop `0.0553m`, knee `0.395rad`, hip `0.216rad`, contact `1.00`, slip `0.029m`, final height `0.7409m`이다.
- Terminal stand assist는 안정 복귀 자체는 회복했지만, 그 대가로 visible depth/pose가 5.53cm 수준으로 얕아졌다. 반대로 depth 보존 후보는 fall/slip으로 무너졌다.
- 다음 길은 qfrc proxy를 더 키우는 것이 아니라 full-order predictive optimization 또는 upstream tracker parity다.

### 가설은 통과했나?

- [ ] PASS — native exp29 visible gate를 통과했다.
- [x] FAIL — terminal stand IDQP/MPC assist만으로 native exp29 visible gate를 닫지 못했다.
