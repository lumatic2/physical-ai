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
- `audit_reference.py`
  - staged reference가 실제 foot-contact preserving squat target인지 기하적으로 검사한다.
  - raw reference scale sweep으로 stage 0.74에 필요한 calibrated reference scale을 찾는다.
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
| attempt-003-pose-prior-10k | DEPTH_PENDING | local WSL/JAX PPO + native MuJoCo / ~5.5min | 0 | pose_prior/height_push 추가, contact 1.00 유지하나 min height 0.7495m로 악화 |
| attempt-004-action-target-10k | DEPTH_PENDING | local WSL/JAX PPO + native MuJoCo / ~5.5min | 0 | action_target 추가, contact 1.00 유지하나 min height 0.7493m로 gate 미달 |
| attempt-005-source-controller-blend-0p18 | CONTACT_GATE_PENDING | native MuJoCo / 6.0s | 0 | controller blend가 depth/hold를 만들지만 contact 0.73, slip 1.63m |
| attempt-006-controller-blend-0p18-10k | CONTACT_GATE_PENDING | local WSL/JAX PPO + native MuJoCo / ~7.3min | 0 | blend controller에서 residual fine-tune해도 contact 0.72, slip 1.69m |
| attempt-007-source-blend-0p18-freeze-phase | DEPTH_PENDING | native MuJoCo / 6.0s | 0 | freeze phase로 contact 1.00/slip 0.012m, 그러나 min height 0.7491m |
| attempt-008-source-blend-0p35-freeze-phase | FAIL_FALL | native MuJoCo / 6.0s | 0 | freeze phase에서 큰 blend는 2.16s fall |
| attempt-009-source-blend-0p25-freeze-phase | FAIL_FALL | native MuJoCo / 6.0s | 0 | 중간 blend도 4.40s fall |
| attempt-010-source-blend-0p20-freeze-phase | DEPTH_PENDING | native MuJoCo / 6.0s | 0 | contact 1.00/slip 0.012m 유지, depth는 0.7490m에서 정체 |
| attempt-011-squat-schedule-0p25-freeze-phase | DEPTH_PENDING | native MuJoCo / 6.0s | 0 | descent/hold/return blend schedule, contact 1.00/slip 0.012m이나 min height 0.7484m |
| attempt-012-squat-schedule-0p35-freeze-phase | FAIL_FALL | native MuJoCo / 6.0s | 0 | stronger schedule은 depth를 만들지만 3.76s fall |
| attempt-013-reference-audit | REFERENCE_GATE_FAIL | native MuJoCo geometry audit | 0 | staged reference는 declared 0.740m이지만 foot-anchored height 0.7532m라 실제로는 거의 서 있는 포즈 |
| attempt-014-refscale-0p75-blend-0p05-freeze-schedule | DEPTH_PENDING | native MuJoCo / 6.0s | 0 | raw reference 0.75 scale + weak blend, contact 1.00이나 min height 0.7496m |
| attempt-015-refscale-0p75-blend-0p15-freeze-schedule | DEPTH_PENDING | native MuJoCo / 6.0s | 0 | calibrated reference가 depth를 늘렸지만 min height 0.7480m |
| attempt-016-refscale-0p75-blend-0p30-freeze-schedule | DEPTH_PENDING | native MuJoCo / 6.0s | 0 | no-fall/contact 1.00, min height 0.7456m로 gate 직전 |
| attempt-017-refscale-0p75-blend-0p35-freeze-schedule | PASS_CONTROLLED_SQUAT | native MuJoCo / 6.0s | 0 | no-fall, min height 0.7446m, hold 1.32s, contact 1.00 |
| attempt-018-web-replay-record | PASS_CONTROLLED_SQUAT | native MuJoCo / 6.0s + web replay QA | 0 | attempt-017 controller를 50Hz qpos trajectory로 기록하고 `g1-controlled-squat` replay QA PASS |

### best gate
| Metric | Best | Gate | 상태 |
|---|---:|---:|---|
| fell_at | None | None | PASS |
| min_height | 0.7446 | <= 0.745 | PASS |
| hold_duration | 1.32s | >= 0.50s | PASS |
| final_height | 0.7497 | >= 0.740 | PASS |
| foot_contact_ratio | 1.00 | >= 0.90 | PASS |
| joint_limit_violation | 0.0000 | <= 0.05 | PASS |

