# HORIZON — 여러 과제에서 통하는 로봇 판단 실험실

> 생성: 2026-07-21 · ROADMAP marker: `harness:goal id="multitask-generalization-lab"` · 상태: completed
> 위계: Objective(`OBJECTIVE.md`) → **Horizon**(이 문서) → Milestone(`plans/2026-07-21-gen*-*.md`) → Step.

## 목표

- 단일 LIBERO 과제의 recorded evidence를 사전 고정한 12개 과제·5개 초기 상태·두 policy family의 재현 가능한 비교 제품으로 확장한다.
- Objective의 **이해에서 실증으로** 축을 표본과 통계로, **데모에서 실험 플랫폼으로** 축을 반복 실행·실패 추적·공개 비교로 전진시킨다.
- **무감독 분량: ≥25 changeset 상당** — GEN1~GEN5 각 5 step/changeset의 bottom-up 합계다.

## 왜 지금

- LAB3는 실제 evidence와 공개 화면을 닫았지만 한 과제의 PASS/FAIL만으로 일반화나 cherry-pick 부재를 입증하지 못한다.
- 기존 LeRobot episode, provenance event, public replay 계약을 그대로 재사용할 수 있어 새 viewer보다 평가 신뢰성에 집중할 수 있다.
- 하드웨어를 기다리지 않고도 정책 실행·비교·한계 공개라는 Objective의 핵심 포트폴리오 가치를 크게 높일 수 있다.

## 범위

- 포함: LIBERO Spatial/Object/Goal 각 4개 task, task별 initial state 5개, OpenVLA와 π₀.₅-LIBERO, 총 120 canonical rollout, paired aggregate, 관측 가능한 실패 양상, public matrix와 episode drill-down.
- 제외: LIBERO-100 전체, 새 foundation model 학습, 상시 public GPU backend, real robot claim, 원인 근거 없는 자동 failure diagnosis.
- 실행 모드: `continuous`; 정지 조건은 blocked/error, 새 사용자 결정·secret·risk, 사용자 명시 중단뿐이다.

## 담을 Milestone — 설계 번들 인덱스

| Milestone | 제목 | plan doc | 승인 | 리서치 입력 |
|---|---|---|---|---|
| **GEN1** | 고정된 다과제 평가 계약 | `plans/2026-07-21-gen1-multitask-evaluation-contract.md` | approved | `research/2026-07-21-multitask-generalization-lab-policy-evaluation.md` |
| **GEN2** | OpenVLA 다과제 기준선 | `plans/2026-07-21-gen2-openvla-multitask-baseline.md` | approved | GEN1 + 같은 research |
| **GEN3** | 두 VLA의 공정 비교 | `plans/2026-07-21-gen3-paired-vla-comparison.md` | approved | GEN1/GEN2 + ADR 0015 |
| **GEN4** | 증거 기반 실패 양상 | `plans/2026-07-21-gen4-observable-failure-patterns.md` | approved | GEN2/GEN3 canonical episodes |
| **GEN5** | 공개 일반화 비교 실험실 | `plans/2026-07-21-gen5-public-generalization-lab.md` | approved | GEN1~GEN4 evidence |

## 닫는 기준

- **평가군:** 선언 12 task×5 initial state×2 policy=120 episode / 관측: frozen manifest와 runner report / 판정: 누락·중복·revision drift 0.
- **정책 비교:** 선언 OpenVLA와 π₀.₅-LIBERO / 관측: compatibility registry, exact revision, paired result / 판정: 같은 task-state denominator와 adapter gate PASS.
- **재현성:** 선언 중단 후 재개와 clean rerun이 결과 index를 보존 / 관측: resumability·hash·negative fixture / 판정: duplicate execution 0, canonical artifact mismatch 0.
- **실패 양상:** 선언 모든 non-success episode가 증거 링크 또는 `unknown`을 가짐 / 관측: taxonomy validator와 reviewer sample / 판정: 근거 없는 causal label 0.
- **공개 제품:** 선언 aggregate→suite/task/policy→episode evidence drill-down / 관측: local/live Playwright와 asset gate / 판정: denominator·claim·hash·console/network gate PASS.

## 미리 쓰는 실패 회고

- **suite별 checkpoint를 하나의 범용 정책처럼 비교해 순위표가 불공정했다.** → GEN1 compatibility registry와 GEN3 fairness gate가 suite/checkpoint/action adapter를 공개하고 불일치 fixture를 거부한다.
- **120 rollout이 중간 실패와 재실행으로 중복·누락됐다.** → GEN1 immutable run key와 GEN2 resumable ledger가 task-state-policy 단위 idempotency를 강제한다.
- **실패 원인을 화면이 그럴듯하게 추정했다.** → GEN4는 관측 가능한 양상과 근거 pointer만 허용하고 부족하면 `unknown`으로 둔다.
- **대시보드 작업이 평가보다 커졌다.** → GEN5는 GEN1~GEN4 final report가 PASS하기 전 시작하지 않고 LAB3 drill-down을 재사용한다.

## 결정 로그

- resolved: 12 task×5 state, 두 policy family, 120 rollout을 Horizon 고정 범위로 한다.
- resolved: 비교 대상은 기존 OpenVLA와 π₀.₅-LIBERO다. 새 모델 학습은 제외한다.
- resolved: 실패는 원인이 아니라 증거 기반 양상으로 부른다.
- resolved: 공개 UI는 static recorded evidence이며 기존 `robotics.askewly.com` 배포 경로를 사용한다.

## Objective 임팩트

- 단일 demo를 12개 과제×5개 초기 상태×두 policy의 120 episode 완전성, 60쌍 paired 비교, 27/27 failure coverage와 production reviewer path로 확장했다. Objective의 “이해에서 실증으로”와 “데모에서 실험 플랫폼으로” 축은 공개 재현 가능한 비교까지 이동했으며, 실물 축은 다음 Horizon으로 명시적으로 남겼다.

## 링크

- 위: `OBJECTIVE.md`
- 후보 결정: `plans/horizons/CANDIDATES.md`
- 리서치: `research/2026-07-21-multitask-generalization-lab-policy-evaluation.md`
- 설계 결정: `docs/adr/0015-fixed-multitask-paired-vla-evaluation.md`
