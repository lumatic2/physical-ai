# 60-g1-safe-combo-curriculum-probe - safe_combo depth curriculum boundary

> `experiments/60-g1-safe-combo-curriculum-probe/README.md` - exp59 safe_combo basis의 8cm gate 확장 가능성 probe. 접근일: 2026-06-18.

## 1. 가설 (Hypothesis)

exp59에서 `safe_combo` residual basis가 no-fall stable drop을 4.73cm에서 5.73cm로 늘렸다. 같은 basis를 residual scale, target drop, teacher blend curriculum으로 조금씩 키우면 8cm visible gate에 더 가까워질 수 있다.

외부 근거:
- Gait-conditioned RL on Unitree G1 uses a structured curriculum that progressively introduces gait complexity and expands command space. URL: https://arxiv.org/html/2505.20619v1, access date: 2026-06-18.
- residual policy learning works best when a good but imperfect controller exists and the learned residual is restricted to task-specific corrections. URL: https://github.com/k-r-allen/residual-policy-learning, access date: 2026-06-18.
- ResMimic frames humanoid residual learning as a second-stage correction on top of a general motion-tracking controller. URL: https://arxiv.org/html/2510.05070v1, access date: 2026-06-18.
- Safe policy learning emphasizes that continuous-control agents must remain near-safe during training and convergence. URL: https://proceedings.mlr.press/v155/chow21a/chow21a.pdf, access date: 2026-06-18.

## 2. 방법 (Method)

### 셋업
- 모델: local G1 MuJoCo model.
- teacher: exp55 best no-fall CoM feedback controller.
- residual basis: exp59 `safe_combo`.
- 코드: `run_safe_combo_curriculum_probe.py`.
- raw evidence: `verify/safe-combo-curriculum/`.

### 시나리오
- V0: teacher baseline 8cm target.
- V1: exp59 stable point 재현: drop 0.08, residual scale 0.06.
- V2: scale 0.09 at 8cm target.
- V3: target 10cm, blend 0.55, residual scale 0.06/0.09.
- V4: soft/zmp_hold filter로 10~12cm candidate collapse가 줄어드는지 확인.

### 측정 metric
- M19 native gate: fall 없음, visible drop >=0.08m, knee >=0.60rad, hip pitch >=0.35rad, return, contact >=0.90, slip <=0.15m.
- 추가 metric: support margin, ZMP margin, foot slip, contact ratio, return height.

## 3. 결과 (Results)

### 데이터
| Run | Verdict | Drop target | Residual | Native drop | Knee | Hip | Contact | Slip | CoM min | ZMP min | Fell |
|-----|---------|------------:|---------:|------------:|-----:|----:|--------:|-----:|--------:|--------:|------|
| teacher-0p08 | DEPTH_PENDING | 0.08 | 0.00 | 0.0473m | 0.368 | 0.096 | 1.00 | 0.017m | 0.0292m | 0.0184m | never |
| safe-combo-0p08-r0p06 | DEPTH_PENDING | 0.08 | 0.06 | 0.0573m | 0.426 | 0.123 | 1.00 | 0.019m | 0.0182m | 0.0078m | never |
| safe-combo-0p08-r0p09 | FAIL_FALL | 0.08 | 0.09 | 0.6454m | 0.532 | 0.346 | 0.95 | 0.160m | -0.5740m | -0.5739m | 5.86s |
| safe-combo-0p10-r0p06 | FAIL_FALL | 0.10 | 0.06 | 1.5021m | 0.619 | 0.450 | 0.83 | 0.961m | -0.5809m | -0.5799m | 4.54s |
| safe-combo-0p10-r0p09 | FAIL_FALL | 0.10 | 0.09 | 1.5077m | 0.617 | 0.425 | 0.87 | 0.949m | -0.5814m | -0.5810m | 4.48s |
| soft-combo-0p10-r0p09 | FAIL_FALL | 0.10 | 0.09 | 1.5027m | 0.617 | 0.447 | 0.82 | 0.975m | -0.5814m | -0.5809m | 4.52s |
| zmp-hold-combo-0p12-r0p10 | FAIL_FALL | 0.12 | 0.10 | 1.4968m | 0.598 | 0.409 | 0.86 | 0.916m | -0.5808m | -0.5803m | 4.82s |

Best no-fall run remains `safe-combo-0p08-r0p06`: 5.73cm stable drop, contact 1.00, slip 0.019m, return true.

### 박제 위치
- `verify/safe-combo-curriculum/result.json`
- `verify/safe-combo-curriculum/safe-combo-curriculum-summary.md`
- `verify/safe-combo-curriculum/*/native-eval.json`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- `safe_combo` basis has a narrow stable boundary: scale 0.06 at 8cm target is stable, but scale 0.09 already crosses into fall.
- 10cm target and higher blend do not produce a controlled 8cm squat. They pass through visible-depth geometry only as collapse.
- soft/zmp_hold filtering did not rescue the 10~12cm curriculum candidates. Once the target asks for more depth, support/ZMP margins collapse to about -0.58m.

### 가설은 통과했나?
- [ ] PASS
- [x] FAIL - scale/curriculum expansion did not approach the 8cm native gate while preserving stance/contact/return.

### 정의에 반영
- M19 completion remains unchanged: native visible gate and browser replay must pass together.
- The next technical path should not be another hand residual scale sweep. It should move to torque/contact-aware WBC or actual learning with hard stance-foot constraints.

### 다음 실험 후보
- torque/contact-aware WBC: stance foot velocity/slip as hard or high-weight cost, pelvis height phase as the optimized task.
- safe_combo PPO only if the action projection can hard-bound support/ZMP/slip, not merely reward-shape them.
