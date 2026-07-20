# PLAN ADDENDUM — LAB1 공식 episode/viewer 재사용

Status: proposed 2026-07-21 — 사용자 승인 대기

> 원 계획 `2026-07-20-lab1-camera-action-episode-contract.md`는 승인 이력으로 보존한다. 이 문서는 공식 viewer probe 결과에 따른 후속 실행 변경안이다.

## 왜 바꾸는가

- 공개 `lerobot/libero` episode에서 LAB1이 요구한 dual camera, state, action, timestamp, instruction 계약을 실제로 확인했다.
- LeRobot 공식 CLI가 같은 episode를 Rerun과 Foxglove로 이미 변환한다.
- LeRobot Dataset Visualizer 배포본이 LAB3에 필요한 synchronized video/chart/scrub interaction을 이미 제공한다.
- 따라서 `physical-ai-arm-episode-v1`을 새로 발명하면 호환성과 UI adapter를 중복 구현하게 된다.

근거: `experiments/147-camera-action-episode-contract/verify/official-viewer-reuse/README.md`.

## 변경 결정

| 기존 승인안 | 변경안 |
|---|---|
| 독자 `physical-ai-arm-episode-v1` manifest | LeRobot v3 episode를 canonical format으로 사용 |
| 별도 camera/action schema부터 설계 | LeRobot feature profile + LAB provenance sidecar만 추가 |
| custom replay path | Rerun official export를 내부 replay 기준선으로 사용 |
| LAB3 interaction 신규 설계 | Dataset Visualizer의 video/playback/chart 패턴 선택 이식 |
| SmolVLA checkpoint 우선 probe | 이미 성공 evidence가 있는 OpenVLA+LIBERO 경로를 첫 producer로 사용; 모델 비교는 LAB2로 이동 |

## 수정된 LAB1 step 트리

- [ ] **step-1 — lerobot-episode-profile**
  - Artifact: LeRobot v3 feature profile validator와 valid/missing-wrist/missing-action fixture.
  - Required: 2 camera, state, action, timestamp, instruction, environment/policy revision pointer.
  - Verify: 공개 `lerobot/libero` episode PASS; single-camera/missing-action fixture FAIL.
  - Commit: changeset 1 — LeRobot episode profile and validator.
- [ ] **step-2 — libero-lerobot-writer**
  - Artifact: `experiments/01-vla-local-eval/client.py:85-95`의 rollout 경계를 감싼 LeRobot writer.
  - Record: agentview, eye-in-hand, 8D state, executed 7D action, task, 10fps timestamp.
  - Sidecar: raw policy action, request latency, model/environment revision, termination/success.
  - Verify: bounded mock/short rollout이 official Rerun export에서 2 camera + state/action을 연다.
  - Failure: wrist observation 부재, timestep mismatch, non-finite action이면 episode 저장 거부.
  - Commit: changeset 2 — LIBERO to LeRobot writer.
- [ ] **step-3 — canonical-pass-fail-rerun**
  - Artifact: 동일 task/policy의 PASS·FAIL LeRobot episode, provenance sidecar, RRD, hashes.
  - Verify: profile validator PASS, official Rerun viewer smoke PASS, PASS/FAIL outcome consistency PASS.
  - Failure: recorded/simulation evidence를 live/real telemetry로 relabel하면 claim gate FAIL.
  - Commit: changeset 3 — canonical episode evidence and replay.

## LAB2/LAB3에 넘기는 경계

- LAB2가 sidecar를 `sensor | vlm | vla | controller | environment` provenance event로 승격한다. hidden chain-of-thought는 저장·표시하지 않는다.
- LAB3가 Dataset Visualizer의 synchronized multi-video, playback bar, Recharts cursor interaction을 현재 공개 앱에 이식한다.
- LAB3 공개 화면은 dataset-cleaning sidebar를 복제하지 않고 `관측 → 판단 → 행동 → 결과` lane과 raw evidence link를 추가한다.
- Foxglove는 optional developer diagnostic이며 공개 UI dependency가 아니다.

## 승인 시 효력

사용자 승인 후 이 addendum이 LAB1의 실행 정본이 된다. 기존 plan은 변경하지 않고, `ROADMAP.md`의 LAB1 DoD도 그대로 유지한다.
