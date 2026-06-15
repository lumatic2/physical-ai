# 14-skill-authoring — behavior spec foundation

> M18. Atlas식 skill lab에서 "원하는 동작"을 바로 코드/학습으로 보내지 않고, versioned behavior spec으로 고정한다.

## 1. 가설 (Hypothesis)

G1 skill을 `behavior_spec`으로 먼저 고정하면, `squat`, `front kick`, `ball tap`, `handstand prep` 같은 목표를 reward, scene requirement, metric으로 일관되게 번역할 수 있다.

반증 기준:
- 예시 skill 4개가 같은 schema로 표현되지 않는다.
- compiler가 M19/M21/M22가 쓸 scene requirement와 eval metric을 뽑지 못한다.

## 2. 방법 (Method)

### 셋업
- 모델: local JSON schema + Python stdlib compiler.
- 데이터: `examples/*.json` behavior specs.
- 하네스 구성: `behavior_spec.schema.json`, `compile_behavior.py`.

### 시나리오
- S1: `g1_pose_hold`, `g1_squat`, `g1_front_kick`, `g1_ball_tap` spec을 작성한다.
- S2: compiler가 각 spec을 train/eval config stub으로 변환한다.
- S3: ball/handstand/reference-motion처럼 추가 scene requirement가 필요한 skill을 명시적으로 표시한다.

### 측정 metric
- compiled spec count.
- failed validation count.
- compiled config의 reward terms, scene requirements, eval metrics 존재 여부.

## 3. 결과 (Results)

### 데이터
| Run | Verdict | Cost | Retries | 비고 |
|-----|---------|------|---------|------|
| S1-S3 compile examples | PASS | local Python | 0 | 4개 example spec compile, failed=0 |

### 박제 위치
- `verify/compile-summary.json`
- `verify/*.compiled.json`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- M19는 자연어 목표가 아니라 `g1_squat` 또는 `g1_front_kick` compiled config에서 시작하면 된다.
- M21의 ball skill은 spec 자체가 `ball_body`, `ball_velocity_sensor`, `goal_direction_metric` scene requirement를 요구한다.
- M22의 reference-motion loop는 `track_reference` objective를 schema에 포함해 둬야 후속 skill이 같은 authoring 경로를 탄다.

### 가설은 통과했나?
- [x] PASS — 4개 G1 skill spec이 같은 schema로 compile되고, scene/reward/eval 요구사항이 명시됐다.
- [ ] FAIL — 무엇이 어긋났나, 가설 수정

### 정의에 반영
- `ROADMAP.md` M18을 완료로 갱신하고 M19/M21/M22는 compiled behavior spec을 입력으로 사용한다.

### 다음 실험 후보
- M19: `g1_squat` compiled config로 custom reward wrapper를 만든다.
- M21: `g1_ball_tap` compiled config의 scene requirements를 실제 ball scene으로 구현한다.
