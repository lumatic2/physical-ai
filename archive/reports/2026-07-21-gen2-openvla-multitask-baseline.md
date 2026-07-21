# 최종 보고서 — GEN2 OpenVLA 다과제 기준선

> 완료: 2026-07-21 · 대상: GEN2 · 작성: 완료 경계(§B3) — 이 보고서가 완료 의식의 정본이다.

## 1. 문제 정의 (무엇을 왜 하려 했나)

GEN1은 12개 task와 5개 initial state의 평가 분모를 고정했지만 실제 다과제 OpenVLA 결과는 없었다. 한 과제의 성공·실패 영상만으로는 일반화 능력을 수치로 말할 수 없고, 장시간 실행이 끊겼을 때 이미 끝난 결과를 숨겨 재시도할 위험도 있었다. GEN2는 60개 OpenVLA cell을 실제 실행하고 모든 outcome을 canonical episode와 append-only 이력으로 보존하는 것을 목표로 했다.

## 2. Objective 연결 (북극성과의 관계)

Objective의 “정책을 직접 실행·비교하고 제3자가 재현 가능한 산출물로 확인”하는 축을 실제 60-rollout baseline으로 움직였다. 문헌·코드 이해나 한 과제 데모가 아니라 RTX 5090에서 세 suite를 실행한 수치와 개별 dual-camera episode를 같은 증거 계약에 연결했다.

## 3. 경로 (horizon → milestone → steps)

“여러 과제에서 통하는 로봇 판단 실험실” Horizon의 두 번째 milestone으로 진행했다. 첫 step에서 GEN1 분모를 60개 exact command로 변환했고, 두 번째에서 중단·재시도를 숨길 수 없는 append-only ledger를 만들었다. 세 번째에서 LAB1 LeRobot와 LAB2 direct-VLA event를 run key의 sealed episode로 승격했다. 네 번째에서 Spatial/Object/Goal 각 20개를 실제 실행했고, 마지막 step에서 canonical index만으로 aggregate를 재계산했다. π0.5 실행, 정책 우열, 실패 원인 추정과 공개 UI는 추가하지 않았다.

## 4. 구현 결과 (무엇이 만들어졌나)

OpenVLA baseline은 60개 중 35 success, 25 timeout으로 성공률 58.33%다. Spatial은 13/20, Object는 12/20, Goal은 10/20 success였다. 각 결과에는 task/state/checkpoint/adapter revision, dual-camera LeRobot episode, raw→executed action causal event, frames, wall latency와 content hash가 연결된다. 완료된 cell은 재개할 때 건너뛰고 infrastructure error는 policy timeout으로 합산되지 않는다.

## 5. 이슈와 해결 (막혔던 것, 어떻게 풀었나)

첫 실제 smoke는 LeRobot writer가 parquet footer를 닫기 전에 causal exporter를 호출해 infrastructure error가 됐다. 실패 attempt를 삭제하지 않고 ledger에 남긴 뒤, client 종료 후 finalized parquet에서 event를 생성하도록 순서를 옮겨 같은 run key의 explicit retry를 성공시켰다. Object checkpoint 기본 다운로드는 3.96GB partial shard에서 stale connection으로 정체됐다. 관련 server/executor를 정리하고 partial cache를 보존한 채 single-worker `hf download`로 resume해 복구했다. Goal checkpoint는 Object inference와 병행 다운로드했다. 전체 종료 뒤 server/client process 0과 GPU baseline 복귀를 확인했다.

## 6. 결과물과 증거 (검증 포함)

- Changesets: `changesets/20260721-gen2-manifest-driven-runner/`, `changesets/20260721-gen2-resumable-run-ledger/`, `changesets/20260721-gen2-canonical-episode-export/`, `changesets/20260721-gen2-sixty-cell-execution/`, `changesets/20260721-gen2-baseline-aggregate-gate/`.
- Commits: `61f9f01`, `10ea88c`, `648e7f4`, `6fa3384`, `43cce9e`.
- Canonical index/ledger: `experiments/151-openvla-multitask-baseline/verify/canonical/`; 60 terminal, 0 pending, 123 ledger events, infrastructure attempt 1.
- Aggregate: `experiments/151-openvla-multitask-baseline/verify/baseline-report.json`; 35 success, 25 timeout, median 189 frames, median wall 64.978초.
- Raw local evidence: LeRobot episode 60개, causal event stream 60개, valid camera video 120개를 포함한 134MB local-only artifact root.
- Traceability: 60/60 artifact ref와 manifest/dataset/sidecar/event SHA-256를 전수 재계산했고 suite별 representative success/timeout 6개를 raw episode에 연결했다.
- Negative gates: invalid task/state/revision, hidden retry, duplicate terminal, partial promotion, camera relabel, action link 누락, local path leak, missing/duplicate cell, corrupt hash, timeout 누락과 infrastructure relabel을 모두 거부했다.
- External anchors: [LIBERO commit](https://github.com/Lifelong-Robot-Learning/LIBERO/tree/8f1084e3132a39270c3a13ebe37270a43ece2a01)과 suite별 exact [OpenVLA LIBERO checkpoints](https://huggingface.co/openvla) (접근일: 2026-07-21).
- 크기 회고: 승인 plan의 5개 changeset으로 닫혀 선언한 `changesets>=5`와 일치하며 runner, ledger, exporter, actual execution, aggregate가 각각 독립 검증 표면을 가진다.
- 실표면: Ubuntu WSL2·RTX 5090에서 실제 60 rollout을 실행해 `SIXTY_CELL_EXECUTION_GATE=PASS`, aggregate CLI에서 `BASELINE_AGGREGATE_GATE=PASS`, 종료 후 process cleanup PASS를 관측했다.
- 재현: `python experiments/151-openvla-multitask-baseline/execute_baseline.py --artifact-root <GEN2_ARTIFACT_ROOT> --ledger <GEN2_LEDGER>; python experiments/151-openvla-multitask-baseline/verify_execution.py --artifact-root <GEN2_ARTIFACT_ROOT> --ledger <GEN2_LEDGER> --assert-clean-processes; python experiments/151-openvla-multitask-baseline/aggregate_baseline.py`.

## 7. 후속 제안 (다음에 무엇을)

다음 milestone GEN3는 동일한 60개 run key에 π0.5-LIBERO를 실행해 paired difference와 입력 차이를 함께 기록한다. GEN4 전까지 timeout을 실패 원인으로 해석하지 않고 관측 가능한 episode pattern으로만 유지한다. GEN5에서는 대표 raw episode와 aggregate drill-down을 공개 화면으로 옮겨 외부 reviewer가 수치에서 증거까지 내려갈 수 있게 한다.
