# 최종 보고서 — GEN1 고정된 다과제 평가 계약

> 완료: 2026-07-21 · 대상: GEN1 · 작성: 완료 경계(§B3) — 이 보고서가 완료 의식의 정본이다.

## 1. 문제 정의 (무엇을 왜 하려 했나)

LAB1~LAB3는 한 LIBERO 과제에서 실제 OpenVLA 성공·실패 episode와 관찰 가능한 공개 화면을 만들었지만, 여러 과제에서 정책을 비교할 때 무엇을 몇 번 실행할지 고정된 분모가 없었다. 평가 뒤 좋은 결과만 고르는 일을 막고 OpenVLA와 π0.5를 같은 task·initial state 기준으로 비교하려면, 실제 rollout 전에 과제·상태·정책 artifact·결과 evidence 계약을 먼저 동결해야 했다.

## 2. Objective 연결 (북극성과의 관계)

Objective의 “정책을 직접 실행·학습·비교하며 동일한 증거 계약으로 검증” 축을 한 과제 데모에서 다과제 실험 계약으로 확장했다. 아직 정책 성능을 주장하지 않고, 제3자가 앞으로의 120개 실행 분모와 제외 조건을 실행 전에 확인할 수 있게 했다.

## 3. 경로 (horizon → milestone → steps)

“여러 과제에서 통하는 로봇 판단 실험실” Horizon의 첫 milestone으로 진행했다. LIBERO Spatial/Object/Goal에서 각 4개 과제를 고정하고, 과제마다 초기 상태 5개를 실제 MuJoCo reset으로 대조했다. 이어 OpenVLA와 π0.5의 서로 다른 camera·state·action 계약과 exact artifact revision을 registry로 명시하고, 120개 immutable run key와 terminal evidence schema를 생성했다. 마지막으로 네 선행 정본과 외부 source를 묶은 통합 gate를 Windows clean checkout에서 재실행했다. 승인된 5-step 경로에서 실제 rollout이나 성능 비교를 추가하지 않았다.

## 4. 구현 결과 (무엇이 만들어졌나)

이제 평가 대상은 12개 task × 5개 initial state × 2개 policy의 120개 cell로 사전 고정된다. 각 cell은 suite, task, state, policy artifact revision과 adapter revision을 포함한 immutable key를 가지며 누락·중복을 자동 거부한다. OpenVLA와 π0.5의 입력이 같다고 가장하지 않고 각 policy가 보는 camera와 state, 생성하는 단일 action 또는 action chunk를 별도로 기록한다. success·timeout은 episode, error는 재현 보고서, excluded는 사유가 없으면 유효한 결과가 될 수 없다.

## 5. 이슈와 해결 (막혔던 것, 어떻게 풀었나)

초기 상태 반복 probe의 첫 시도는 같은 environment instance에서 RNG가 진행돼 다른 observation을 만들었다. 각 clean repeat 전에 seed를 다시 설정해 “같은 초기 상태”의 의미를 분명히 한 뒤 60개 state를 두 번 대조했다. π0.5 checkpoint는 mutable GCS prefix이므로 object generation·size·checksum으로 16개 object snapshot을 별도 고정했다. 첫 clean checkout gate는 Windows CRLF 변환 때문에 repo 내부 텍스트 hash가 달라져 실패했다. 내부 tracked text만 Git 정본인 LF bytes로 정규화하고, 외부 BDDL과 state binary는 raw-byte hash를 유지해 `core.autocrlf=true` clean checkout에서 다시 PASS했다.

## 6. 결과물과 증거 (검증 포함)

- Changesets: `changesets/20260721-gen1-suite-task-slice/`, `changesets/20260721-gen1-initial-state-contract/`, `changesets/20260721-gen1-policy-compatibility-registry/`, `changesets/20260721-gen1-multitask-result-contract/`, `changesets/20260721-gen1-clean-contract-gate/`.
- Commits: `83b2933`, `d3f6800`, `db79ffa`, `0b5a0f3`, `553168b`.
- Contract surface: `experiments/150-multitask-evaluation-contract/benchmark-manifest.json`, `initial-states.json`, `policy-registry.json`, `run-denominator.json`, `schemas/multitask-run-v1.json`.
- Canonical evidence: `experiments/150-multitask-evaluation-contract/verify/canonical/`; 통합 report는 12 task, 60 selected states, 24 compatible task-policy pair, 120 planned/unique cell을 기록한다.
- External anchors: [LIBERO commit](https://github.com/Lifelong-Robot-Learning/LIBERO/tree/8f1084e3132a39270c3a13ebe37270a43ece2a01), [openpi commit](https://github.com/Physical-Intelligence/openpi/tree/15a9616a00943ada6c20a0f158e3adb39df2ccac), [π0.5 LIBERO checkpoint listing](https://storage.googleapis.com/storage/v1/b/openpi-assets/o?prefix=checkpoints/pi05_libero/)을 대조했다(접근일: 2026-07-21).
- Negative evidence: unknown/duplicate/relabel task, state order/seed/hash drift, action/camera/checkpoint mismatch, missing/duplicate/evidenceless result, cell deletion/duplication/revision drift가 모두 거부됐다.
- Clean evidence: detached Windows checkout에서 unit·mutation·official-source·live-GCS gate PASS, checkout dirty file 0, 임시 worktree 제거 완료.
- 크기 회고: 승인 plan의 5개 changeset으로 닫혀 선언한 `changesets>=5`와 일치하며 task, state, policy, result, clean gate가 각각 독립 검증 표면을 가진다.
- 실표면: CLI clean checkout에서 `CLEAN_WORKTREE_GATE=PASS`; 120 planned/unique cell과 세 negative mutation 거부를 실제 실행으로 확인했다.
- 재현: `python experiments/150-multitask-evaluation-contract/test_verify_contract.py; python experiments/150-multitask-evaluation-contract/verify_contract.py --libero-root <LIBERO-at-8f1084e> --openpi-root <openpi-at-15a9616> --verify-live-gcs`.

## 7. 후속 제안 (다음에 무엇을)

다음 milestone GEN2는 고정된 OpenVLA 60개 cell을 manifest-driven resumable runner로 실제 실행하고 모든 terminal result에서 canonical episode까지 추적되게 만든다. 그 다음 GEN3는 동일한 60개 paired cell에 π0.5를 실행해 입력 차이를 숨기지 않는 비교를 만든다. 실제 성능 수치와 failure pattern은 이 두 실행이 끝나기 전까지 주장하지 않는다.
