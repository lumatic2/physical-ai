# 20260721-lab1-canonical-pass-fail-pair

## Target

- ROADMAP milestone: LAB1 — 카메라-행동 episode 계약.
- Plan leaf: `plans/2026-07-21-lab1-lerobot-episode-evidence.md` step-4.
- Goal: 동일 task·seed·OpenVLA/LIBERO revision에서 init-state만 다른 실제 PASS·FAIL episode를 각각 canonical LeRobot dataset과 RRD로 보존한다. 기술 선택은 현재 pinned runtime의 실제 outcome을 따르며 과거 label을 재사용하지 않는다.

## Planning Gate

```yaml
planning_gate:
  team_validation_mode: manual-pass
  scope_posture: selective
  delegation_decision:
    remote_background_agents: skip
    reason: "한 GPU server가 두 고정 init-state rollout을 순차 실행해야 하며 dataset/video writer 병렬화는 충돌 위험만 늘린다."
    target_roles: []
    execution_path: local_manual
  spec_skip_reason: "승인 plan과 ADR 0014가 pair의 canonical format, outcome, claim boundary를 이미 고정했다."
  perspectives:
    product: "사람이 같은 지시에서 성공과 실패의 카메라·행동 차이를 나란히 재생할 수 있어야 한다."
    architecture: "PASS와 FAIL은 독립 LeRobot dataset이고 pair report가 공통 contract와 hash를 묶는다."
    security: "공개 evidence에 절대 로컬 경로·token을 넣지 않는다."
    qa: "outcome relabel, revision/seed/task drift, raw→executed action 연결 누락을 거부한다."
    skeptic: "bounded 실패를 과제 실패로 둔갑시키지 않고 full-horizon timeout만 canonical FAIL로 인정한다."
  role_lanes:
    explorer: "기존 500-episode 분포를 출발점으로 current runtime에서 같은 task의 PASS와 FAIL init-state를 실제 탐색한다."
    planner: "한 pinned server에서 PASS/FAIL client를 순차 실행하고 별도 dataset으로 finalize한다."
    reviewer: "두 episode가 init-state 외 동일 contract인지 대조한다."
    qa: "official loader/profile/RRD/pair gate와 outcome relabel failure를 실행한다."
    gate: "dataset/sidecar/RRD hash와 실제 success/timeout outcome을 최종 대조한다."
  dod:
    - "동일 task·seed·policy/environment revision의 PASS와 FAIL dataset이 각각 strict profile을 통과한다."
    - "PASS는 success termination, FAIL은 full-horizon timeout이며 둘 다 raw→executed action 연결이 있다."
    - "두 official RRD가 main/wrist/state/action timeline을 제공한다."
    - "pair report가 revision·seed·task·hash drift와 outcome relabel을 실패시킨다."
```

## Scope

| File/Path | Reason | Expected effect |
|---|---|---|
| `experiments/01-vla-local-eval/client.py`, `run.py` | init-state offset와 rollout provenance | PASS/FAIL 초기 상태를 독립 재현한다. |
| `experiments/147-camera-action-episode-contract/libero_writer.py` | seed/task/init-state/full-horizon sidecar | 결과 relabel과 contract drift를 검증 가능하게 한다. |
| `experiments/147-camera-action-episode-contract/verify_canonical_pair.py`, test | pair gate | 공통 contract와 상반 outcome을 기계 판정한다. |
| `experiments/147-camera-action-episode-contract/verify/canonical/` | canonical pair와 RRD | LAB2/LAB3 입력 정본을 만든다. |

## Contract

- Source of truth: PASS와 FAIL 각각의 LeRobot v3 dataset; pair report는 hash와 공통 contract만 소유한다.
- Compatibility: record flag가 없으면 기존 evaluator 동작을 유지하고 trial offset 기본값은 0이다.
- Provenance: suite, task id, init-state index, seed, full max-policy-steps와 pinned revisions를 sidecar에 둔다.
- Deploy/operation: WSL OpenVLA server 1개에 두 client를 순차 실행하고 official Windows viewer로 RRD를 파생한다.
- Out of scope: 모델 비교, causal event 설명, 공개 UI, 실물/live claim.

## Verification

- [x] Producer pair: task 5의 init-state 0 PASS, init-state 1 full-horizon FAIL recording PASS.
- [x] Dataset pair: strict profile와 official loader에서 camera/state/action/outcome PASS.
- [x] Rerun pair: 두 RRD verify와 entity/timeline PASS.
- [x] Negative pair gate: relabel/revision/seed/task drift와 action link 누락 FAIL.
- [x] Cleanup/integration: process 0, 전체 LAB1 tests와 `git diff --check` PASS.

## Result

- Status: completed
- Canonical pair: LIBERO Spatial task 5, seed 0, max policy steps 220.
- PASS: init-state 0, success termination, 78 frames.
- FAIL: init-state 1, timeout termination, 220 frames.
- Policy revision: `962318cec55ac10993ff0f5f43eda9a270b4c873`.
- Environment revision: `8f1084e3132a39270c3a13ebe37270a43ece2a01`.
- Pair report: `experiments/147-camera-action-episode-contract/verify/canonical/pair-report.json`.
- 탐색 메모: 과거 분포에서 후보였던 task 0은 현재 pinned runtime의 init-state 0~9가 모두 성공했다. 과거 label을 재사용하지 않고 current runtime에서 실제 상반 outcome이 나온 task 5를 선택했다.
