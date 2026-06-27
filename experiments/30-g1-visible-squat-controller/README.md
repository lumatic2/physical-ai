# 30-g1-visible-squat-controller — visible-depth G1 squat controller probe

> M19 follow-up after exp29. The visible squat gate is now explicit: the robot must visibly lower, keep both feet in contact, avoid falling, and return upright. This experiment tests whether the existing exp28 calibrated-reference controller can reach that gate by simply lowering the stage target to 0.67m.

## 1. 가설 (Hypothesis)

If the exp28 controller only failed because the stage target was too shallow, then reusing the same calibrated reference/controller with `stage_height=0.67` should produce a visible squat without fall.

Visible squat gate for this probe:
- pelvis/base drop from start >= 0.08m
- `fell_at is None`
- `foot_contact_ratio >= 0.90`
- final height returns to >= 0.74m

반증 기준:
- weak blend stays stable but does not visibly lower.
- strong blend reaches visible depth but falls or cannot return.

## 2. 방법 (Method)

planning_gate:
  team_validation_mode: manual-pass
  spec_delta: "M19 next work moves from exp29 static feasibility into native visible-depth controller probing."
  perspectives:
    product: "사용자가 보는 스쿼트는 최소 8cm 이상 내려가는 동작이어야 한다."
    architecture: "새 reward를 만들기 전에 exp28 controller를 stage 0.67로 재사용해 병목을 분리한다."
    security: "secret 없음. WSL local JAX/MuJoCo environment만 사용한다."
    qa: "native MuJoCo result JSON을 attempt별로 보존하고, visible gate를 수치로 판정한다."
    skeptic: "target을 낮추는 것만으로는 stance/contact/stability 제어가 따라오지 않을 수 있다."
  dod:
    - "stage 0.67 weak/strong controller attempts are preserved under verify/attempts."
    - "summary states whether visible-depth and no-fall can be satisfied together."
    - "next controller direction is explicit."

### 셋업
- Runner: `experiments/28-g1-controlled-squat-stage0p74/run_controlled_squat.py`
- Python: `/home/<user>/playground-go1/.venv/bin/python` in WSL
- Source params: `experiments/22-g1-squat-depth-finetune/verify/train/params.pkl`
- Target stage: `0.67m`
- Reference scale: `1.0`
- Freeze phase: `true`
- Blend schedule: `squat`

### 시나리오
- A: `controller_blend=0.35` — exp28-like stable controller, deeper target.
- B: `controller_blend=1.0` — strong target tracking, same deeper target.

### 측정 metric
- start height, min height, visible drop
- fall time
- contact ratio
- final height / return
- joint limit violation

## 3. 결과 (Results)

### 데이터
| Run | Verdict | Cost | Retries | 비고 |
|-----|---------|------|---------|------|
| stage0p67-scale1p0-blend0p35 | DEPTH_PENDING | WSL JAX/MuJoCo native 6s | 0 | stable/contact 1.00, but drop only 1.19cm |
| stage0p67-scale1p0-blend1p0 | FAIL_FALL | WSL JAX/MuJoCo native 6s | 0 | visible depth reached, but fall at 2.06s |

| Variant | Min height | Visible drop | Fell at | Foot contact | Final height | Verdict |
|---|---:|---:|---:|---:|---:|---|
| blend0.35 | 0.7431m | 0.0119m | never | 1.00 | 0.7499m | DEPTH_PENDING |
| blend1.0 | -0.7702m | >0.08m but invalid fall | 2.06s | 0.92 | -0.7592m | FAIL_FALL |

### 박제 위치
- `verify/attempts/stage0p67-scale1p0-blend0p35/result.json`
- `verify/attempts/stage0p67-scale1p0-blend0p35/native-eval.json`
- `verify/attempts/stage0p67-scale1p0-blend1p0/result.json`
- `verify/attempts/stage0p67-scale1p0-blend1p0/native-eval.json`
- `verify/visible-squat-controller-summary.md`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- Target height를 0.67m로 낮추는 것만으로는 visible squat이 생기지 않는다. exp28-like blend 0.35는 안정적이지만 pelvis drop이 약 1.2cm에 그친다.
- Strong blend 1.0은 8cm 이상 내려가는 구간에 도달하지만 2.06초에 fall한다. 즉 현재 병목은 target depth가 아니라 controlled descent stability다.
- `contact_ratio`만으로는 충분하지 않다. blend1.0은 contact ratio가 0.92로 보이지만 실제로는 넘어진 뒤 접촉이 계속 잡히는 false-positive가 섞인다.
- 다음 controller는 단순 reference blend가 아니라 descent speed cap, COM/support polygon proxy, torso pitch guard, return ramp, fall-aware contact metric을 함께 가져야 한다.

### 가설은 통과했나?
- [ ] PASS — stage 0.67 target만 낮춰도 visible squat이 안정적으로 된다.
- [x] FAIL — weak controller는 안 내려가고, strong controller는 내려가다 넘어진다.

### 정의에 반영
- M19 visible squat completion은 아직 열려 있다. 완료 조건은 visible-depth, no-fall, contact, return이 동시에 통과해야 한다.

### 다음 실험 후보
- `g1-visible-squat-guarded-descent`: blend를 시간으로만 키우지 말고 torso/upright/height/error guard로 descent speed와 max blend를 제한한다.
