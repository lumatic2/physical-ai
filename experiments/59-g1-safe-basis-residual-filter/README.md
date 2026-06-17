# 59-g1-safe-basis-residual-filter - support/ZMP/slip gated residual basis

> `experiments/59-g1-safe-basis-residual-filter/README.md` - exp58 collapse mode를 이어받은 safe residual filter probe. 접근일: 2026-06-18.

## 1. 가설 (Hypothesis)

exp58에서 knee/hip residual은 depth leverage를 만들지만 support/ZMP collapse를 냈다. 그렇다면 residual을 더 크게 주는 대신 support/ZMP/slip health로 knee residual을 gate하고 ankle recenter를 safe basis로 남기면, exp55 teacher의 no-fall corridor를 collapse 없이 깊게 만들 수 있다.

외부 근거:
- CBF-RL은 nominal RL policy를 safety filter로 통과시켜 catastrophic unsafe action을 막는 구조를 제안한다. URL: https://arxiv.org/html/2510.14959v1, access date: 2026-06-18.
- safety filter literature는 unsafe input을 감지하고 최소 수정해 safety를 유지하는 접근을 정리한다. URL: https://hybrid-robotics.berkeley.edu/publications/CSM2023_Safety_Filters.pdf, access date: 2026-06-18.
- residual RL은 fixed base controller 위에 제한된 residual correction을 학습해 safety/sample efficiency를 얻는 방식으로 설명된다. URL: https://arxiv.org/abs/1812.03201, access date: 2026-06-18.
- CBF/MPC 기반 legged locomotion safety work는 learned locomotion policy 위에 safety-critical planner/filter를 결합하는 방향을 제시한다. URL: https://www.roboticsproceedings.org/rss18/p033.pdf, access date: 2026-06-18.

## 2. 방법 (Method)

### 셋업
- 모델: local G1 MuJoCo model.
- teacher: exp55 best no-fall controller `com-feedback-a-blend0p50`.
- 코드: `run_safe_basis_residual_filter.py`.
- raw evidence: `verify/safe-basis-residual/`.

### 시나리오
- V0: teacher baseline을 같은 harness에서 재실행한다.
- V1: `safe_combo` residual basis를 적용한다: shallow hip/knee depth residual + stronger ankle recenter.
- V2: residual filter를 비교한다.
  - `none`: support health만 적용한 unfiltered-ish residual.
  - `soft`: support/ZMP/slip minimum health squared로 knee residual을 줄인다.
  - `zmp_hold`: support center error가 커지면 knee residual을 닫고 ankle recenter만 남긴다.

### 측정 metric
- M19 native gate: fall 없음, visible drop >=0.08m, knee >=0.60rad, hip pitch >=0.35rad, return, contact >=0.90, slip <=0.15m.
- 추가 metric: support margin, ZMP margin, foot slip, contact ratio, return height.

## 3. 결과 (Results)

### 데이터
| Run | Verdict | Filter | Drop | Knee | Hip | Contact | Slip | CoM min | ZMP min | Fell |
|-----|---------|--------|-----:|-----:|----:|--------:|-----:|--------:|--------:|------|
| teacher-best | DEPTH_PENDING | none | 0.0473m | 0.368 | 0.096 | 1.00 | 0.017m | 0.0292m | 0.0184m | never |
| unfiltered-safe-combo-r0p06 | DEPTH_PENDING | none | 0.0573m | 0.426 | 0.123 | 1.00 | 0.019m | 0.0182m | 0.0078m | never |
| soft-safe-combo-r0p06 | DEPTH_PENDING | soft | 0.0550m | 0.413 | 0.117 | 1.00 | 0.018m | 0.0207m | 0.0090m | never |
| zmp-hold-safe-combo-r0p08 | DEPTH_PENDING | zmp_hold | 0.0518m | 0.398 | 0.124 | 1.00 | 0.016m | 0.0307m | 0.0196m | never |
| zmp-hold-counter-ankle-r0p08 | DEPTH_PENDING | zmp_hold | 0.0489m | 0.378 | 0.120 | 1.00 | 0.017m | 0.0255m | 0.0155m | never |
| soft-ankle-recenter-r0p08 | DEPTH_PENDING | soft | 0.0459m | 0.364 | 0.112 | 1.00 | 0.015m | 0.0443m | 0.0344m | never |

Best no-fall run: `unfiltered-safe-combo-r0p06`, visible drop 5.73cm, contact 1.00, slip 0.019m, return true.

### 박제 위치
- `verify/safe-basis-residual/result.json`
- `verify/safe-basis-residual/safe-basis-residual-summary.md`
- `verify/safe-basis-residual/*/native-eval.json`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- safe-basis residual은 exp55 teacher의 stable depth를 4.73cm에서 5.73cm로 늘렸다. 최근 selector/residual 실험 중 no-fall/contact/slip/return을 유지한 가장 좋은 depth다.
- 하지만 아직 exp29 visible gate인 8cm와 knee/hip pose gate에는 못 미친다.
- zmp_hold filter는 margin을 더 보수적으로 지키지만 depth를 줄인다. 즉, 단순 필터는 안전을 보존하는 대신 residual을 너무 닫는다.

### 가설은 통과했나?
- [ ] PASS
- [x] PARTIAL - collapse 없이 stable depth를 늘렸지만 M19 native gate는 실패했다.

### 정의에 반영
- M19 완료 조건은 유지한다. browser replay 없이 native-only로 완료 처리하지 않는다.
- 다음 작업은 safe-basis residual을 PPO/BC fine-tune action basis로 쓰거나, WBC에서 stance foot constraint를 hard cost로 두는 쪽이다.

### 다음 실험 후보
- `safe_combo` basis를 action space로 하는 짧은 PPO/BC fine-tune: target은 5.7cm -> 8cm curriculum, termination은 support/ZMP/slip.
- torque/contact-aware WBC에서 stance foot velocity and slip을 직접 cost로 두고 pelvis height phase만 최적화한다.
