# 106-g1-friction-cone-wbc-planner — G1 friction-cone-aware WBC planner

> `experiments/106-g1-friction-cone-wbc-planner/README.md` — exp91 contact-constrained qfrc planner 주변에서 slip/friction proxy를 더 강하게 걸어 M19 visible squat gate를 다시 검증한다.

## 1. 가설 (Hypothesis)

Exp91의 best no-fall branch는 8cm drop/contact/hip은 만족했지만 slip 9cm와 knee 0.448rad 때문에 실패했다. friction/slip 제약을 더 강하게 걸고, knee qfrc assist를 support health가 충분한 순간에만 허용하면 exp29 visible gate에 더 가까워질 수 있다.

## 2. 방법 (Method)

### 셋업
- 모델: local MuJoCo G1 + exp91 contact-constrained pose qfrc planner.
- 하네스 구성: exp91의 WBC-lite candidate selector를 재사용하고, variant를 slip floor, support-gated knee assist, depth cap, return slip penalty 중심으로 다시 구성했다.
- 판정: exp29 visible gate native pass 후에만 browser replay를 시도한다.

### 웹 근거
- Humanoid squat 연구는 TP-MPC + WBC로 squat trajectory를 tracking한다. 접근일: 2026-06-18. https://pmc.ncbi.nlm.nih.gov/articles/PMC11769464/
- Strict contact force constrained tracking은 floating-base humanoid에서 contact forces와 friction constraints가 tracking feasibility를 좌우한다고 정리한다. 접근일: 2026-06-18. https://la.disneyresearch.com/publication/human-motion-tracking-control-with-strict-contact-force-constraints-for-floating-base-humanoid-robots/
- Heavy-limb humanoid WBC는 slip 방지를 위해 contact force를 friction cone 안에 제한해야 한다고 명시한다. 접근일: 2026-06-18. https://arxiv.org/html/2506.14278v1
- MuJoCo 문서는 contact force/inverse dynamics가 contact model과 분리될 수 없음을 설명한다. 접근일: 2026-06-18. https://mujoco.readthedocs.io/en/stable/computation/index.html

### 시나리오
- `friction-tight-light`: exp91 light qfrc 주변에서 slip penalty를 강화한다.
- `friction-tight-medium`: knee assist를 조금 올리되 slip floor를 더 낮춘다.
- `friction-braked-knee-*`: depth cap과 support health floor를 높여 fall branch를 피한다.
- `friction-knee-minimal-depth`: knee qfrc를 더 세게 주되 depth를 최소화한다.

### 측정 metric
- exp29 visible gate: drop >= 8cm, knee >= 0.60rad, hip >= 0.35rad.
- stability gate: no fall, return, contact >= 0.90, slip <= 0.08m, joint violation <= 0.05rad.

## 3. 결과 (Results)

### 데이터
| Run | Verdict | Drop | Knee | Hip | Contact | Slip | Final h | Fall |
|-----|---------|---:|---:|---:|---:|---:|---:|---|
| friction-knee-minimal-depth | DEPTH_PENDING_8CM | 0.0520m | 0.383 | 0.204 | 1.00 | 0.016m | 0.7262m | never |
| friction-tight-light | FAIL_FALL | 1.2235m | 0.463 | 0.324 | 0.94 | 0.277m | -0.4685m | 5.66s |
| friction-braked-knee-low-slip | FAIL_FALL | 1.5241m | 0.414 | 0.374 | 0.88 | 0.377m | -0.7119m | 5.38s |
| friction-tight-medium | FAIL_FALL | 1.5221m | 0.414 | 0.417 | 0.90 | 0.375m | -0.7212m | 5.40s |
| friction-braked-knee-return | FAIL_FALL | 1.5305m | 0.478 | 0.427 | 0.88 | 0.394m | -0.7121m | 5.38s |

Best friction-ranked run: `friction-knee-minimal-depth` -> `DEPTH_PENDING_8CM`.

### 박제 위치
- `verify/result.json`
- `verify/friction-cone-wbc-planner-summary.md`
- `verify/<attempt>/native-eval.json`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- Friction/slip을 강하게 벌점화하면 exp91의 9cm slip branch를 줄일 수 있는지 확인했다.
- Best run은 drop `0.0520m`, knee `0.383rad`, hip `0.204rad`, contact `1.00`, slip `0.016m`, final height `0.7262m`이다.
- Native gate가 PASS하지 않으면 browser replay는 M19 evidence가 아니다.

### 가설은 통과했나?
- [ ] PASS — native exp29 visible gate를 통과했다.
- [x] FAIL — friction-aware WBC planner variant만으로 native exp29 visible gate를 닫지 못했다.

### 정의에 반영
- M19는 native+browser replay가 둘 다 통과해야 닫힌다.
