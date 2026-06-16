# 28-g1-controlled-squat-stage0p74 — controlled G1 squat stage 0.74

> M19k. exp26/27에서 stage 0.74 depth corridor는 찾았지만 contact gate가 남았다. 이번 실험은 exp 단위를 더 쪼개지 않고, `stage 0.74 controlled squat PASS`를 목표로 attempts를 누적한다.

## 1. 가설 (Hypothesis)

exp22 stabilizer policy에서 시작해 stage 0.74 contact-aware reward로 짧은 PPO fine-tune을 반복하면, G1은 native MuJoCo에서 6초 동안 fall 없이 stage 0.74 squat를 양발 접촉을 유지하며 수행할 수 있다.

PASS 기준:
- `fell_at is None`
- `min_height <= 0.745`
- `hold_duration_at_or_below_stage >= 0.5`
- `final_height >= 0.74`
- `foot_contact_ratio >= 0.90`
- `max_joint_limit_violation <= 0.05`

반증 기준:
- reward/env smoke가 실패한다.
- source params와 target policy shape가 맞지 않는다.
- contact-aware reward가 depth를 standing attractor로 되돌린다.
- depth는 만들지만 foot contact 0.90을 반복적으로 못 넘는다.

## 2. 방법 (Method)

planning_gate:
  team_validation_mode: manual-pass
  spec_delta: "M19 staged depth curriculum/controller redesign을 exp28 stage 0.74 controlled squat PASS 실험으로 수렴시킨다."
  perspectives:
    product: "목표를 '다음 exp'가 아니라 stage 0.74 controlled squat acceptance gate로 고정한다."
    architecture: "exp25 env/source params를 재사용하되 exp28 안에 attempts/best evidence를 누적한다."
    security: "secret, network, 외부 권한 없음. 로컬 WSL/JAX/MuJoCo만 사용한다."
    qa: "py_compile, smoke, native eval, train attempt output을 verify/stage-0p74에 보존한다."
    skeptic: "짧은 PPO로 gate가 닫히지 않을 수 있으므로 실패도 next reward direction으로 남긴다."
  dod:
    - "attempt runner가 compatibility/smoke/native eval을 실행한다."
    - "verify/stage-0p74/attempts/<attempt>/result.json 생성"
    - "best.json과 summary.md가 현재 best gate 상태를 보여준다."

### 실험 구조
- `run_controlled_squat.py`
  - exp25 `G1SquatCurriculum`을 contact-aware reward config로 실행한다.
  - source params는 exp22, 없으면 exp21을 사용한다.
  - `--train`이 없으면 source policy native baseline만 평가한다.
  - `--train`이면 attempt 폴더에 params/rewards/native 결과를 저장한다.
- `verify/stage-0p74/attempts/attempt-*/result.json`
- `verify/stage-0p74/best.json`
- `verify/stage-0p74/summary.md`

### acceptance gate
exp24/25/27에서 확정한 controlled squat gate를 그대로 쓴다. stage 0.74가 PASS하기 전에는 0.72로 내려가지 않는다.

## 3. 결과 (Results)

### 데이터
| Run | Verdict | Cost | Retries | 비고 |
|-----|---------|------|---------|------|
| py_compile | PASS | local Python | 0 | runner syntax/import 확인 |
| attempt-001-source-baseline | DEPTH_PENDING | local WSL/JAX + native MuJoCo / 6.0s | 0 | source policy: no-fall/contact 1.00, min height 0.7501m |
| attempt-002-contact-aware-10k | DEPTH_PENDING | local WSL/JAX PPO + native MuJoCo / ~6.9min | 1 | 첫 run은 metric shape mismatch로 실패, reset metric 추가 후 재실행 |

### best gate
| Metric | Best | Gate | 상태 |
|---|---:|---:|---|
| fell_at | None | None | PASS |
| min_height | 0.7489 | <= 0.745 | FAIL |
| hold_duration | 0.00s | >= 0.50s | FAIL |
| final_height | 0.7501 | >= 0.740 | PASS |
| foot_contact_ratio | 1.00 | >= 0.90 | PASS |
| joint_limit_violation | 0.0000 | <= 0.05 | PASS |

### 박제 위치
- `verify/stage-0p74/attempts/attempt-001-source-baseline/result.json`
- `verify/stage-0p74/attempts/attempt-002-contact-aware-10k/result.json`
- `verify/stage-0p74/best.json`
- `verify/stage-0p74/summary.md`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- exp28 runner는 `stage 0.74 controlled squat PASS`를 단일 experiment 내부 attempt loop로 다룬다. 이제 다음 시도들은 새 exp가 아니라 exp28의 attempt로 누적하면 된다.
- contact-aware reward는 안정성과 foot contact를 보존했다. attempt-002는 6초 no-fall, foot contact ratio 1.00, joint violation 0.0이다.
- 하지만 depth는 아직 부족하다. attempt-002의 min height는 0.7489m로 gate 0.745m에 못 미치고, hold duration도 0.0s다.
- exp27의 controller blend는 depth를 만들지만 contact를 잃었고, exp28 contact-aware reward는 contact를 보존하지만 depth를 잃었다. 다음 attempt는 이 둘을 결합해야 한다.

### 가설은 통과했나?
- [ ] PASS — stage 0.74 controlled squat gate를 모두 통과한다.
- [x] FAIL_PARTIAL — attempt loop와 contact-aware training path는 열렸지만, 첫 fine-tune은 depth gate 미달이다.

### 정의에 반영
- M19는 아직 완료가 아니다. 다음 작업은 `blend_0p18~0p22` corridor를 reward target/behavior prior로 넣으면서 contact-aware reward를 유지하는 exp28 attempt다.

### 다음 attempt 후보
- attempt-003: policy-only action에 맡기지 말고 `blend_0p18~0p20` staged pose prior를 reward 또는 action target으로 명시한다.
- contact 1.00을 유지하면서 min height를 0.745m 아래로 낮추는 것이 다음 단일 목표다.
