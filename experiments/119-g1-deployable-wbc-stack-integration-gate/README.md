# 119-g1-deployable-wbc-stack-integration-gate — G1 deployable WBC stack integration gate

> `experiments/119-g1-deployable-wbc-stack-integration-gate/README.md` — 실험은 *가설·방법·결과·통찰* 4섹션.

## 1. 가설 (Hypothesis)

GR00T/SONIC 계열 deployable WBC stack이 Unitree G1 29-DOF body joint contract와 맞고, 기존 exp33 Unitree DDS/browser path도 29-DOF unassisted controller를 받을 수 있다면, M19는 더 이상 hand adapter/short PPO/qfrc smoke 반복이 아니라 GR00T/SONIC sim2sim trace를 exp29 visible gate와 browser replay gate로 흘려보내는 통합 작업으로 전환해야 한다.

## 2. 방법 (Method)

### 셋업
- 모델/스택 후보: NVlabs GR00T-WholeBodyControl partial checkout `tmp/gr00t-wbc` (조사용, 커밋 제외).
- 로컬 검증기: `run_deployable_wbc_stack_integration_gate.py`.
- 기존 evidence: exp33 `unassisted-controller-candidate` browser gate.
- 실행 환경: Windows 11, `C:\tmp\e34\Scripts\python.exe`, `OPENBLAS_NUM_THREADS=1`.

### 웹/문서 근거
- NVlabs/GR00T-WholeBodyControl: G1-capable WBC/SONIC repo, training/eval/deploy/checkpoint/C++ inference stack. 접근일: 2026-06-18. https://github.com/NVlabs/GR00T-WholeBodyControl
- GR00T WBC Quick Start: MuJoCo sim2sim은 host `.venv_sim`, `install_mujoco_sim.sh`, `run_sim_loop.py`, `gear_sonic_deploy/deploy.sh sim` 절차. 접근일: 2026-06-18. https://nvlabs.github.io/GR00T-WholeBodyControl/getting_started/quickstart.html
- GR00T Decoupled WBC docs: Unitree G1 primary support, Ubuntu 22.04, NVIDIA GPU, Docker/NVIDIA Container Toolkit, `run_g1_control_loop.py`. 접근일: 2026-06-18. https://nvlabs.github.io/GR00T-WholeBodyControl/references/decoupled_wbc.html
- unitreerobotics/unitree_mujoco: Unitree SDK2 control program을 MuJoCo simulator와 연결하고 G1 low-level message를 지원. 접근일: 2026-06-18. https://github.com/unitreerobotics/unitree_mujoco

### 시나리오
- V0: GR00T source presence gate — README, docs, sim loop, deploy script, G1 policy params, supplemental info 확인.
- V1: 29-DOF contract gate — GR00T G1 body joint list, default angles, action scale, IsaacLab/MuJoCo reorder arrays, exp33 DDS order를 비교.
- V2: runtime gate — 이 호스트가 공식 문서의 Linux/Docker/Git LFS 실행 경로를 만족하는지 확인.
- V3: browser transport gate — exp33 Unitree RL Lab G1-29DOF unassisted policy -> official MuJoCo -> DDS -> browser candidate PASS 재사용.

### 측정 metric
- source key files present.
- 29 body joints / 29 default angles / 29 action scale entries.
- reorder arrays permutation 0..28.
- GR00T body joint order == exp33 Unitree DDS 29-DOF order.
- exp33 browser candidate verdict.
- direct GR00T runtime readiness.

## 3. 결과 (Results)

### 데이터
| Run | Verdict | Cost | Retries | 비고 |
|-----|---------|------|---------|------|
| V0 source presence | PASS | local parse | 0 | key files all present |
| V1 29-DOF contract | PASS | local parse | 1 | DDS names normalized with `_joint` suffix |
| V2 runtime | BLOCKED | local preflight | 0 | Windows host, Docker absent; docs path expects Linux/Ubuntu + Docker/GPU |
| V3 browser transport | PASS_EXISTING | exp33 evidence | 0 | unassisted G1-29DOF controller candidate browser PASS |
| Overall | `WBC_STACK_CANDIDATE__LOCAL_INTEGRATION_BLOCKED` | local audit | 1 | M19 not closed |

### 핵심 수치
- GR00T G1 body joints: 29.
- GR00T default angles: 29.
- GR00T action scale entries: 29.
- `isaaclab_to_mujoco` / `mujoco_to_isaaclab`: both valid 0..28 permutations.
- GR00T body joint order vs exp33 DDS 29-DOF order: match.
- exp33 unassisted browser candidate: PASS.
- direct official GR00T runtime on current host: FAIL/BLOCKED, because current host is Windows and Docker is not available.

### 박제 위치
- `verify/result.json`
- `verify/deployable-wbc-stack-integration-summary.md`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- 스쿼트 가능성 조사 결과, GR00T/SONIC은 M19에서 볼 만한 가장 현실적인 deployable WBC 후보지만, 현재 세션에서 바로 native visible squat를 만들 수 있는 로컬 runtime은 아니다.
- 중요한 긍정 신호는 29-DOF contract다. GR00T G1 body order가 exp33 Unitree DDS/browser order와 맞으므로 hand adapter/short PPO 반복보다 “GR00T sim2sim trace export -> exp33 browser candidate gate -> exp29 visible metrics”가 다음 실험으로 맞다.
- M19는 아직 열려 있다. 이번 실험은 controller를 실행해 스쿼트를 성공시킨 것이 아니라, 다음 실험의 외부 WBC stack 통합 조건을 닫은 것이다.

### 가설은 통과했나?
- [x] PASS — GR00T/SONIC은 G1 29-DOF WBC 후보이고 로컬 browser transport contract와 맞는다.
- [ ] FAIL — 해당 없음. 단, M19 완료 가설은 이번 실험 범위가 아니며 native visible squat/browser replay는 미달이다.

### 정의에 반영
- ROADMAP M19에 exp119를 추가하고 다음 작업을 Linux/WSL2/Ubuntu GR00T sim2sim trace export 또는 동등한 deployable WBC trace gate로 좁힌다.

### 다음 실험 후보
- exp120: Linux/WSL2 또는 Ubuntu host에서 GR00T/SONIC sim2sim을 Git LFS/model/Docker/GPU 조건으로 실행하고, 29-DOF G1 trace를 exp33 DDS/browser candidate gate와 exp29 visible squat metrics에 통과시킨다.
