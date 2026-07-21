# 최종 보고서 — GEN3 두 VLA의 공정 비교

> 완료: 2026-07-21 · 대상: GEN3 · 작성: 완료 경계(§B3) — 이 보고서가 완료 의식의 정본이다.

## 1. 문제 정의 (무엇을 왜 하려 했나)

GEN2는 OpenVLA의 60개 다과제 기준선을 만들었지만 한 정책만의 수치로는 비교 실험실이라 부를 수 없었다. 두 번째 정책을 단순히 붙이면 서로 다른 checkpoint, 입력, action horizon과 재시도를 숨긴 채 하나의 순위로 오해하게 만들 수 있었다. GEN3는 π₀.₅-LIBERO를 같은 60 task-state에서 실제 실행하고, 공통 분모와 정책별 adapter 차이를 함께 공개하는 paired comparison을 목표로 했다.

## 2. Objective 연결 (북극성과의 관계)

Objective의 “컨슈머 하드웨어에서 정책을 직접 실행·비교하며 동일한 증거 계약으로 검증”하는 축을 두 policy·120 canonical rollout로 확장했다. 사람이 aggregate 수치에서 각 정책의 dual-camera episode와 causal event까지 내려갈 수 있는 비교 정본을 만들었고, 검증된 시뮬레이션 결과와 일반화·실물에 대한 미검증 주장을 분리했다.

## 3. 경로 (horizon → milestone → steps)

“여러 과제에서 통하는 로봇 판단 실험실” Horizon의 세 번째 Milestone으로 진행했다. 먼저 exact OpenPI revision과 12.4GB π₀.₅ checkpoint를 실제 GEN2 관측으로 probe했다. 다음으로 두 정책의 model input·전처리·action chunk·gripper·재계획 차이를 adapter contract로 고정했다. 세 번째 Step에서 π₀.₅ 60개 rollout을 실행·봉인했고, 네 번째에서 GEN1 denominator로 두 60-cell manifest를 lossless join했다. 마지막 Step은 exact provenance, retry/exclusion과 허용 claim을 함께 검증했다. 승인 plan의 다섯 Step을 변경 없이 완주했다.

## 4. 구현 결과 (무엇이 만들어졌나)

고정된 60 pair에서 OpenVLA는 35 success, π₀.₅는 58 success였다. 관측된 paired success difference는 π₀.₅ 기준 `+23/60 = +0.383333…`이고, seed 고정 10,000회 paired bootstrap 95% 구간은 `[+0.25, +0.516666…]`다. both success 34, π₀.₅-only success 24, OpenVLA-only success 1, both non-success 1로 각 cell의 결과가 두 canonical episode에 연결된다.

이 수치는 동일 입력·동일 checkpoint 비교가 아니다. OpenVLA는 suite별 checkpoint와 instruction+main camera에서 1×7 action을 매 step 생성한다. π₀.₅는 단일 checkpoint와 instruction+main+wrist+8D state에서 10×7 chunk를 만들고 5 step마다 재계획한다. 실험실은 이 차이를 숨기지 않은 채 동일 task/state/environment/result denominator만 공통으로 고정한다.

## 5. 이슈와 해결 (막혔던 것, 어떻게 풀었나)

OpenPI가 공식 문서에서 Ubuntu 22.04를 대상으로 하는 반면 현재 환경은 Ubuntu 24.04였다. 지원을 추정하지 않고 exact revision의 checkpoint load와 actual inference probe로 먼저 호환성을 확인했다. 첫 rollout은 LIBERO import path 누락과 PyTorch 2.6의 `weights_only=True` 기본값 때문에 infrastructure error가 두 번 났다. 두 attempt를 삭제하지 않고 ledger에 남기고, 고정된 local LIBERO init에만 명시적으로 `weights_only=False`를 적용해 60개 policy result와 분리했다.

