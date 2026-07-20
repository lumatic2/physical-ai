# PLAN — LAB1 LeRobot episode 증거

Status: approved 2026-07-21 — Horizon 전체 연쇄 실행 승인
Supersedes: `plans/2026-07-20-lab1-camera-action-episode-contract.md`, `plans/2026-07-21-lab1-official-viewer-reuse-addendum.md`

> 공식 viewer 재사용 probe를 반영한 LAB1 후속 실행안이다. 이전 승인안과 addendum은 결정 이력으로 보존한다.

## 북극성 → Horizon → Milestone → Step

- **북극성**: 카메라와 센서로 세상을 보고, 언어 지시를 이해하고, 로봇 행동을 생성·실행하며, 그 전 과정을 사람이 관찰할 수 있는 피지컬 AI 실험실. (← `OBJECTIVE.md`)
- **Horizon**: 보고 판단하고 움직이는 로봇팔 실험실. (← `plans/horizons/see-understand-act-robot-lab.md`)
- **Milestone**: 기존 OpenVLA+LIBERO 실행을 LeRobot v3 episode와 재현 가능한 PASS/FAIL 증거로 바꾸는 LAB1.
- **리서치 입력**: `experiments/147-camera-action-episode-contract/verify/official-viewer-reuse/README.md`.

## Scope Boundary

- 결정: 기존에 성공한 OpenVLA+LIBERO 단일 과제에서 dual camera, robot state, executed action, instruction, timestamp를 LeRobot v3 episode로 기록하고, 정책·환경 revision과 결과처럼 표준 필드 밖의 사실만 provenance sidecar에 둔다.
- 포함: feature profile validator, LIBERO writer, 동일 조건 PASS/FAIL pair, 공식 Rerun export.
- 제외: SmolVLA 비교, VLM 설명 event, 공개 브라우저 UI, 실물 로봇, 새 episode 포맷.
- Execution mode: `continuous`
- Stop only: completed, blocked, decision_required, risk_gate, secret_required, external_authority_required, user_stopped.
- Rollback/cleanup: 각 changeset을 독립 revert할 수 있게 하고, WSL2·CUDA·LIBERO child process와 임시 video/RRD를 종료·삭제한다. canonical evidence는 검증을 통과한 뒤에만 보존한다.

## planning_gate

- team_validation_mode: `manual-pass`
- scope_posture: `reduction` — 새 포맷과 전체 viewer fork를 제거하고 검증된 표준 경로만 남긴다.
- delegation_decision: `skip` — 사전 probe와 코드 경계가 이미 로컬 증거로 고정됐고, 이 계획 단계는 공유 작업공간 병렬 편집의 이득보다 충돌 위험이 크다.
- spec_delta: `physical-ai-arm-episode-v1` 가정을 LeRobot v3 canonical episode + provenance sidecar로 교체하고 ADR 0014에 기록한다. Objective 문구는 바꾸지 않는다.
- product: 첫 산출물만으로도 카메라·상태·지시·행동·결과가 같은 episode에서 재생돼야 한다.
- architecture: LeRobot episode가 시계열 정본이고 sidecar는 표준 필드를 중복하지 않는 파생 메타데이터다.
- security: 로컬 경로·토큰·사용자 정보는 episode와 공개 후보 asset에 포함하지 않는다.
- qa: 정상 fixture뿐 아니라 카메라 누락, timestep 불일치, 비유한 action, 결과 relabel을 실패시킨다.
- skeptic: writer가 데이터를 만들었다는 사실과 정책이 실제로 사용한 입력을 구분하고, wrist camera를 model input으로 과장하지 않는다.

## 스캐폴딩 결정

- source-of-truth: LeRobot v3 episode의 feature metadata와 frame index가 시계열 정본이고, LAB provenance sidecar는 revision·latency·outcome·claim 경계만 소유한다.
- 검증: feature profile unit test, bounded writer smoke, 공식 Rerun export, 동일 조건 PASS/FAIL outcome consistency, `git diff --check`.
- 배포/운영: LAB1은 로컬 evidence producer와 RRD까지만 소유한다. 공개 asset 변환과 Vercel은 LAB3가 맡는다.
- data: 두 카메라, 8D state, 7D executed action, instruction, timestamp를 canonical episode에 보존하고 content hash로 sidecar와 묶는다.
- model: 첫 producer는 기존 성공 증거가 있는 OpenVLA checkpoint/revision을 고정한다. 모델 비교는 LAB2 이후로 미룬다.
- control: raw policy output, postprocessed action, 실제 `env.step` 입력을 분리해 기록하며 실행되지 않은 action을 executed로 표시하지 않는다.
- 관측: request latency, dropped frame, shape, seed, termination, success와 producer revision을 summary에 남긴다.
- 검토 후 제외: frontend·backend·인증·DB — LAB1은 로컬 episode 생성과 검증만 수행한다.

