# 최종 보고서 — GEN5 공개 일반화 비교 실험실

> 완료: 2026-07-21 · 대상: GEN5 · 작성: 완료 경계(§B3) — 이 보고서가 완료 의식의 정본이다.

## 1. 문제 정의 (무엇을 왜 하려 했나)

LAB3는 카메라·판단·행동·결과를 한 과제의 PASS/FAIL 기록으로 공개했지만, 그것만으로는 여러 과제에서 정책을 비교했다거나 cherry-pick을 피했다는 사실을 제3자가 확인할 수 없었다. GEN5는 GEN1~GEN4에서 고정하고 실제 실행한 120개 episode의 분모, 두 VLA의 paired 결과, 관측 가능한 실패 양상을 한 공개 화면에 모으고 aggregate cell에서 원 canonical episode까지 내려가 검토할 수 있게 만드는 작업이었다.

## 2. Objective 연결 (북극성과의 관계)

Objective의 “카메라와 센서로 세상을 보고, 언어 지시를 이해하고, 로봇 행동을 생성·실행하며, 그 전 과정을 사람이 관찰할 수 있는 피지컬 AI 실험실”을 단일 데모에서 다과제 비교 플랫폼으로 확장했다. recorded LIBERO simulation이라는 경계 안에서 무엇을 몇 번 비교했고 어디까지 직접 재생할 수 있는지 외부 사람이 확인할 수 있다.

## 3. 경로 (horizon → milestone → steps)

“여러 과제에서 통하는 로봇 판단 실험실” Horizon의 마지막 milestone으로 진행했다. 첫 step에서 GEN1~GEN4 정본을 60 paired cell·120 episode의 content-hashed public index로 만들었다. 두 번째에서 raw numerator/denominator와 paired difference 중심 overview를, 세 번째에서 unknown을 숨기지 않는 failure explorer를 구현했다. 네 번째에서 두 canonical OpenVLA cell을 LAB3 dual-camera replay에 exact provenance로 연결했다. 마지막 step에서 local release gate, 사용자의 시각 확인 생략 승인, Vercel production 배포와 live reviewer gate를 완료했다.

## 4. 구현 결과 (무엇이 만들어졌나)

공개 방문자는 12개 과제와 5개 초기 상태의 60쌍을 suite와 task로 필터링하고 OpenVLA 35/60, π₀.₅-LIBERO 58/60, paired difference +23/60이라는 원시 분모를 함께 본다. 27개 non-success는 `no_progress` 6개와 `unknown` 21개로 완전 집계되며, 정의·predicate·frame·manifest evidence와 판정하지 않은 양상도 노출된다. Spatial task-05의 두 OpenVLA cell에서는 policy, manifest, dataset tree와 dual-camera hash가 일치할 때만 기존 LAB3 PASS/FAIL 기록을 연다. 화면은 recorded simulation을 일반 승자, live inference, real robot 또는 root cause로 재표현하지 않는다.

## 5. 이슈와 해결 (막혔던 것, 어떻게 풀었나)

배포 전 사람의 시각 확인을 필수 gate로 두었으나 사용자가 화면을 보기 어려운 상황이었다. 배포를 추정 진행하지 않고 `decision_required`로 정지한 뒤, 사용자가 직접 확인을 명시적으로 생략하고 배포하도록 승인한 시점에 재개 근거를 ledger에 남겼다. 정지 기록을 처음 적용할 때 반복 JSON 필드의 첫 항목인 과거 LAB1을 잘못 건드릴 뻔했지만 전체 work state 검증에서 즉시 발견해 원상복구하고 GEN5에만 적용했다. 배포 빌드는 500 kB 초과 Three.js chunk 경고를 냈으나 기존 MuJoCo runtime 자산이며 functional gate와 네트워크 검증에는 영향을 주지 않았다.

## 6. 결과물과 증거 (검증 포함)

- Changesets: `changesets/20260721-gen5-deterministic-public-index/`, `changesets/20260721-gen5-comparison-overview/`, `changesets/20260721-gen5-failure-pattern-explorer/`, `changesets/20260721-gen5-episode-drilldown-linkage/`, `changesets/20260721-gen5-public-reviewer-release/`.
- Commits: `40db0f6`, `83ece0f`, `9c20ec4`, `b778fb2`, `fb83234`와 최종 release 마감 commit.
- Public surface: `https://robotics.askewly.com/generalization-lab.html` (접근·검증 2026-07-21).
- Deployment: Vercel `dpl_6eKWczLY8u6U9ByFRBp3hhxKzC3G`, production `READY`, custom alias 연결 PASS.
- Release evidence: `experiments/03-digital-twin/web/verify/generalization-lab/live-release-report.json`; registry SHA-256 `4ab5b110aee5d490a32964f7c696cc49c990eadbde10d10d5733d3b5d428445d`.
- Browser evidence: desktop dark/light와 390×844 mobile screenshot, console error 0, failed response 0, horizontal overflow 0.
- Denominator: 60 paired cells, 120 policy episodes, OpenVLA 35 successes, π₀.₅-LIBERO 58 successes, difference +23, failures 27, unknown 21.
- Drill-down evidence: `experiments/03-digital-twin/web/verify/arm-lab/gen5-live-player-report.json`; 두 source-bound LAB3 episode와 wrong episode/stale manifest/policy-camera relabel rejection PASS.
- 크기 회고: 승인 plan의 5개 step이 5개 changeset으로 닫혔고 public index, overview, failure explorer, drill-down, live release가 각각 독립 검증 표면을 가진다. milestone 인플레가 아니다.
- Horizon 예측 대조: 선언 ~25 cs / 실측 25 cs / 오차 0.
- C09 배포면 검증: 요구·계획 충족(spec) PASS, 구현 품질(quality) PASS. 반복 JSON 필드에 정지 사유를 잘못 적용할 뻔한 near-miss는 전체 work state 검증으로 배포 전에 차단했다.
- 정리: Vercel 임시 업로드 디렉터리는 자동 제거됐고 persistent backend, GPU process, secret 파일은 만들지 않았다. 로컬 Vite 서버는 최종 gate 이후 종료 대상이다.
- 실표면: `https://robotics.askewly.com/generalization-lab.html`에서 desktop dark/light, 390×844 mobile, suite/task filter, 60쌍 분모, 27개 실패 필터와 LAB3 deep link를 실제 Playwright로 조작해 PASS했다.
- 재현: `cd experiments/03-digital-twin/web; GENERALIZATION_LAB_BASE_URL=https://robotics.askewly.com GENERALIZATION_LAB_PREFIX=live node qa/generalization_release_check.mjs; GENERALIZATION_LAB_URL=https://robotics.askewly.com node qa/generalization_drilldown_check.mjs; python qa/arm_lab_player_check.py --url https://robotics.askewly.com/arm-lab --prefix gen5-live`.

## 7. 후속 제안 (다음에 무엇을)

연쇄 2/3 후보는 사용자가 새 언어 지시를 입력하면 local VLM/VLA가 recorded replay가 아니라 실제 시뮬레이터 실행을 만들고 같은 관찰 화면에 남기는 “지시를 바꿔 실행하는 로컬 피지컬 AI 실험실”이다. 연쇄 3/3 후보는 SO-101에서 동일한 명령·카메라·행동·안전·결과 계약을 실제 하드웨어 evidence로 연결하는 “시뮬레이션과 실물을 잇는 검증”이며, 구매·조립·안전 준비라는 외부 gate를 먼저 통과해야 한다.
