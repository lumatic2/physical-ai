# 31-robotics-lab-gallery-polish — Robotics Lab public gallery polish

> `experiments/31-robotics-lab-gallery-polish/README.md` — 하네스 실행 기록.

## 1. 가설 (Hypothesis)

`robotics.askewly.com`을 실험 번호 중심이 아니라 로봇, 가능한 동작, 증거, 한계 중심으로 재구성하면 방문자가 5분 안에 "무엇을 볼 수 있고 무엇은 아직 아닌지"를 구분할 수 있다.

## 2. 방법 (Method)

### 셋업
- 대상: `experiments/03-digital-twin/web/src/main.js`
- 문서: `experiments/03-digital-twin/web/README.md`, `experiments/README.md`, `ROADMAP.md`
- 하네스 구성: learning 갈래의 experiment 단위로 진행하되, 실제 산출물은 public web gallery UI다.

### 시나리오
- V0: 기존 overlay를 읽고 claim drift를 분류한다.
- V1: overlay 메타데이터를 `robot + motion + evidence + limit` 구조로 재작성한다.
- V2: desktop/mobile live QA로 first viewport, selected robot panel, replay/policy 화면이 깨지지 않는지 확인한다.
- V3: ROADMAP에서 M19는 보류로 고정하고 M23을 public gallery horizon으로 재편한다.

### 측정 metric
- old domain / stale claim 검색 결과.
- live QA PASS 여부.
- G1 lowering probe가 completed squat이 아니라 micro-dip probe로 보이는지.

## 3. 결과 (Results)

### 데이터
| Run | Verdict | Cost | Retries | 비고 |
|-----|---------|------|---------|------|
| V0 | PASS | - | 0 | overlay data model rewritten to robot/motion/evidence/limit |
| V1 | PASS | - | 0 | local G1 policy QA and mobile SO-100 replay QA passed |
| V2 | PASS | - | 0 | live deploy `dpl_FjcwuMkkwUhztEvMM9Si3V9ZpzAW`; live G1 policy, mobile SO-100, and lowering-probe DOM checks passed |

### 박제 위치
- live QA screenshots: `experiments/03-digital-twin/web/qa/out/`
- 주요 검증:
  - `node qa/visual_check.mjs --exp=g1-walk --steps=80 --chunk=40`
  - `node qa/visual_check.mjs --exp=so100-stack --mobile`
  - `node qa/visual_check.mjs --live --exp=g1-walk --steps=80 --chunk=40`
  - `node qa/visual_check.mjs --live --exp=so100-stack --mobile`
  - live DOM audit: lowering probe panel contains `Not a squat`, `Evidence`, `Current limit`, and no old `Robot / experiment` or `Verified / learned` labels.

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- Public gallery의 기본 단위는 exp id가 아니라 robot capability다.
- G1 squat 관련 artifact는 증거로는 가치가 있지만, public UI에서는 반드시 "not a squat" 한계를 같이 보여야 한다.
- 모바일에서는 패널을 60vh 내부 스크롤로 제한해야 3D 장면이 남는다.

### 가설은 통과했나?
- [x] PASS — desktop/mobile live QA와 stale-claim audit 통과.
- [ ] FAIL — 사용자가 여전히 가능한 동작과 보류 동작을 혼동하면 UI 구조를 다시 바꾼다.

### 정의에 반영
- `ROADMAP.md` M23에 public gallery horizon으로 반영한다.

### 다음 실험 후보
- askewly.com 제품 카드도 SO-100 단독 설명에서 Robotics Lab 설명으로 교체한다.
