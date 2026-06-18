# 107-g1-contact-force-feasibility-audit — G1 contact-force feasibility audit

> `experiments/107-g1-contact-force-feasibility-audit/README.md` — exp91/106의 대표 G1 squat 후보를 MuJoCo `mj_contactForce`로 다시 재생해 friction cone, CoP support margin, normal force imbalance를 직접 박제한다.

## 1. 가설 (Hypothesis)

Exp106까지의 WBC-lite/qfrc sweep은 slip proxy를 조이면 자세가 얕아지고, 자세를 밀면 fall/slip이 커졌다. 실제 contact force audit을 붙이면 M19의 다음 작업이 단순 qfrc sweep이 아니라 full contact-force QP 또는 reference-motion policy retrain이어야 하는지 더 명확해질 것이다.

## 2. 방법 (Method)

### 셋업
- 모델: local MuJoCo G1 + exp91 contact-constrained WBC-lite path.
- 비교 후보: exp91 visible-depth 계열 2개와 exp106 friction-tight 계열 2개.
- 계측: 기존 `EXP42.contact_wrench_summary` 호출 지점에 auditor를 주입해 각 control step의 `mj_contactForce` 값을 수집했다.
- 판정: native exp29 gate는 그대로 유지하고, 별도로 max friction ratio, min friction margin, CoP support margin, 좌우 normal imbalance를 박제했다.

### 웹 근거
- Heavy-limb humanoid WBC는 contact force와 generalized acceleration을 함께 최적화하고, slip 방지를 위해 friction cone 제약을 둔다. 접근일: 2026-06-18. https://arxiv.org/html/2506.14278v1
- MuJoCo 문서는 contact force가 contact frame의 normal/tangent friction cone으로 표현되며 solver 설정에 따라 elliptic/pyramidal cone을 쓴다고 설명한다. 접근일: 2026-06-18. https://mujoco.readthedocs.io/en/3.6.0/computation/
- Strict contact force constrained tracking 논문은 floating-base humanoid에서 base motion은 contact force와 friction constraints에 의해 실현 가능성이 결정된다고 설명한다. 접근일: 2026-06-18. https://la.disneyresearch.com/wp-content/uploads/PROJECT_Humanoids-mocap_IEEE-RAS-ICHR-2013_PAPER1.pdf
- Unitree 공식 open-source 페이지는 `unitree_mujoco`와 G1 지원 RL 구현을 공개 경로로 제시한다. 접근일: 2026-06-18. https://www.unitree.com/mobile/opensource/

## 3. 결과 (Results)

### 데이터
| Run | Force verdict | Drop | Knee | Hip | Max friction ratio | Min friction margin | Friction breach / saturation frames | CoP breach frames | Slip | Fall |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| exp91-poseqfrc-braked-8cm | FAIL_FALL | 0.4652m | 0.418 | 0.313 | 1.000 | 0.00N | 0 / 150 | 0 | 0.096m | 5.92s |
| exp91-poseqfrc-braked-knee | FAIL_FALL | 1.5257m | 0.392 | 0.435 | 1.000 | 0.00N | 0 / 158 | 1 | 0.400m | 5.50s |
| exp106-friction-knee-minimal-depth | FRICTION_LIMITED_SHALLOW | 0.0520m | 0.383 | 0.204 | 1.000 | 0.00N | 0 / 162 | 0 | 0.016m | never |
| exp106-friction-tight-medium | FAIL_FALL | 1.5221m | 0.414 | 0.417 | 1.000 | 0.00N | 0 / 109 | 0 | 0.375m | 5.40s |

### 박제 위치
- `verify/result.json`
- `verify/contact-force-feasibility-summary.md`
- `verify/<attempt>/native-eval.json`
- `verify/<attempt>/contact-force-audit.json`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- Contact force 자체는 이제 direct metric으로 남는다. 이후 실험은 slip proxy가 아니라 friction ratio / CoP margin / native pose gate를 같이 볼 수 있다.
- Best no-fall force-audited 후보: `{'attempt': 'exp106-friction-knee-minimal-depth', 'visible_drop': 0.05198772714581834, 'knee': 0.38281909097765765, 'hip': 0.2044383814544241, 'max_friction_ratio': 1.0, 'min_cop_support_margin': 0.001766757487128387, 'force_verdict': 'FRICTION_LIMITED_SHALLOW'}`.
- Best visible 후보: `{'attempt': 'exp91-poseqfrc-braked-knee', 'visible_drop': 1.5257117910043432, 'knee': 0.3920349879898506, 'hip': 0.4345580914435561, 'fell_at': 5.5, 'force_verdict': 'FAIL_FALL'}`.
- Native exp29 gate가 PASS하지 않았으므로 browser replay는 M19 완료 증거가 아니다.

### 가설은 통과했나?
- [ ] PASS — native exp29 visible gate와 force audit을 동시에 통과했다.
- [x] FAIL — force audit은 다음 병목을 좁혔지만 M19 native/browser gate를 닫지 못했다.

### 정의에 반영
- M19의 다음 구현은 WBC-lite score tuning이 아니라 contact-force decision variable을 가진 QP, 또는 contact-aware reference-motion policy retrain이어야 한다.
