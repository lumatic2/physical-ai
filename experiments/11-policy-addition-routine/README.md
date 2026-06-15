# 11-policy-addition-routine — policy 추가 루틴 일반화

> M16. M15 Barkour에서 드러난 누락 지점을 checklist와 자동 sanity check로 끌어올린다.

## 1. 가설 (Hypothesis)

새 policy 추가 과정의 반복 gate를 문서와 checker로 고정하면, 다음 Playground policy는 `train -> export -> verify -> bundle -> QA` 경로를 빠뜨린 단계 없이 시작할 수 있다.

반증 기준:
- checklist가 M15의 실제 실패 지점(manifest 누락, command convention, runtime XML mutation bake)을 포착하지 못한다.
- checker가 현재 Go1/G1/Spot/Barkour policy bundle을 통과시키지 못한다.

## 2. 방법 (Method)

### 셋업
- 대상: `experiments/03-digital-twin/experiments.json`의 policy experiments.
- 산출물: `POLICY_ADDITION.md`, `check_policy_bundle.py`, checker raw output.

### 시나리오
- S1: M15에서 발견한 수작업 gate를 checklist로 정리한다.
- S2: registry, scene, ONNX, golden, manifest, required policy fields를 자동 점검하는 checker를 만든다.
- S3: 현재 policy set에 checker를 실행해 PASS를 확인한다.

### 측정 metric
- checker pass/fail, 누락 파일 수, 검증된 policy 수.

## 3. 결과 (Results)

### 데이터
| Run | Verdict | Cost | Retries | 비고 |
|-----|---------|------|---------|------|
| S1 checklist | PASS | - | 0 | `POLICY_ADDITION.md` 작성 |
| S2 checker | PASS | - | 1 | v1은 ONNX/golden manifest 요구가 과도해 수정. scene/XML assets manifest gate로 좁힘 |
| S3 current bundles | PASS | - | 0 | policy 7종 PASS, optional obs_spec warning 6건 |

### 박제 위치
- `verify/policy-bundle-check.txt`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- 새 policy 추가의 실제 deploy blocker는 ONNX 자체보다 `scene XML/assets`가 manifest에 들어갔는지 여부다.
- ONNX/golden은 HTTP fetch 대상이므로 존재 여부는 확인하되 WASM FS manifest gate로 묶지 않는다.
- `obs_history`처럼 stateful obs를 쓰는 policy는 `frames * current_dim == obs_dim`, `command_transform`, `command_scale`을 자동으로 검사할 수 있다.
- 기존 policy 7종은 checker를 통과한다. G1/Go1/Spot의 web asset tree에는 optional `obs_spec.json`이 없어 warning만 남긴다.

### 가설은 통과했나?
- [x] PASS — `python experiments/03-digital-twin/check_policy_bundle.py`가 현재 policy 7종을 통과했다.
- [ ] FAIL — 무엇이 어긋났나, 가설 수정

### 정의에 반영
- `experiments/03-digital-twin/POLICY_ADDITION.md`
- `experiments/03-digital-twin/check_policy_bundle.py`

### 다음 실험 후보
- M17: 같은 command/terrain protocol로 policy gallery 비교표 생성.
