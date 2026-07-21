# HORIZON — 시뮬레이션과 실물을 잇는 SO-101 검증

> 생성: 2026-07-21 · 연쇄: 3/3 · 상태: queued-approved · 외부 hardware gate

## 목표

- SO-101의 front/wrist camera, joint state, teleop/action, ACT policy outcome과 safety event를 simulation evidence와 같은 상위 계약으로 관찰·평가한다.
- Objective의 **시뮬레이션에서 실물로** 축을 실제 consumer hardware evidence로 처음 전진시킨다.
- **무감독 분량: ≥25 changeset 상당** — REAL1~REAL5 각 5 step/changeset 합계다.

## 왜 지금

- 앞 두 Horizon이 task/policy/session/recording 계약을 고정하면 real hardware에 새 viewer나 schema를 발명할 필요가 없다.
- 실물 축은 현재 Objective의 가장 큰 미충족 항목이지만 구매·공간·안전은 코드 승인과 분리해야 한다.

## 범위

- 포함: SO-101 leader/follower, front+wrist camera, physical stop, calibration/teleop, 50 episode dataset, ACT training, 30 real eval, sim analogue와 public evidence comparison.
- 제외: 자동 구매, 무감독 실물 실행, SmolVLA/HIL 필수화, sim-real physics 동일성 주장, 원격 public robot control.
- 실행 모드: `continuous`; 단 REAL1 시작 전 사용자의 hardware acquisition 승인 필수.

## 담을 Milestone — 설계 번들 인덱스

| Milestone | 제목 | plan doc | 승인 | 리서치 입력 |
|---|---|---|---|---|
| **REAL1** | SO-101 획득·안전 준비 | `plans/2026-07-21-real1-so101-acquisition-safety.md` | pending chain + hardware gate | `research/2026-07-21-sim-real-so101-evidence-loop.md` |
| **REAL2** | 보정된 dual-camera teleoperation | `plans/2026-07-21-real2-calibrated-teleoperation.md` | pending chain approval | REAL1 + LeRobot docs |
| **REAL3** | 실물 dataset과 sim 대응 과제 | `plans/2026-07-21-real3-real-dataset-sim-analogue.md` | pending chain approval | REAL2 |
| **REAL4** | ACT 학습과 실물 평가 | `plans/2026-07-21-real4-act-training-real-evaluation.md` | pending chain approval | REAL3 |
| **REAL5** | sim-real 증거 비교와 공개 검토 | `plans/2026-07-21-real5-sim-real-public-evidence.md` | pending chain approval | REAL1~REAL4 |

## 닫는 기준

- hardware identity, calibration revision, camera roles, physical stop과 workspace safety gate가 PASS한다.
- 50 teleop episode가 dual-camera/state/action/timestamp/task/outcome 계약과 quality audit를 통과한다.
- sim analogue와 real task가 공유 task/result schema와 다른 claim level을 명시한다.
- ACT가 unseen-condition 30 episode에서 safety event·intervention·success/failure를 모두 기록한다.
- public comparison에서 sim/real evidence를 동일 화면에서 보되 physics·performance 동치 claim fixture가 거부된다.

## 미리 쓰는 실패 회고

- **구매·배송·공간이 준비되지 않아 전체 연쇄가 묶였다.** → REAL1은 별도 external gate이며 앞 두 Horizon 완료를 방해하지 않는다.
- **캘리브레이션과 camera 품질이 낮아 model 문제가 아닌 data 문제가 됐다.** → REAL2 quality gate 전 dataset recording을 금지한다.
- **성공 영상 몇 개를 실물 성능으로 과장했다.** → REAL4는 30 episode denominator와 모든 실패/safety event를 의무화한다.
- **sim과 real 성공률을 직접 비교해 디지털 트윈을 과장했다.** → REAL3/5는 schema coverage만 비교하고 claim negative fixture를 둔다.

## 결정 로그

- status: resolved
- SO-101 leader/follower + front/wrist camera를 hardware 기준으로 한다.
- 첫 dataset 50 episode, ACT real eval 30 episode로 고정한다.
- 실제 구매는 별도 사용자 승인 없이는 진행하지 않는다.

## 링크

- 위: `OBJECTIVE.md`
- 연쇄: `plans/horizons/CANDIDATES.md`
- 리서치: `research/2026-07-21-sim-real-so101-evidence-loop.md`
- 결정: `docs/adr/0017-so101-real-evidence-and-safety-boundary.md`