### 박제 위치
- `verify/stage-0p74/attempts/attempt-001-source-baseline/result.json`
- `verify/stage-0p74/attempts/attempt-002-contact-aware-10k/result.json`
- `verify/stage-0p74/attempts/attempt-003-pose-prior-10k/result.json`
- `verify/stage-0p74/attempts/attempt-004-action-target-10k/result.json`
- `verify/stage-0p74/attempts/attempt-005-source-controller-blend-0p18/result.json`
- `verify/stage-0p74/attempts/attempt-006-controller-blend-0p18-10k/result.json`
- `verify/stage-0p74/attempts/attempt-007-source-blend-0p18-freeze-phase/result.json`
- `verify/stage-0p74/attempts/attempt-008-source-blend-0p35-freeze-phase/result.json`
- `verify/stage-0p74/attempts/attempt-009-source-blend-0p25-freeze-phase/result.json`
- `verify/stage-0p74/attempts/attempt-010-source-blend-0p20-freeze-phase/result.json`
- `verify/stage-0p74/attempts/attempt-011-squat-schedule-0p25-freeze-phase/result.json`
- `verify/stage-0p74/attempts/attempt-012-squat-schedule-0p35-freeze-phase/result.json`
- `verify/stage-0p74/attempts/attempt-013-reference-audit/result.json`
- `verify/stage-0p74/attempts/attempt-013-reference-audit/reference-audit.md`
- `verify/stage-0p74/attempts/attempt-014-refscale-0p75-blend-0p05-freeze-schedule/result.json`
- `verify/stage-0p74/attempts/attempt-015-refscale-0p75-blend-0p15-freeze-schedule/result.json`
- `verify/stage-0p74/attempts/attempt-016-refscale-0p75-blend-0p30-freeze-schedule/result.json`
- `verify/stage-0p74/attempts/attempt-017-refscale-0p75-blend-0p35-freeze-schedule/result.json`
- `verify/stage-0p74/attempts/attempt-018-web-replay-record/result.json`
- `../03-digital-twin/g1_controlled_squat_trajectory.json`
- `verify/stage-0p74/best.json`
- `verify/stage-0p74/summary.md`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- exp28 runner는 `stage 0.74 controlled squat PASS`를 단일 experiment 내부 attempt loop로 다룬다. 이제 다음 시도들은 새 exp가 아니라 exp28의 attempt로 누적하면 된다.
- contact-aware reward는 안정성과 foot contact를 보존했다. attempt-002는 6초 no-fall, foot contact ratio 1.00, joint violation 0.0이다.
- 하지만 depth는 아직 부족하다. attempt-002의 min height는 0.7489m로 gate 0.745m에 못 미치고, hold duration도 0.0s다.
- attempt-003에서 pose_prior/height_push를 추가했지만 min height가 0.7495m로 오히려 나빠졌다. reward만 추가하는 방식은 source policy의 standing attractor를 충분히 깨지 못한다.
- attempt-004에서 action_target 보상을 추가해도 min height는 0.7493m에 머물렀다. 짧은 PPO fine-tune의 reward shaping만으로는 exp27의 blend controller가 만든 0.741m depth를 재현하지 못한다.
- controller blend 0.18은 depth/hold를 만들지만 contact 0.73과 foot slip 1.63m로 gate를 못 닫는다. 같은 blend에서 10k residual fine-tune을 해도 contact는 0.72로 회복되지 않았다.
- freeze phase는 contact와 slip 병목을 거의 제거한다. `blend_0p18~0p20 + freeze_phase`는 contact 1.00, slip 0.012m를 유지한다.
- 하지만 freeze phase는 depth를 0.749m 근처에서 막는다. blend를 0.25~0.35로 키우면 깊이는 생기지만 fall한다. 즉 현재 병목은 `phase/contact/depth` 세 항의 동시 controller 설계다.
- squat-specific blend schedule도 같은 trade-off를 보였다. 0.25 schedule은 안정적이지만 shallow, 0.35 schedule은 depth를 만들지만 fall한다.
- exp27의 moving-phase blend는 depth를 만들지만 contact를 잃고, freeze-phase blend는 contact를 보존하지만 depth를 잃는다. 단순 reward/fine-tune보다 squat 전용 reference/controller가 필요하다.
- reference audit에서 핵심 원인을 찾았다. 기존 staged reference는 declared target이 0.740m여도 foot-anchored base height가 0.7532m라 실제 관절 포즈는 stage depth를 만들지 못한다.
- raw reference scale sweep상 0.75 scale은 foot-anchored min height 0.7422m, foot XY drift 0.0077m, joint violation 0.0으로 stage 0.74에 맞는 calibrated target이다.
- `reference_scale=0.75`, `freeze_phase`, squat blend schedule, `controller_blend=0.35` 조합은 native 6초 gate를 통과했다. 결과: no-fall, min height 0.7446m, hold 1.32s, return true, contact 1.00, joint violation 0.0.
- 같은 controller rollout을 50Hz qpos trajectory로 기록해 browser replay artifact로 연결했다. local visual QA는 `?exp=g1-controlled-squat` replay mode, 300 frames, console errors 0으로 PASS했다.

### 가설은 통과했나?
- [x] PASS — stage 0.74 controlled squat gate를 모두 통과한다.
- [ ] FAIL_PARTIAL — attempt loop와 contact-aware training path는 열렸지만, 첫 fine-tune은 depth gate 미달이다.

### 정의에 반영
- M19의 stage 0.74 depth/contact gate와 browser replay packaging은 닫혔다. 다만 이 산출물은 learned residual policy가 아니라 stabilizer policy + calibrated reference controller다.
- 다음 M19 작업은 같은 calibrated reference를 reward/prior로 넣어 residual policy로 증류하거나, 더 낮은 stage height로 curriculum을 확장하는 것이다.

### 다음 attempt 후보
- exp28 후속은 learned-policy packaging 여부를 결정하는 integration step이다. 현재 웹에는 `g1-controlled-squat` replay로 노출된다.
