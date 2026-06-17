# 69-g1-terminal-stand-horizon-optimizer

## Hypothesis

웹 검색 기준으로 Unitree G1의 squat 가능성 자체는 부정할 이유가 작다. Unitree는 G1을 큰 관절 가동범위와 imitation/RL driven motion이 가능한 휴머노이드로 설명하고, G1 developer guide는 다리 6-DOF와 허리 DOF를 명시한다. 별도 연구에서도 humanoid squat-like motion은 TP-MPC와 WBC 조합, 또는 ZMP/CoM 제약이 들어간 whole-body MPC 문제로 다뤄진다.

따라서 이번 가설은 "G1이 스쿼트를 할 수 있는가"가 아니라, exp68의 6.51cm 안정 복귀 cliff를 넘기려면 hand-picked parameter sweep이 아니라 terminal stand constraint를 가진 full-rollout horizon objective가 필요하다는 것이다.

Sources accessed 2026-06-18:
- https://www.unitree.com/g1
- https://support.unitree.com/home/en/G1_developer
- https://www.mdpi.com/1424-8220/25/2/435
- https://arxiv.org/html/2505.19540v1
- https://underactuated.mit.edu/humanoids.html

## Method

- Reuse exp67's qfrc-assisted WBC selector as the actuator/controller layer.
- Generate candidate descend/return trajectory plans programmatically around the exp68 stability cliff.
- Run each candidate through a full 6s native MuJoCo rollout.
- Score candidates with a terminal stand objective:
  - heavy penalty for fall
  - 7cm depth shortfall
  - final stand-height shortfall
  - contact, slip, support, ZMP, and joint-limit penalties
- Record raw evidence under `verify/terminal-stand-horizon-optimizer/`.

Command:

```powershell
$env:OPENBLAS_NUM_THREADS='1'; C:\tmp\e34\Scripts\python.exe .\experiments\69-g1-terminal-stand-horizon-optimizer\run_terminal_stand_horizon_optimizer.py
```

## Results

Native verdict: `FAIL_RECOVERABLE_7CM_GATE`.

Raw evidence:
- `verify/terminal-stand-horizon-optimizer/result.json`
- `verify/terminal-stand-horizon-optimizer/terminal-stand-horizon-optimizer-summary.md`
- per-candidate `native-eval.json` files under `verify/terminal-stand-horizon-optimizer/<attempt>/`

Best terminal plan:

| Attempt | Score | Drop | Contact | Slip | CoM min | ZMP min | qfrc | Final h | Fell | Verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| `horizon-d0p0832-b0p532-r0p0686-td3p50-tr2p20` | 124.22 | 0.0655m | 0.99 | 0.050m | 0.0094m | -0.0065m | 14.8 | 0.7509m | never | `DEPTH_PENDING_7CM` |

Best no-fall/depth run after widening the candidate set:

| Attempt | Drop | Final h | Fell | Verdict |
|---|---:|---:|---|---|
| `horizon-d0p0832-b0p533-r0p0682-td3p50-tr2p20` | 0.1449m | 0.6101m | never | `RETURN_PENDING` |

The widened optimizer found two regimes:

- terminal-safe candidates return to stand with good contact/slip/ZMP, but saturate at about 6.55cm visible drop;
- deeper candidates can lower the body far beyond the 7cm intermediate gate without falling, but they do not return to stand within the rollout.

## Insights

The web-search answer is: yes, a G1-class humanoid squat is plausible in principle. The local dynamic result is narrower: the current controller stack can either keep terminal stand around 6.5cm or descend much deeper without recovery, but not both.

That changes the next M19 move. More target depth or wider blend search is no longer the right lever. The next experiment should start from the deep no-fall state and add a dedicated terminal recovery/stand-up controller, rather than asking the same descend planner to solve recovery implicitly.
