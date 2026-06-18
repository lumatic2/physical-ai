# 111-g1-contact-aware-reference-retrain — G1 contact-aware reference retrain

> `experiments/111-g1-contact-aware-reference-retrain/README.md` — exp105 future-reference tracker를 contact/slip/support-aware reward로 restored PPO 재학습해 M19 native visible gate를 다시 평가한다.

## 1. 가설 (Hypothesis)

Exp103/105는 reference tracking signal을 넣으면 knee/hip pose에는 접근하지만 both-foot contact와 slip이 무너졌다. 최근 humanoid motion tracking work처럼 reference tracker를 유지하되 contact/support/slip reward와 contact-aware action prior를 강화하면, shallow retreat나 foot slip 없이 exp29 visible gate에 가까워질 수 있다.

## 2. 방법 (Method)

### 셋업
- 모델: local MuJoCo G1 + `ContactAwareReferenceSquat`.
- 초기 checkpoint: `C:\Users\yusun\projects\physical-ai\experiments\105-g1-future-reference-observation-tracker\verify\train\params.pkl`.
- 학습: restored PPO `20000` steps, lookahead `0.55s`, contact action scale `0.55`.
- 판정: native exp29 visible gate가 통과할 때만 browser replay를 시도한다.

### 웹 근거
- UniTracker는 Unitree G1에서 whole-body motion tracker를 sim/real로 검증한다. 접근일: 2026-06-18. https://arxiv.org/html/2507.07356v3
- Whole-body humanoid locomotion work는 reference motion tracker + closed-loop fine-tuning이 reward shaping 단독보다 유리하다고 설명한다. 접근일: 2026-06-18. https://arxiv.org/html/2604.17335v1
- Strict contact-force tracking은 floating-base humanoid에서 contact force/friction constraints가 motion tracking의 핵심 제약임을 보인다. 접근일: 2026-06-18. https://la.disneyresearch.com/wp-content/uploads/PROJECT_Humanoids-mocap_IEEE-RAS-ICHR-2013_PAPER1.pdf
- Squat motion literature frames squatting as CoM/ZMP/foot-force constrained whole-body coordination. 접근일: 2026-06-18. https://pmc.ncbi.nlm.nih.gov/articles/PMC11769464/

## 3. 결과 (Results)

### 데이터
| Run | Verdict | Timesteps | Drop | Knee | Hip | Contact | Slip | Final h | Fall |
|-----|---------|---:|---:|---:|---:|---:|---:|---:|---|
| contact-aware-reference | DEPTH_PENDING_7CM | 20000 | 0.0213m | 0.500rad | 0.329rad | 0.44 | 3.237m | 0.7390m | never |

Verdict: `DEPTH_PENDING_7CM`.

### 박제 위치
- `verify/result.json`
- `verify/native-eval.json`
- `verify/contact-aware-reference-summary.md`
- `verify/train/params.pkl`
- `verify/train/rewards.txt`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- Contact-aware reference retrain이 exp103/105의 foot slip/contact failure를 줄이는지 native gate로 직접 확인했다.
- 결과는 drop `0.0213m`, knee `0.500rad`, hip `0.329rad`, contact `0.44`, slip `3.237m`이다.
- native gate가 PASS하지 않으면 다음은 reward 재가중이 아니라 WBC/MPC-in-loop tracker 또는 더 긴 motion-tracking training이다.

### 가설은 통과했나?
- [ ] PASS — native exp29 visible gate를 통과했다.
- [x] FAIL — contact-aware reference retrain만으로 native exp29 visible gate를 닫지 못했다.

### 정의에 반영
- M19는 native+browser replay가 둘 다 통과해야만 닫힌다.
