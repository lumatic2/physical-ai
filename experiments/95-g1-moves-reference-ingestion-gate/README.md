# 95-g1-moves-reference-ingestion-gate — G1 Moves reference ingestion gate

> M19/M22. exp94가 local stabilizer injection으로는 knee tracking이 부족하다는 것을 보였기 때문에, 외부 retargeted G1 motion/policy dataset을 현재 local G1 qpos/web trajectory contract로 받을 수 있는지 먼저 검증한다.

## 1. 가설 (Hypothesis)

G1 Moves 같은 retargeted Unitree G1 dataset은 local G1 model의 29 joint order와 맞고, visible squat급 knee/hip motion window를 `qpos[36]` web trajectory로 변환할 수 있을 것이다.

## 2. 방법 (Method)

### 셋업
- 모델: local `ContactAwareSquat` MuJoCo G1 model.
- 데이터: Hugging Face `exptech/g1-moves` manifest + selected retargeted CSV.
- 하네스 구성: `run_g1_moves_reference_ingestion_gate.py`, raw evidence under `verify/g1-moves-reference-ingestion-gate/`.

### 웹 근거
- G1 Moves dataset card documents retargeted G1 CSV/PKL, NPZ training references, and trained ONNX policies. URL: https://huggingface.co/datasets/exptech/g1-moves accessed 2026-06-18.
- GMR supports Unitree G1 retargeting/visualization and is tuned for RL tracking policies. URL: https://github.com/YanjieZe/GMR accessed 2026-06-18.
- Recent whole-body humanoid locomotion work combines generated/reference motions with a whole-body reference tracker and deploys on Unitree G1. URL: https://arxiv.org/abs/2604.17335 accessed 2026-06-18.

### 시나리오
- V0: public manifest를 fetch하고 29-DoF joint range metadata가 있는 clips를 rank한다.
- V1: local G1 model `qpos[7:35]` order가 G1 Moves 29 joint order와 일치하는지 검사한다.
- V2: best candidate CSV 하나를 fetch해 36-column `root_pos + root_quat + 29 joints` shape를 검증한다.
- V3: selected 6s window를 `physical-ai-web-trajectory-v1` `qpos[36]` artifact로 변환하고 contract checker를 통과시킨다.

### 측정 metric
- `matches_qpos_7_to_35`
- selected CSV shape `[N, 36]`
- best window root drop, knee range, hip pitch range
- web trajectory contract verdict

## 3. 결과 (Results)

### 데이터
| Run | Verdict | Cost | Retries | 비고 |
|-----|---------|------|---------|------|
| manifest-rank | PASS | web fetch | 1 | `V_PullOver` lacked `joint_range`, skip logic added |
| local-joint-order | PASS | local MuJoCo | 0 | G1 Moves 29 joints map to local `qpos[7:35]` exactly |
| selected-csv | PASS | web fetch | 0 | `J_Dance4_Broadway.csv` shape `[1677, 36]` |
| best-window | PASS reference-like | local NumPy | 0 | 6s window has root drop 0.200m, knee 2.371rad, hip 1.822rad |
| web-contract | PASS | local checker | 1 | checker function API corrected; 360 frames, nq=36, finite/shape valid |

### 박제 위치
- `verify/g1-moves-reference-ingestion-gate/result.json`
- `verify/g1-moves-reference-ingestion-gate/g1-moves-reference-ingestion-summary.md`
- `verify/g1-moves-reference-ingestion-gate/g1_moves_reference_excerpt_web_trajectory.json`
- `verify/g1-moves-reference-ingestion-gate/web-trajectory-contract-check.json`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- G1 Moves의 retargeted CSV는 local G1 qpos order와 바로 맞는다. 별도 joint remap 없이 `root_pos[3] + root_quat[4] + dof_pos[29] -> qpos[36]`로 들어온다.
- 선택된 `J_Dance4_Broadway`는 visible squat gate보다 훨씬 큰 knee/hip/reference motion을 포함한다. 따라서 다음 병목은 reference authoring이 아니라 native dynamics tracker다.
- 이 artifact는 kinematic replay/reference다. M19 완료 evidence가 되려면 이 reference를 native dynamics policy가 추적하고, 그 결과를 browser replay로 검증해야 한다.

### 가설은 통과했나?
- [x] PASS — external retargeted G1 motion ingestion path가 local contract까지 열린다.

### 정의에 반영
- M19 route는 `manual controller -> reference-conditioned tracker / external retargeted policy ingestion`으로 더 좁힌다.

### 다음 실험 후보
- exp96: selected G1 Moves 6s window를 reference-conditioned native tracker target으로 넣고, current stabilizer policy가 아니라 motion imitation objective로 knee >=0.60rad를 직접 추적한다.
- exp96 대안: G1 Moves ONNX policy loading contract를 분석해 local MuJoCo observation/action loop에 연결 가능한지 확인한다.
