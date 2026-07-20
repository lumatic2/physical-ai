# 20260721-lab1-libero-lerobot-writer

## Target

- ROADMAP milestone: LAB1 — 카메라-행동 episode 계약.
- Plan leaf: `plans/2026-07-21-lab1-lerobot-episode-evidence.md` step-2.
- Goal: 기존 OpenVLA+LIBERO rollout의 성공한 `env.step()`만 dual-camera LeRobot frame으로 기록하고 provenance sidecar로 raw→executed action을 연결한다.

## Planning Gate

```yaml
planning_gate:
  team_validation_mode: manual-pass
  scope_posture: selective
  delegation_decision:
    remote_background_agents: skip
    reason: "기존 client의 한 rollout 경계와 독립 writer module만 수정하며, fake backend unit test와 실제 LeRobot local smoke를 순차 실행할 수 있다."
    target_roles: []
    execution_path: local_manual
  spec_skip_reason: "ADR 0014와 step-1 spec이 writer 계약을 이미 고정했으며 이번 changeset은 그 구현이다."
  perspectives:
    product: "실행된 action과 두 camera가 같은 episode clock에 남아야 한다."
    architecture: "OpenVLA 환경은 LeRobot을 지연 import하고 dataset backend를 주입 가능하게 분리한다."
    security: "revision은 CLI에서 pinned hash만 받고 local path와 token은 sidecar에서 거부한다."
    qa: "fake backend unit test와 실제 LeRobot local dataset load를 모두 실행한다."
    skeptic: "env.step 실패 action, observer-only wrist, timestep mismatch를 성공 증거로 저장하지 않는다."
  role_lanes:
    explorer: "current LeRobot create/add_frame/save_episode/finalize API와 기존 state 집계를 대조한다."
    planner: "pre-step observation과 성공한 executed action의 commit 순서를 고정한다."
    reviewer: "client integration scope와 provenance 중복을 반박 검토한다."
    qa: "mock·official backend·failure injection을 독립 실행한다."
    gate: "writer artifact를 official LeRobot loader와 step-1 profile로 대조한다."
  dod:
    - "dual-camera 8D state/7D action frame이 official LeRobot dataset으로 저장된다."
    - "raw policy output, latency, revisions, outcome이 sidecar에 연결된다."
    - "wrist 누락, timestep 불일치, non-finite action이 저장 전에 실패한다."
    - "기존 client는 record flag가 없을 때 동작을 바꾸지 않는다."
```

## Scope

| File/Path | Reason | Expected effect |
|---|---|---|
| `experiments/147-camera-action-episode-contract/libero_writer.py` | LeRobot adapter와 sidecar emitter | producer를 official dataset API와 분리한다. |
| `experiments/147-camera-action-episode-contract/test_libero_writer.py` | 정상·실패 regression | camera/state/action contract drift를 막는다. |
| `experiments/147-camera-action-episode-contract/mock_writer_smoke.py` | official backend surface smoke | synthetic bounded episode를 실제 loader로 연다. |
| `experiments/01-vla-local-eval/client.py` | rollout integration | 성공한 env action만 writer에 commit한다. |
| experiment README | 설치·실행·공식 출처 | 재현 경로를 남긴다. |

## Contract

- Source of truth: successful `env.step()` 직전 observation + 실제 전달한 7D action이 canonical LeRobot frame이다.
- Provenance: raw policy output, latency, pinned revision, camera role, outcome과 executed-action hash만 sidecar가 소유한다.
- Compatibility: record flags가 없으면 기존 evaluator 결과와 REST path가 유지된다.
- Deploy/operation: OpenVLA env에서 LeRobot import는 record mode에서만 발생한다. official backend smoke는 기존 viewer-probe venv를 사용한다.
- Out of scope: 실제 GPU rollout, Rerun export, canonical PASS/FAIL pair, LAB2 event schema.
- Official API sources: [LeRobot dataset source](https://github.com/huggingface/lerobot/blob/main/src/lerobot/datasets/lerobot_dataset.py), [feature utility](https://github.com/huggingface/lerobot/blob/main/src/lerobot/utils/feature_utils.py) (접근일 2026-07-21).

## Verification

- [x] Targeted unit tests: profile 7/7, writer 6/6 PASS; wrist·shape·non-finite·timestep mismatch를 저장 전에 거부.
- [x] Client compile/compatibility: `client.py`, writer, smoke module `py_compile` PASS; record mode에서만 LeRobot을 지연 import.
- [x] Official backend smoke: synthetic 3-frame dual-camera dataset create/save/finalize/load PASS, PyAV로 두 video를 다시 읽음.
- [x] Profile/negative smoke: generated info+sidecar strict PASS, injected mismatch/non-finite action FAIL.
- [x] Diff/cleanup: `git diff --check` PASS, smoke process 0개, temporary dataset는 ignored `tmp/`에만 존재.

## Result

- Status: completed 2026-07-21
- Correction evidence: step-1 changeset의 “public cache 부재” 메모는 부정확했다. `tmp/lab1-viewer-probe/dataset/meta/info.json`을 실제 재검사했고 profile PASS했다. 이 changeset이 그 정정 기록을 supersede한다.
- Evidence: `experiments/147-camera-action-episode-contract/verify/writer-smoke.json` — frames=3, camera=2, state=8D, action=7D, strict profile PASS.
- Near miss: Windows two-camera parallel encoding이 child process를 남겨 timeout됐다. 정확한 smoke process만 종료하고 official `parallel_encoding=False` 경로로 고정해 재검증했다.
- Reviewer verdict:
  - Spec: PASS — 성공한 env action만 pre-step observation과 묶고 raw output은 sidecar에 분리한다.
  - Quality: PASS — fake backend 회귀와 actual LeRobot loader smoke가 같은 adapter를 검증한다.
