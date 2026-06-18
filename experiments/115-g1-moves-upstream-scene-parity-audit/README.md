# 115-g1-moves-upstream-scene-parity-audit — G1 Moves upstream scene parity audit

## 1. 가설 (Hypothesis)

G1 Moves/UniTracker 계열 public tracker를 M19에 연결하려면 ONNX adapter를 더 추정하기 전에 exact training scene, sensor, action, observation parity가 먼저 필요하다. 공개 tree에 `g1_mode15_square.xml`이 없고 로컬 scene 계약이 다르면 native ONNX retry는 또 실패한다.

## 2. 방법 (Method)

### 셋업
- 모델: local `scene_g1_policy.xml` / `g1_mjx_feetonly.xml`.
- 데이터: G1 Moves GitHub/Hugging Face public tree, upstream `run_policy.py`, G1 Moves `CLAUDE.md`, mjlab G1 constants/env cfg, exp99/100/101 native failure evidence.
- 하네스 구성: learning experiment 1개로 `verify/result.json`과 `verify/upstream-scene-parity-summary.md`를 박제한다.

### 웹 근거
- G1 Moves GitHub tree: https://api.github.com/repos/experientialtech/g1-moves/git/trees/main?recursive=1 (accessed 2026-06-18)
- G1 Moves Hugging Face tree: https://huggingface.co/api/datasets/exptech/g1-moves/tree/main?recursive=1 (accessed 2026-06-18)
- G1 Moves `run_policy.py`: https://raw.githubusercontent.com/experientialtech/g1-moves/main/run_policy.py (accessed 2026-06-18)
- G1 Moves README: https://raw.githubusercontent.com/experientialtech/g1-moves/main/README.md (accessed 2026-06-18)
- G1 Moves HF `CLAUDE.md`: https://huggingface.co/datasets/exptech/g1-moves/resolve/main/CLAUDE.md, fallback https://huggingface.co/datasets/exptech/g1-moves/blob/fce747a1677d5e6ffbc45e04f9fbdc0252b276f5/CLAUDE.md (accessed 2026-06-18)
- mjlab G1 constants: https://raw.githubusercontent.com/mujocolab/mjlab/main/src/mjlab/asset_zoo/robots/unitree_g1/g1_constants.py (accessed 2026-06-18)
- mjlab G1 env cfg: https://raw.githubusercontent.com/mujocolab/mjlab/main/src/mjlab/tasks/tracking/config/g1/env_cfgs.py (accessed 2026-06-18)

### 시나리오
- V0: GitHub/Hugging Face tree와 대표 direct URL probe에서 `g1_mode15_square.xml`, XML, ONNX, NPZ, YAML path를 수집한다.
- V1: upstream `run_policy.py`와 HF `CLAUDE.md`에서 exact scene/action/obs contract hit를 수집한다.
- V2: local scene의 actuator/sensor/compile contract를 감사한다.
- V3: exp99/100/101 실패 결과와 합쳐 M19 다음 행동을 결정한다.

### 측정 metric
- exact XML 공개 tree/direct probe 존재 여부.
- local actuator/sensor contract가 upstream runner 전제와 맞는지.
- previous native adapter/public XML/mjlab attempts가 모두 FAIL인지.
- native retry를 해도 되는지 여부.

## 3. 결과 (Results)

### 데이터
| Run | Verdict | 핵심 수치 | 비고 |
|---|---|---|---|
| V0 | EXACT_XML_MISSING_PUBLIC_TREE_OR_DIRECT_PROBES | GitHub/HF tree와 대표 direct probe 모두 `g1_mode15_square.xml` 확보 실패 | 공개 artifact만으로 exact scene parity 불가 |
| V1 | UPSTREAM_CONTRACT_DEPENDS_ON_EXACT_SCENE | `run_policy.py`/HF note에서 exact XML hit 확인 | ONNX만으로 재현 불가 |
| V2 | LOCAL_SCENE_MISMATCH | local base XML is position-actuated; compiled `nu=29`, `nsensor=22` | policy training scene과 다름 |
| V3 | PRIOR_NATIVE_RETRY_FAILED | exp99/100/101 all FAIL | hand adapter sweep 중단 근거 |

최종 verdict: `PARITY_BLOCKED_EXACT_SCENE_NOT_PUBLIC`.

### 박제 위치
- `verify/result.json`
- `verify/upstream-scene-parity-summary.md`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- G1 Moves ONNX는 유효하지만, M19 native 성공의 병목은 ONNX shape가 아니라 exact scene parity다.
- 공개 GitHub/Hugging Face tree와 대표 direct probe에서 `g1_mode15_square.xml`을 찾지 못했다. 따라서 현재 공개 artifact만으로 upstream policy를 exact 재현하는 route는 닫혀 있다.
- 로컬 scene은 position actuator 기반이고, 이전 exp99/100/101 native retry도 모두 실패했다. 같은 방향의 adapter sweep은 M19를 닫을 가능성이 낮다.

### 가설은 통과했나?
- [x] PASS — exact scene parity가 현재 공개 tree/direct probe 기준 막혀 있고, native retry 전제조건이 충족되지 않음을 확인했다.
- [ ] FAIL — 실행 후 판단

### 정의에 반영
- M19 다음 작업은 public ONNX hand adapter가 아니라 local-scene tracker retrain 또는 full-order ID-QP/MPC다.

### 다음 실험 후보
- local `scene_g1_policy.xml` 기준으로 G1 Moves reference window를 teacher/reference로 쓰는 29DOF squat tracker를 새로 학습한다.
- 또는 exp109 static target을 full-order ID-QP/MPC로 직접 추종하되 contact force/floating-base dynamics를 decision variable에 포함한다.