`openpi-client` 설치 과정에서 평가 venv의 NumPy를 1.26으로 내리려는 near-miss가 있어 2.2.6으로 복구하고 실제 client import와 rollout으로 확인했다. 종료 검증에서는 제가 만든 보조 monitor 셸이 process-clean gate에 걸렸다. 정책 runner와 무관한 해당 PID만 종료한 뒤 verifier를 다시 실행해 잔존 runner/server/client 0을 확인했다. claim gate에서는 aggregate 하나로 우승자를 선언하는 문구, 동일 checkpoint/input 주장, hidden exclusion/retry를 모두 adversarial fixture로 고정했다.

## 6. 결과물과 증거 (검증 포함)

- Changesets: `changesets/20260721-gen3-pi05-compatibility-probe/`, `changesets/20260721-gen3-shared-policy-adapter-gate/`, `changesets/20260721-gen3-pi05-sixty-cell-execution/`, `changesets/20260721-gen3-paired-statistics/`, `changesets/20260721-gen3-fairness-and-claim-gate/`.
- Commits: `c44a06f`, `6d662ee`, `aa81689`, `30d854c`; 마지막 fairness changeset과 이 보고서는 GEN3 완료 commit에 포함된다.
- π₀.₅ 실행 정본: `experiments/152-paired-vla-comparison/verify/canonical/`; 60 terminal, 58 success, 2 timeout, 7,608 frames, 1,545 requests, attempts 62와 infrastructure 2.
- Paired 정본: `experiments/152-paired-vla-comparison/verify/paired-report.json`; exact 60 pairs, OpenVLA 35/60, π₀.₅ 58/60, difference +23/60, bootstrap 95% `[+0.25,+0.516666…]`.
- Fairness 정본: `experiments/152-paired-vla-comparison/verify/fairness-report.json`; planned/included 60, exclusion/unmatched 0, attempts 61/62, spec/quality `pass/pass`.
- Negative gates: wrong suite checkpoint, missing norm stats, action dimension, hidden transform/sign drift, wrist relabel, missing/duplicate/relabel cell, suite omission, zero denominator, rounded-only metric, general winner, same checkpoint, hidden exclusion/retry와 revision drift를 거부했다.
- External anchors: [OpenVLA](https://github.com/openvla/openvla), [OpenPI `15a9616a`](https://github.com/Physical-Intelligence/openpi/tree/15a9616a00943ada6c20a0f158e3adb39df2ccac), [LIBERO `8f1084e`](https://github.com/Lifelong-Robot-Learning/LIBERO/tree/8f1084e3132a39270c3a13ebe37270a43ece2a01) (접근일: 2026-07-21).
- 크기 회고: 승인 plan의 5개 changeset으로 닫혀 선언한 `changesets>=5`와 일치한다. compatibility, adapter, actual execution, statistics, fairness가 각각 독립 검증 표면이다.
- 실표면: Ubuntu WSL2·RTX 5090에서 실제 π₀.₅ 60 rollout을 완료했고, `pi05 execution gate: PASS`, `paired statistics gate: PASS`, `fairness and claim gate: PASS`와 process cleanup을 관측했다.
- 재현: `/home/yusun/.venvs/vla-eval/bin/python experiments/152-paired-vla-comparison/verify_pi05_execution.py --artifact-root <GEN3_ARTIFACT_ROOT> --ledger <GEN3_LEDGER> --assert-clean-processes; python experiments/152-paired-vla-comparison/paired_statistics.py; python experiments/152-paired-vla-comparison/fairness_gate.py`.

## 7. 후속 제안 (다음에 무엇을)

다음 Milestone GEN4는 27개 non-success episode(OpenVLA 25, π₀.₅ 2)를 성공률 숫자에서 멈추지 않고 frame/event predicate를 가진 관측 가능한 실패 양상 또는 `unknown`으로 완전 집계한다. 원인 진단으로 과장하지 않으며 reviewer sample로 분류 일관성을 확인한다. GEN5는 그 결과를 공개 비교 화면으로 옮겨 aggregate에서 LAB3 canonical episode까지 제3자가 추적하게 한다.
