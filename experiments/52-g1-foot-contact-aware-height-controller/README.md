# 52-g1-foot-contact-aware-height-controller — foot-contact-aware height controller

## 1. 가설 (Hypothesis)

exp51의 action projection은 policy 출력이 이미 contact-breaking direction으로 갈 때 너무 늦게 개입했다. foot pose/contact를 1순위로 둔 controller가 pelvis height/phase command만 낮은 차원으로 ramp하면, exp36의 stable-but-shallow foot-fixed IK corridor를 더 깊게 밀 수 있다.

근거:
- Squat Motion of a Humanoid Robot Using Three-Particle Model Predictive Control and Whole-Body Control은 continuous squatting을 TP-MPC와 WBC 조합으로 다룬다. https://pmc.ncbi.nlm.nih.gov/articles/PMC11769464/ (accessed 2026-06-18)
- Multi-Contact Whole Body Force Control은 position-controlled robots에서는 contact force 직접 제어가 어렵다는 한계를 지적한다. https://arxiv.org/html/2312.16465v3 (accessed 2026-06-18)
- Task-based WBC with ZMP regulation은 squat-like motion에서 CoM, relative foot pose, joint-limit avoidance task를 같이 둔다. https://www.lirmm.fr/krut/pdf/2014_galdeano_ssd-0568454426/2014_galdeano_ssd.pdf (accessed 2026-06-18)
- Unitree G1 whole-body tracking/teleoperation 사례들은 G1에서 whole-body contact-rich controller가 별도 연구 주제임을 보여준다. https://developer.nvidia.com/blog/streamline-robot-learning-with-whole-body-control-and-enhanced-teleoperation-in-nvidia-isaac-lab-2-3/ (accessed 2026-06-18)

## 2. 방법 (Method)

### 셋업
- 모델: local MuJoCo Playground G1 env.
- 초기 정책: exp46 force/torque residual checkpoint 또는 policy disabled mode.
- controller: exp36 foot-fixed IK target을 base로, per-step support/contact/slip/vertical-velocity health가 나쁠 때 blend 증가를 멈추거나 후퇴한다.

### 측정 metric
- visible pelvis drop, knee/hip pitch delta, fall time, final height/return, both-feet contact ratio, foot slip, support margin.
- M19 PASS는 exp29 visible gate와 native/browser replay가 동시에 통과해야 한다.

## 3. 결과 (Results)

### 데이터
| Attempt | Verdict | Drop | Knee | Hip | Contact | Slip | 비고 |
|---|---|---:|---:|---:|---:|---:|---|
| drop0p08-blend0p25-adapt0p08-policy1p0 | DEPTH_PENDING | 0.0212m | 0.201 | 0.119 | 1.00 | 0.013m | stable stance/return, shallow |
| drop0p08-blend0p35-adapt0p10-policy1p0 | DEPTH_PENDING | 0.0264m | 0.222 | 0.136 | 1.00 | 0.014m | best no-fall depth |
| drop0p10-blend0p35-adapt0p10-policy1p0 | FAIL_FALL | 1.5049m | 0.614 | 0.549 | 0.84 | 0.896m | visible pose leverage but fall at 4.38s |
| drop0p12-blend0p45-adapt0p14-policy1p0 | FAIL_FALL | 1.5094m | 0.600 | 0.530 | 0.87 | 0.911m | visible pose leverage but fall at 3.32s |

### 박제 위치
- `verify/contact-height-sweep/result.json`
- `verify/contact-height-sweep/contact-height-summary.md`
- per-attempt raw JSON under `verify/contact-height-sweep/*/native-eval.json`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- Full stabilizer prior is mandatory. no-policy/default-pose variants collapse around 1.24s, matching exp36's old no-policy failure.
- foot-contact-aware blend gating recovers stance: best no-fall attempt keeps contact 1.00, slip 0.014m, and return-to-stand true.
- The stable corridor is still shallow: best no-fall drop is 2.64cm, far below the 8cm visible gate.
- Raising target drop to 10-12cm gives knee/hip pose leverage, but falls with foot slip near 0.9m. This repeats the same depth-vs-stance cliff seen in exp36/44/51.

### 가설은 통과했나?
- [ ] PASS — controller preserves foot/contact while reaching visible depth and return.
- [x] FAIL — controller preserves foot/contact only in a shallow corridor; visible-depth variants still fall.

### 정의에 반영
- M19 still requires native visible gate before browser replay. Contact-aware low-dimensional control alone is not enough.

### 다음 실험 후보
- Train a policy inside the contact-aware controller envelope: action space should be pelvis-height/phase residuals only, with curriculum target starting at 2.5cm stable corridor and expanding toward 8cm.
