# 최종 보고서 — LAB1 카메라-행동 episode 계약

> 완료: 2026-07-21 · 대상: LAB1 · 작성: 완료 경계(§B3) — 이 보고서가 완료 의식의 정본이다.

## 1. 문제 정의 (무엇을 왜 하려 했나)

기존 OpenVLA+LIBERO evaluator는 카메라 관측에서 로봇 행동을 생성해 환경에 실행할 수 있었지만, 사람이 그 과정을 다시 보고 감사할 episode 증거를 남기지 않았다. LAB1은 단순 성공률 대신 같은 과제의 성공과 실패에서 카메라·센서·언어 지시·행동·결과가 어떻게 이어지는지 보존하는 것을 목표로 했다.

## 2. Objective 연결 (북극성과의 관계)

Objective의 “카메라와 센서로 세상을 보고, 언어 지시를 이해하고, 로봇 행동을 생성·실행하며, 그 전 과정을 사람이 관찰할 수 있는 피지컬 AI 실험실”에서 가장 아래층인 실행 증거를 만들었다. 문헌·코드 이해를 실제 OpenVLA 추론과 재현 가능한 episode로 끌어올려 **이해에서 실증으로**, **데모에서 실험 플랫폼으로** 축을 전진시켰다.

## 3. 경로 (horizon → milestone → steps)

승인된 “보고 판단하고 움직이는 로봇팔 실험실” Horizon의 첫 milestone으로 진행했다. 공식 viewer 재사용 probe에서 새 포맷이나 viewer fork 대신 LeRobot v3 dataset과 Rerun을 선택했고, 이어서 canonical profile, LIBERO writer, 실제 bounded OpenVLA smoke, 동일 과제 PASS/FAIL pair의 네 step을 순서대로 닫았다. 계획의 step 경계는 유지했지만 과거 outcome label을 재사용하지 않고 현재 pinned runtime에서 상반 결과가 실제로 나오는 task를 다시 탐색했다.

## 4. 구현 결과 (무엇이 만들어졌나)

이제 LIBERO rollout은 main camera와 wrist camera, 8차원 robot state, 언어 지시, 7차원 executed action, 요청 지연, 종료 사유와 성공 여부를 하나의 LeRobot episode로 저장한다. 동일 LIBERO Spatial task 5에서 초기 상태 0은 78프레임 만에 성공했고 초기 상태 1은 220프레임 전체를 실행한 뒤 timeout으로 실패했다. 두 episode는 독립 dataset과 Rerun recording으로 남아 이후 판단·행동 trace와 공개 UI가 소비할 정본이 됐다.

## 5. 이슈와 해결 (막혔던 것, 어떻게 풀었나)

WSL이 `E_UNEXPECTED`로 시작되지 않아 사용자의 승인을 받고 Ubuntu WSL을 종료·재시작한 뒤 Python 3.12, LeRobot source, LIBERO 환경을 다시 구성했다. OpenVLA checkpoint revision이 중간 경로에서 느슨해질 수 있어 server까지 commit SHA를 전달하도록 고정했다. 과거 분포에서 실패 후보였던 task 0은 현재 runtime의 init-state 0~9가 모두 성공했으므로 label을 재사용하지 않았고, task 5에서 실제 success/timeout pair를 찾았다. Windows의 `torchcodec` 부재는 공식 viewer가 제공하는 PyAV fallback으로 처리했다. 검증이 끝난 임시 후보 dataset 삭제는 로컬 안전 정책이 명령 실행 전에 거부해 `tmp/`에 남겼으며, Git 산출물에는 포함하지 않았다.

## 6. 결과물과 증거 (검증 포함)

- Changesets: `changesets/20260721-lab1-canonical-contract-profile/`, `changesets/20260721-lab1-libero-lerobot-writer/`, `changesets/20260721-lab1-bounded-official-viewer-smoke/`, `changesets/20260721-lab1-canonical-pass-fail-pair/`.
- Commits: `9abec93`, `114a88f`, `777701b`, `70f5661`.
- Canonical evidence: `experiments/147-camera-action-episode-contract/verify/canonical/`; pair report의 종합 판정은 PASS다.
- 실제 결과: task 5, seed 0, max 220; PASS init-state 0은 success/78 frames, FAIL init-state 1은 timeout/220 frames다.
- Producer revisions: OpenVLA `962318cec55ac10993ff0f5f43eda9a270b4c873`, LIBERO `8f1084e3132a39270c3a13ebe37270a43ece2a01`.
- Dataset tree SHA-256: PASS `fa32a6cc199cab3c77267b193f7bfac8cad20e4b0a2d25e54808d4dc786d705d`, FAIL `dd84f5e677a24ffa1746c70acaa6afa943817104eb00cf90fa4c6a013dda4d90`.
- 검증: LAB1 unit tests 24/24 PASS, official LeRobot loader에서 78/220 frames와 `(8,)` state·`(7,)` action·dual camera 확인, 두 RRD의 entity/timeline verify PASS, pair negative gates의 relabel/revision·seed drift/action-link 누락 거부 PASS, WSL 관련 process 0 및 ports 8012~8015 listener 0, `git diff --check` PASS.
- 크기 회고: 승인 plan의 4개 독립 changeset으로 닫혀 선언한 `changesets>=3`보다 크지만 각 step이 정본 계약·producer·실제 viewer·상반 outcome이라는 독립 검증 표면을 소유하므로 milestone 인플레가 아니다. 선행 viewer probe changeset은 계획 입력으로 별도다.
- 실표면: official LeRobot loader와 `lerobot-dataset-viz`를 두 실제 dataset에 실행해 dual-camera/state/action을 읽고 78·220프레임 Rerun recording을 생성·검증했다.
- 재현: `python experiments/147-camera-action-episode-contract/verify_canonical_pair.py --pass-dataset-root <pass> --pass-sidecar <pass-sidecar> --pass-rrd <pass.rrd> --fail-dataset-root <fail> --fail-sidecar <fail-sidecar> --fail-rrd <fail.rrd> --rerun-cli <rerun.exe> --output <report.json>`.

## 7. 후속 제안 (다음에 무엇을)

같은 Horizon의 LAB2를 이어서 direct VLA action과 VLM→skill 판단 event를 같은 trace contract에서 비교해야 한다. 특히 보조 설명을 VLA의 숨은 생각으로 표시하지 않도록 모든 event에 실제 source와 causal role을 붙이고, hidden-reasoning fixture를 거부하는 것이 다음 핵심 게이트다. LAB2가 닫히면 LAB3에서 이 canonical PASS/FAIL pair를 공개 브라우저의 dual-camera·timeline scrub 화면으로 연결한다.
