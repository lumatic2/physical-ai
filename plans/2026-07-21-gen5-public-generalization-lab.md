# PLAN — GEN5 공개 일반화 비교 실험실

Status: approved — 2026-07-21 사용자 승인; 3-Horizon 전체 연쇄 실행

## Objective → Horizon → Milestone

- Objective: 제3자가 정책 실행·비교 결과를 재현 가능한 산출물로 확인한다. (`OBJECTIVE.md`)
- Horizon: 여러 과제에서 통하는 로봇 판단 실험실. (`plans/horizons/multitask-generalization-lab.md`)
- Milestone: aggregate matrix에서 기존 LAB3 canonical episode까지 내려가는 공개 reviewer 제품을 배포한다.

## Scope Boundary

- 포함: hashed public bundle, suite/task/policy matrix, paired stats, failure-pattern filters, LAB3 drill-down, local/live release gate.
- 제외: 새로운 3D viewer, live inference backend, 로그인/DB, 순위 하나로 축약한 leaderboard.
- Execution mode: continuous
- Stop only: completed, blocked, decision_required, risk_gate, secret_required, external_authority_required, user_stopped.
- Rollback/cleanup: 새 route·bundle registry 단위로 revert하고 기존 `/arm-lab`을 보존한다.

## planning_gate

```yaml
planning_gate:
  team_validation_mode: manual-pass
  scope_posture: selective
  delegation_decision:
    remote_background_agents: skip
    reason: "기존 LAB3 route를 재사용하는 하나의 public release chain이다."
  perspectives:
    product: "5분 안에 분모, paired 차이, 실패 양상과 대표 episode를 이해한다."
    architecture: "static aggregate index가 LAB3 episode bundle을 참조하고 canonical data를 복제하지 않는다."
    security: "public allowlist, path/token scrub, asset hash와 size budget을 배포 전 검사한다."
    qa: "desktop/mobile, filter, denominator, drill-down, live asset/console/network를 검사한다."
    skeptic: "일반 승자·실물·live inference·원인 진단으로 과장하는 문구를 거부한다."
```

## 스캐폴딩 결정

- source-of-truth: GEN1~GEN4 final report와 canonical artifact를 읽어 만든 content-hashed public registry다.
- 검증: local/live Playwright, asset 200/hash, claim negative fixture와 human visual gate를 사용한다.
- frontend: 기존 Vite/React app의 별도 `/generalization-lab` route와 LAB3 components를 재사용한다.
- data: GEN1~GEN4 report에서 deterministic public index를 생성한다.
- design: overview matrix→paired detail→failure patterns→episode drill-down의 세 깊이만 둔다.
- deploy: 기존 Vercel REST path와 `robotics.askewly.com`; persistent backend 없음.
- 관측: `qaGeneralizationSummary()`가 denominator, filters, selected cell, evidence hashes와 claim boundary를 반환한다.
- 검토 후 제외: 3D 환경 재구현, 애니메이션 중심 hero, 모델 점수만 큰 leaderboard.

## 결정 로그

- status: resolved
- resolved: 기본 진입은 “어느 정책이 이겼나”가 아니라 “무엇을 몇 번 비교했나”다.
- resolved: 기존 `/arm-lab`을 episode 상세 화면으로 재사용하고 deep link를 추가한다.
- resolved: 사람 visual gate 후에만 production alias를 갱신한다.

## Step 트리

- [ ] **step-1 — deterministic-public-index**
  - Artifact: aggregate/pattern/episode refs를 content-hashed static registry로 변환하는 allowlist generator.
  - Files: `experiments/154-public-generalization-lab/gen_public_index.py`, public assets/tests, changeset.
  - Dependencies: 없음
  - Verify: 같은 input은 byte-identical registry를 만들고 size/path/token/hash gate를 통과한다.
  - Failure probe: missing denominator, stale episode hash, local path와 unsupported claim이 FAIL한다.
  - Commit: changeset 1 — public generalization bundle.
- [ ] **step-2 — comparison-overview**
  - Artifact: suite/task/policy raw count, success와 paired difference를 보이는 responsive overview.
  - Files: React route/components/styles, QA, changeset.
  - Dependencies: step-1
  - Verify: raw numerator/denominator와 interval이 filter 후에도 registry와 일치한다.
  - Failure probe: rounded-only score, hidden exclusions, zero denominator가 UI QA에서 FAIL한다.
  - Commit: changeset 2 — paired comparison overview.
- [ ] **step-3 — failure-pattern-explorer**
  - Artifact: policy/suite/task/pattern/unknown filters와 evidence-backed representative episodes.
  - Files: failure explorer components/QA, changeset.
  - Dependencies: step-2
  - Verify: 모든 filter count가 GEN4 index와 일치하고 label definition/evidence가 visible하다.
  - Failure probe: unknown 숨김, root-cause wording, success-only sampling이 FAIL한다.
  - Commit: changeset 3 — observable failure explorer.
- [ ] **step-4 — episode-drilldown-linkage**
  - Artifact: selected matrix/pattern cell에서 LAB3 dual-camera causal replay로 내려가는 stable deep link.
  - Files: routing/query adapter, LAB3 integration QA, changeset.
  - Dependencies: step-3
  - Verify: selected policy/task/state와 episode hash가 drill-down summary에서 동일하다.
  - Failure probe: wrong episode, stale hash, camera/policy relabel이 FAIL한다.
  - Commit: changeset 4 — aggregate-to-episode traceability.
- [ ] **step-5 — public-reviewer-release**
  - Artifact: deployed route, desktop/mobile screenshots, live QA와 5분 reviewer checklist.
  - Files: deployment config, `verify/generalization-lab/`, ROADMAP/final report, changeset.
  - Dependencies: step-1, step-2, step-3, step-4
  - Verify: local/live Playwright, asset 200/hash, console/network, claim negative gate와 human visual gate PASS.
  - Failure probe: asset 404, denominator drift, general-winner/live/real/root-cause relabel이 release를 차단한다.
  - Commit: changeset 5 — public multi-task generalization laboratory.

## Verification / DoD

- 공개 브라우저에서 120 episode의 분모와 paired 결과를 suite/task/policy별로 보고 failure pattern과 canonical LAB3 episode까지 추적한다.