## 결정 로그

- status: resolved
- LeRobot v3 episode를 canonical format으로 사용하고 새 episode manifest를 만들지 않는다 — 공식 viewer 재사용 probe 반영.
- Rerun official export를 LAB1의 사람 검토 기준선으로 사용하고 Foxglove는 선택적 개발 진단으로만 남긴다.
- 첫 producer는 기존 OpenVLA+LIBERO 성공 경로로 고정하고 SmolVLA 선행 probe는 제거한다.
- eye-in-hand frame은 관찰 증거로 저장하되, checkpoint가 실제 소비했다는 근거가 없으면 model input으로 표기하지 않는다.
- Windows video decode는 probe에서 확인한 PyAV fallback을 명시적으로 사용한다.

## Step 트리

- [ ] **step-1 — canonical-contract-profile**
  - Artifact: LeRobot v3 canonical 결정 ADR, 갱신된 PRD/architecture와 dual-camera/action/revision profile validator 및 정상·실패 fixture.
  - Files: `docs/PRD.md`, `docs/ARCHITECTURE.md`, `docs/adr/0014-lerobot-canonical-episode-and-viewer-reuse.md`, `experiments/147-camera-action-episode-contract/episode_profile.py`, `experiments/147-camera-action-episode-contract/test_episode_profile.py`, fixture와 README.
  - Dependencies: 없음
  - Verify: 공개 `lerobot/libero` episode 0과 정상 fixture PASS; single-camera, missing-action, invalid-revision fixture FAIL; Python unit test PASS.
  - Failure probe: sidecar가 canonical action/state를 중복 소유하거나 wrist source를 선언하지 않으면 validator가 거부한다.
  - Commit: changeset 1 — LeRobot canonical contract and profile.
- [ ] **step-2 — libero-lerobot-writer**
  - Artifact: 기존 rollout 경계에서 agentview, eye-in-hand, 8D state, executed 7D action, task, timestamp를 기록하는 LeRobot writer와 provenance sidecar emitter.
  - Files: `experiments/01-vla-local-eval/client.py`, `experiments/147-camera-action-episode-contract/libero_writer.py`, writer unit/integration test와 mock fixture.
  - Dependencies: step-1
  - Verify: bounded mock 또는 짧은 rollout이 local LeRobot loader로 열리고 두 camera·state·action frame 수와 timestamp가 일치한다.
  - Failure probe: wrist observation 부재, camera/action timestep mismatch, non-finite action을 주입하면 finalize 전에 저장을 거부한다.
  - Commit: changeset 2 — LIBERO to LeRobot writer.
- [ ] **step-3 — bounded-official-viewer-smoke**
  - Artifact: 고정 task·seed·checkpoint의 bounded episode, sidecar, content hash와 공식 Rerun export smoke evidence.
  - Files: `experiments/147-camera-action-episode-contract/verify/bounded-smoke/`, 재현 script와 evidence index.
  - Dependencies: step-2
  - Verify: profile validator와 official Rerun export가 PASS하고, RRD에서 두 camera와 state/action graph가 같은 timeline을 scrub한다.
  - Failure probe: RRD의 frame count나 sidecar hash를 변조하면 evidence gate가 FAIL한다.
  - Commit: changeset 3 — bounded episode and official viewer smoke.
- [ ] **step-4 — canonical-pass-fail-pair**
  - Artifact: 동일 task/policy contract의 canonical PASS·FAIL LeRobot episode pair, RRD, provenance summary와 재현 명령.
  - Files: `experiments/147-camera-action-episode-contract/verify/canonical/`, `experiments/147-camera-action-episode-contract/README.md`, `ROADMAP.md`.
  - Dependencies: step-3
  - Verify: 두 episode 모두 profile PASS; PASS는 success=true, FAIL은 success=false; revision·seed·media hash와 raw→executed action 연결이 존재한다.
  - Failure probe: FAIL을 PASS로 relabel하거나 recorded simulation을 live/real telemetry로 표시하면 claim gate가 거부한다.
  - Commit: changeset 4 — canonical PASS/FAIL episode evidence.

## 검증/DoD

- **DoD**: 동일 과제·정책의 PASS/FAIL LeRobot v3 episode가 두 camera, state, instruction, executed action, latency, termination/success를 보존하고 clean rerun에서 profile validator와 공식 Rerun export를 통과한다.

## finding 큐

- exact LIBERO wrist observation key와 checkpoint 실제 image input 목록은 step-2 착수 시 runtime probe로 고정한다. key가 없거나 선언과 실행이 다르면 writer를 진행하지 않고 technical finding으로 남긴다.
