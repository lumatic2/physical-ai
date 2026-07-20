# PLAN — LAB1 카메라-행동 episode 계약

Status: approved 2026-07-20

> 생성: 2026-07-20 · 갈래: product · scope 결정: LIBERO 단일 과제의 versioned PASS/FAIL episode evidence까지
> milestone-레벨 durable plan doc. 진행 상태의 정본은 산출물 status machine과 `ROADMAP.md`다.

## 북극성 → horizon → milestone → step

- **북극성**: 카메라와 센서로 보고, 언어 지시를 이해하고, 행동을 실행하는 전 과정을 관찰 가능한 피지컬 AI 실험실로 만든다. (← `OBJECTIVE.md`)
- **horizon**: 보고 판단하고 움직이는 로봇팔 실험실 (← `plans/horizons/see-understand-act-robot-lab.md`)
- **milestone**: camera/state/instruction/action/outcome producer, schema validator, canonical evidence를 가로지르는 독립 step이 필요하므로 milestone 규모다.

## Scope Boundary

- 결정: 기존 LIBERO evaluator를 확장해 단일 pick-and-place 과제의 main/wrist camera와 state/action/outcome trace를 만들고 PASS/FAIL fixture까지 검증한다.
- Execution mode: `continuous`
- Stop only: completed, blocked, decision_required, risk_gate, secret_required, external_authority_required, user_stopped.
- 진행 보고: commentary only. 미완 leaf는 턴 종료점이 아니다.
- Rollback/cleanup: 각 changeset을 독립 revert할 수 있게 하고 WSL2/model/server child process와 임시 media bundle을 종료·삭제한다.

## 스캐폴딩 결정

- source-of-truth: `experiments/01-vla-local-eval`의 LIBERO rollout과 새 `experiments/147-camera-action-episode-contract`의 trace schema/evidence.
- 검증: bounded rollout smoke, JSON schema/provenance validator, PASS/FAIL canonical fixture, `git diff --check`.
- 배포/운영: LAB1은 로컬 producer/evidence만 만든다. public web sync와 Vercel은 LAB3 소유.
- data: `physical-ai-arm-episode-v1` manifest가 environment/policy revision, seed, camera asset, state/action source와 outcome을 소유한다. media는 content-hashed compressed asset으로 참조한다.
- model: LeRobot-compatible SmolVLA LIBERO checkpoint를 우선 probe하고 호환 실패 시 기존 OpenVLA path를 사용한다. fallback 사용 여부는 evidence에 기록한다.
- 관측: latency, dropped frame, state/action shape, termination/success를 trace summary에 기록한다.
- 검토 후 제외: 인증·DB·결제 — 로컬 evidence producer이며 사용자 계정과 영속 서비스가 없다.

## 결정 로그

- status: resolved
- 로봇 제조사 브랜딩보다 LIBERO의 camera/state/action 계약을 우선한다 — 사용자 방향 승인 2026-07-20.
- 첫 Horizon은 공개 checkpoint와 단일 과제를 사용하고 새 foundation model을 학습하지 않는다 — 범위 확정 2026-07-20.
- 과제는 기존 suite에서 target/destination이 시각적으로 분명하고 PASS/FAIL 재현이 가능한 첫 항목을 기술 gate로 선택한다 — 별도 사용자 결정 없음.

## Step 트리

- [ ] **step-1 — episode-contract-fixture**
  - Artifact: `physical-ai-arm-episode-v1` schema, 최소 fixture, validator와 failure fixture.
  - Files: `experiments/147-camera-action-episode-contract/`, `experiments/01-vla-local-eval/client.py` read-only audit.
  - Dependencies: none
  - Verify: valid fixture PASS; missing wrist camera/source/revision fixture FAIL.
  - Failure probe: model input camera와 observer camera provenance가 없으면 validator가 거부한다.
  - Commit: changeset 1 — trace contract and validator.
- [ ] **step-2 — libero-dual-camera-exporter**
  - Artifact: bounded LIBERO rollout이 main/wrist camera, robot state, instruction, raw/controller action, latency와 outcome을 trace로 export한다.
  - Files: `experiments/01-vla-local-eval/client.py`, 새 exporter/helper, experiment 147 fixtures.
  - Dependencies: step-1
  - Verify: one bounded mock/short rollout produces schema-valid synchronized frames and finite 7D actions.
  - Failure probe: camera/action timestep mismatch 또는 non-finite action을 주입하면 export gate FAIL.
  - Commit: changeset 2 — dual-camera episode producer.
- [ ] **step-3 — canonical-pass-fail-evidence**
  - Artifact: 같은 task/policy contract의 canonical PASS와 FAIL episode, summary, 재현 명령.
  - Files: `experiments/147-camera-action-episode-contract/verify/`, README/evidence index.
  - Dependencies: step-2
  - Verify: both episodes validate; PASS success=true, FAIL success=false; revisions/seeds/media hashes present.
  - Failure probe: FAIL episode를 PASS로 relabel하면 outcome consistency gate가 거부한다.
  - Commit: changeset 3 — canonical episode evidence.

## 검증/DoD

- **DoD**: 동일 과제의 PASS/FAIL episode가 main/wrist camera, raw state, instruction, raw/controller action, latency, termination/success를 versioned trace로 보존하고 clean rerun에서 validator를 통과한다.

## finding 큐

- SmolVLA checkpoint가 현재 LIBERO observation naming과 맞지 않으면 environment processor adapter를 좁은 follow-up changeset으로 추가한다.

## 진행 로그

- 2026-07-20 사용자 방향 승인 후 계획 작성.
