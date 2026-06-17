# 47-g1-visible-target-command — G1 visible target as additive action command

## 1. 가설 (Hypothesis)

exp39/40이 reference-offset action origin만으로 실패한 이유가 stabilizer action을 대체하거나 재해석했기 때문이라면, stabilizer policy target은 유지한 채 exp45 visible/static lower-body target을 additive command로 더하면 visible-depth leverage가 생기고 collapse를 줄일 수 있다.

## 2. 방법 (Method)

### 셋업
- 모델: local MuJoCo Playground G1 runtime (`C:\tmp\e34`).
- Source policy: exp46 force/torque residual params가 있으면 사용하고, 없으면 exp28 default source를 쓴다.
- Visible target: exp45 `drop-0p12-com12-posture0p3` static manifold target.
- 하네스 구성: learning experiment 1개. `run_visible_target_command.py --sweep` 결과를 `verify/`에 박제한다.

### 외부 근거
- RuN은 kinematic prior와 residual policy를 분리해 humanoid locomotion을 학습하는 구조를 제안한다. URL: https://arxiv.org/html/2509.20696v1 (accessed 2026-06-18)
- Residual-action humanoid motion tracking은 reference motion 위에 residual action을 출력하는 방식으로 long-horizon behavior를 추적한다. URL: https://arxiv.org/pdf/2509.20717 (accessed 2026-06-18)
- Goal-conditioned humanoid controllers는 high-level goal과 upper-body coordination을 같이 다룬다. URL: https://openreview.net/forum?id=r0xwZWjLEi (accessed 2026-06-18)

### 시나리오
- A0: additive command gain sweep. `default + stabilizer_action + gain * visible_target_delta`.
- A1: support-gated command. support margin이 줄면 command를 자동 감쇠한다.
- A2: support+slip-gated command. foot slip이 커지면 command를 끈다.

### 측정 metric
- Native: visible drop `>=0.08m`, no fall, final height `>=0.74m`, contact ratio `>=0.90`, foot slip `<=0.15m`, joint violation `<=0.05`.
- Diagnostics: support margin, LR normal force imbalance, lower inverse torque.

## 3. 결과 (Results)

### 데이터
| Run | Verdict | Drop | Fell at | 비고 |
|-----|---------|------|---------|------|
| additive-0p15 | DEPTH_PENDING | 0.0161m | never | contact 1.00, slip 0.013m, support min 0.0570m |
| additive-0p25 | DEPTH_PENDING | 0.0232m | never | best stable depth, contact 1.00, slip 0.015m, support min 0.0360m |
| additive-0p35 | FAIL_FALL | 1.5020m | 4.42s | visible leverage turns into collapse, slip 0.915m |
| support-gated-0p35 | FAIL_FALL | 1.5070m | 4.68s | support gate delayed but did not prevent collapse |
| support-slip-gated-0p45 | FAIL_FALL | 1.5103m | 4.04s | slip gate too late once support breach starts |
| support-gated-low-policy-0p45 | FAIL_FALL | 1.5371m | 2.84s | reducing policy weight made collapse earlier |

### 박제 위치
- `verify/visible-target-command-summary.md`
- `verify/attempts/*/result.json`
- `verify/attempts/*/native-eval.json`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- Additive target command gives more depth leverage than exp46 reward-only: stable no-fall drop rose from 0.97cm to 2.32cm.
- The improvement still does not reach exp29 visible gate. The stable region ends before 8cm; at gain 0.35 and above the system crosses into support breach, large slip, LR imbalance 1.00, and fall.
- Support-gating the command reduces effective gain but does not recover once the body momentum leaves the support polygon. The bottleneck is now dynamic transition planning, not only target exposure.

### 가설은 통과했나?
- [ ] PASS — native visible squat gate까지 통과
- [x] FAIL — additive command improved shallow depth but did not pass native visible squat gate.

### 정의에 반영
- M19 완료 기준은 유지한다. native gate가 통과하지 않으면 browser replay를 만들지 않는다.

### 다음 실험 후보
- Target command를 PPO observation/action contract로 넣고 재학습하거나, descent/return을 phase-conditioned trajectory optimization으로 먼저 만들고 그 trajectory를 imitation/residual policy로 distill한다. 현재처럼 native controller에서 target을 더하는 방식은 2.3cm stable / visible-depth fall 경계를 못 넘는다.
