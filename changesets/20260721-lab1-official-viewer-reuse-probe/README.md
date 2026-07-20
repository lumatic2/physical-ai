# 20260721-lab1-official-viewer-reuse-probe

## Target

- Goal: 공개 LeRobot dual-camera episode를 공식 관찰 도구와 웹 UI에서 실제로 열어, LAB1–LAB3가 새로 만들지 않아도 되는 범위를 측정한다.
- ROADMAP milestone: LAB1 — 카메라-행동 episode 계약.
- Scale: 단일 changeset/experiment probe. 새 Milestone이나 공개 UI 구현은 만들지 않는다.

## Planning Gate

```yaml
planning_gate:
  team_validation_mode: manual-pass
  scope_posture: selective
  delegation_decision:
    remote_background_agents: skip
    reason: "공개 dataset 1개와 공식 viewer 3개를 순차 검증하는 단일 experiment이며, shared workspace 병렬 수정 이득보다 환경·다운로드 충돌 위험이 크다."
    target_roles: []
    execution_path: local_manual
  spec_delta: "측정 결과로 LAB1-LAB3 승인 계획의 후속 addendum에서 custom trace/UI 범위를 축소한다. 기존 승인 plan은 수정하지 않는다."
  perspectives:
    product: "dual-camera, instruction, action/state graph가 사용자 화면에서 실제로 읽히는지 본다."
    architecture: "LeRobot episode를 정본 후보로 두고 Rerun/Foxglove/web artifact를 derived viewer로 판정한다."
    security: "공개 dataset만 사용하고 token과 private Hub data는 사용하지 않는다."
    qa: "dataset contract, Rerun artifact, Foxglove channel, 실제 browser UI를 각각 검증한다."
    skeptic: "README상 지원과 실제 동작이 다르거나 dual-camera가 동기화되지 않을 가능성을 failure probe로 확인한다."
  role_lanes:
    explorer: "공개 dual-camera dataset과 공식 실행 경로를 확인한다."
    planner: "probe 결과를 reuse/adapt/reject로 분류한다."
    reviewer: "README claim이 아니라 raw output과 browser surface를 대조한다."
    qa: "happy path와 single-camera/missing-field failure를 확인한다."
    gate: "5개 verification과 evidence 파일을 대조한다."
  dod:
    - "공개 LIBERO dual-camera episode metadata와 실제 frame/action/state를 확인한다."
    - "공식 Rerun export가 생성되고 camera/state/action timeline entity를 포함한다."
    - "공식 Foxglove adapter가 같은 episode의 image/state/action channel을 광고한다."
    - "공식 Dataset Visualizer를 실제 브라우저에서 열어 dual-camera/video, instruction, graph, scrub surface를 확인한다."
    - "single-camera 또는 필수 field 누락 fixture가 재사용 gate에서 거부된다."
```

## Scope

| File/Path | Reason | Expected effect |
|---|---|---|
| `experiments/147-camera-action-episode-contract/probe_official_viewers.py` | dataset/viewer contract를 반복 가능하게 검사 | README 판단이 아니라 machine-readable reuse report를 만든다. |
| `experiments/147-camera-action-episode-contract/probe_foxglove_channels.py` | Foxglove SDK 서버 광고를 직접 검사 | 로그인 여부와 무관하게 channel·재생 capability를 검증한다. |
| `experiments/147-camera-action-episode-contract/verify/official-viewer-reuse/` | raw metadata, command output, screenshot, summary 보존 | LAB 계획 축소의 근거가 남는다. |
| `plans/2026-07-21-lab1-official-viewer-reuse-addendum.md` | probe 결과를 후속 실행안으로 번역 | 승인된 기존 plan을 보존하면서 중복 구현을 제거한다. |
| `changesets/20260721-lab1-official-viewer-reuse-probe/README.md` | 실행·검증 장부 | 5개 gate의 상태와 판정을 추적한다. |

## Contract

- Source of truth: 공개 `lerobot/libero` LeRobot v3 episode와 현재 LeRobot 공식 viewer code.
- Verify target: Rerun `.rrd`, Foxglove WebSocket channel advertisement, LeRobot Dataset Visualizer browser surface.
- Compatibility: existing `experiments/01-vla-local-eval`와 공개 Robotics Lab 코드는 read-only다.
- Deploy/operation: 로컬 probe만 수행한다. public site 배포는 LAB3 소유다.
- Out of scope: custom trace schema, VLA inference 재실행, UI fork/이식, persistent backend.

## Evidence Contract

- Dataset: `lerobot/libero`, episode 0, main `observation.images.image`, wrist `observation.images.image2`.
- Required signals: two camera keys, state, action, timestamp, task/instruction metadata.
- Failure mode: camera key가 1개이거나 action/state/timestamp가 없으면 `reusable=false`.
- Cleanup: local viewer/web processes 종료, dependency cache와 dataset은 ignored temp/cache에만 둔다.
- Not evidence: recorded public dataset 재생은 이 레포의 VLA 실행 성공이나 live inference 증거가 아니다.

## Verification

- [x] Dataset contract: dual-camera/state/action/instruction metadata와 episode sample 확인.
- [x] Rerun surface: official export 생성·entity/timeline 검사와 viewer smoke.
- [x] Foxglove surface: seekable server의 camera/state/action channels 확인.
- [x] Web UI surface: 공식 Dataset Visualizer 실제 브라우저 smoke와 screenshot.
- [x] Failure/cleanup/drift: missing-camera fixture FAIL, 프로세스 정리, dirty-tree 범위 확인.

## Result

- Status: completed 2026-07-21
- Evidence: `experiments/147-camera-action-episode-contract/verify/official-viewer-reuse/README.md`
- Reuse decision:
  - LeRobot v3 episode = canonical LAB1 format.
  - Rerun = immediate internal replay/debug viewer.
  - Foxglove = optional developer channel diagnostic; Web UI integration excluded because sign-in is required.
  - LeRobot Dataset Visualizer = synchronized video/playback/chart interaction을 선택 이식; whole-app vendoring은 local Recharts failure 때문에 보류.
  - Proposed plan delta = `plans/2026-07-21-lab1-official-viewer-reuse-addendum.md` (사용자 승인 대기).
- Verification:
  - unit tests 3/3 PASS; valid, single-camera reject, missing-action reject.
  - official RRD verify PASS; 5 entity paths, 857 rows, 4 sorted timelines.
  - Foxglove required topics 4/4 + playback/time capabilities PASS.
  - deployed Dataset Visualizer: 2 videos, instruction, state/action graph, seek/pause PASS.
  - ports 9090/9876/8765/3017 listener count 0 after cleanup.
