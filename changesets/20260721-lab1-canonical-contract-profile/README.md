# 20260721-lab1-canonical-contract-profile

## Target

- ROADMAP milestone: LAB1 — 카메라-행동 episode 계약.
- Plan leaf: `plans/2026-07-21-lab1-lerobot-episode-evidence.md` step-1.
- Goal: LeRobot v3 episode와 LAB provenance sidecar의 소유 필드를 분리하고 dual-camera/action/revision failure를 기계 검증한다.

## Planning Gate

```yaml
planning_gate:
  team_validation_mode: manual-pass
  scope_posture: reduction
  delegation_decision:
    remote_background_agents: skip
    reason: "공개 episode probe로 정본과 필드 경계가 고정된 단일 contract changeset이며, 표준 라이브러리 unit test로 실패 경로를 직접 검증할 수 있다."
    target_roles: []
    execution_path: local_manual
  spec_delta: "PRD와 architecture의 독자 versioned manifest 가정을 LeRobot v3 canonical episode + provenance sidecar로 교체하고 ADR 0014로 남긴다."
  perspectives:
    product: "두 카메라·state·action·instruction이 공식 viewer와 호환되는 episode로 남아야 한다."
    architecture: "canonical 시계열과 부가 provenance가 같은 필드를 중복 소유하지 않는다."
    security: "sidecar에 local path, secret, 사용자 식별 정보를 허용하지 않는다."
    qa: "공개 dual-camera profile과 정상 sidecar는 통과하고 camera/action/revision 오류는 실패해야 한다."
    skeptic: "wrist 관찰과 model input을 구분하지 않으면 과장된 증거가 되므로 role/source 선언을 강제한다."
  role_lanes:
    explorer: "공식 probe evidence와 기존 client 관측 키를 대조한다."
    planner: "LeRobot 소유 필드와 LAB sidecar 소유 필드를 분리한다."
    reviewer: "spec 충족과 sidecar 중복·과잉 검증 여부를 별도로 검토한다."
    qa: "정상 2종과 실패 fixture를 독립 실행한다."
    gate: "unit test, CLI smoke, spec diff, dirty-tree 범위를 대조한다."
  dod:
    - "LeRobot v3 dual-camera/state/action/timestamp profile이 PASS한다."
    - "정상 provenance sidecar가 revision과 camera role을 보존한다."
    - "single-camera, missing-action, invalid-revision, canonical-field duplication이 FAIL한다."
    - "CLI가 machine-readable report와 정확한 exit code를 반환한다."
```

## Scope

| File/Path | Reason | Expected effect |
|---|---|---|
| `docs/PRD.md`, `docs/ARCHITECTURE.md` | 제품·구조 계약 교정 | 독자 manifest 가정을 제거한다. |
| `docs/adr/0014-lerobot-canonical-episode-and-viewer-reuse.md` | 선택 근거 동결 | 표준 episode와 viewer 재사용 경계를 기록한다. |
| `experiments/147-camera-action-episode-contract/episode_profile.py` | 반복 가능한 profile gate | metadata와 sidecar를 machine-check한다. |
| `experiments/147-camera-action-episode-contract/test_episode_profile.py` | 정상·실패 회귀 검증 | writer 착수 전 계약 drift를 막는다. |
| `experiments/147-camera-action-episode-contract/fixtures/` | 공개·local 계약 표본 | CLI와 unit test가 같은 입력을 사용한다. |
| `experiments/147-camera-action-episode-contract/README.md` | 실행 진입점 | 검증 명령과 claim boundary를 설명한다. |

## Contract

- Source of truth: camera/state/action/timestamp/task는 LeRobot v3 episode, revision·camera role·latency·outcome은 provenance sidecar.
- Compatibility: 공개 `lerobot/libero` metadata profile과 기존 Rerun export를 유지한다.
- Deploy/operation: 로컬 Python validator다. backend·credential·public deploy가 없다.
- Out of scope: LIBERO writer, 실제 rollout, RRD 생성, LAB2 event schema, LAB3 UI.
- Cleanup: test output은 temporary directory에만 만들고 tracked fixture 외 파일을 남기지 않는다.

## Verification

- [x] Targeted unit tests: `python experiments/147-camera-action-episode-contract/test_episode_profile.py` — 7/7 PASS.
- [x] CLI surface smoke: valid strict profile exit 0, `valid=true`, 두 camera와 8D/7D shape 확인.
- [x] Negative CLI smoke: invalid policy revision exit 1, `invalid_policy_revision` 확인.
- [x] Spec/ADR review: LeRobot canonical/sidecar/Rerun/UI 선택 이식 경계가 승인 계획과 일치.
- [x] Diff/cleanup: `python -m py_compile`, `git diff --check` PASS, tracked fixture 외 임시 파일 없음.

## Result

- Status: completed 2026-07-21
- Evidence: 7개 unit fixture, valid/invalid CLI exit code, ADR 0014와 PRD/architecture diff.
- Reviewer verdict:
  - Spec: PASS — step-1의 canonical profile, revision/camera failure와 문서 교정을 충족한다.
  - Quality: PASS — validator는 LeRobot import 없이 deterministic하며 sidecar가 canonical field를 중복하지 못한다.
  - Limitation: 공개 dataset cache는 현재 로컬에 없어서 실제 metadata 재호출 대신 2026-07-21 probe에서 고정한 fixture와 raw evidence를 사용했다.
