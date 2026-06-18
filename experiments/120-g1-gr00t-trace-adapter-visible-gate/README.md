# 120-g1-gr00t-trace-adapter-visible-gate — GR00T trace adapter visible gate

> `experiments/120-g1-gr00t-trace-adapter-visible-gate/README.md` — 실험은 *가설·방법·결과·통찰* 4섹션.

## 1. 가설 (Hypothesis)

GR00T/SONIC sim2sim을 바로 실행하지 못하더라도, GR00T debug/CSV trace를 physical-ai web trajectory와 exp29 visible gate로 변환하는 adapter를 먼저 닫으면 실제 WBC trace가 생겼을 때 M19 완료 판정을 즉시 반복 가능하게 만들 수 있다.

## 2. 방법 (Method)

### 셋업
- 스택 후보: NVlabs GR00T-WholeBodyControl partial checkout `tmp/gr00t-wbc` (조사용, 커밋 제외).
- 로컬 검증기: `run_gr00t_trace_adapter_visible_gate.py`.
- 실행 환경: Windows 11 + WSL Ubuntu 24.04, `C:\tmp\e34\Scripts\python.exe`.
- 기존 contract: exp33 `physical-ai-web-trajectory-v1`, exp29 visible squat thresholds.

### 웹/문서 근거
- GR00T ZMQ tutorial: external source can stream G1 whole-body joint positions; Protocol v1 uses `joint_pos`/`joint_vel` shape `[N,29]`. 접근일: 2026-06-18. https://nvlabs.github.io/GR00T-WholeBodyControl/tutorials/zmq.html
- GR00T Quick Start: online visualization connects to running `g1_deploy` via `tcp://localhost:5557` topic `g1_debug`; MuJoCo sim2sim runs `run_sim_loop.py` + `deploy.sh sim`. 접근일: 2026-06-18. https://nvlabs.github.io/GR00T-WholeBodyControl/getting_started/quickstart.html

### 시나리오
- V0: GR00T trace source audit — `visualize_motion.py`, ZMQ docs, state logger, ZMQ output handler 존재 확인.
- V1: WSL runtime preflight — Ubuntu, Python, Git, Git LFS, Docker CLI, GPU visibility 확인.
- V2: synthetic GR00T debug trace 생성 — `base_trans_measured`, `base_quat_measured`, `body_q_measured` with 29D MuJoCo-order joints.
- V3: adapter conversion — GR00T debug trace -> `physical-ai-web-trajectory-v1` qpos `[root_xyz, quat, 29 joints]`.
- V4: gate verification — exp33 web trajectory contract + exp29 visible squat metrics.

### 측정 metric
- web contract verdict.
- pelvis drop >= 8cm.
- knee flexion delta >= 0.60rad.
- hip pitch delta >= 0.35rad.
- final height return <= 1.5cm.
- WSL Git LFS/Docker/GPU readiness.

## 3. 결과 (Results)

### 데이터
| Run | Verdict | Cost | Retries | 비고 |
|-----|---------|------|---------|------|
| V0 trace source audit | PASS | local parse | 0 | debug fields and CSV/logger paths identified |
| V1 WSL preflight | PARTIAL | shell | 0 | Ubuntu/Docker/GPU visible, Git LFS broken |
| V2 synthetic trace | PASS | generated | 0 | 151 frames, 50Hz, measured fields |
| V3 web trajectory contract | PASS | local checker | 0 | `physical-ai-web-trajectory-v1` valid |
| V4 visible gate | PASS_SYNTHETIC_ONLY | local metrics | 0 | drop 10cm, knee 0.72rad, hip 0.42rad, return OK |
| Overall | `TRACE_ADAPTER_READY__RUNTIME_PREFLIGHT_PARTIAL` | local audit | 0 | M19 not closed |

### 핵심 수치
- Synthetic pelvis drop: 0.100m.
- Synthetic knee delta: 0.720rad.
- Synthetic hip pitch delta: 0.420rad.
- Synthetic final height error: 0.000m.
- WSL Ubuntu 24.04: available.
- WSL Docker CLI: available.
- WSL GPU: visible (`nvidia-smi` sees RTX 5090).
- WSL Git LFS: broken/missing.

### 박제 위치
- `verify/result.json`
- `verify/summary.md`
- `verify/synthetic_gr00t_debug_trace.json`
- `verify/synthetic_gr00t_motion_dir/`
- `verify/synthetic_gr00t_visible_web_trajectory.json`
- `verify/web_contract_summary.json`
- `verify/visible_gate_summary.json`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- exp119의 "공식 GR00T runtime blocked"는 완전한 환경 부재가 아니었다. WSL Ubuntu, Docker CLI, GPU는 이미 보이고 Git LFS만 먼저 고치면 checkpoint/model acquisition 단계로 갈 수 있다.
- GR00T debug output의 `body_q_measured`/`body_q_target`는 MuJoCo-order 29D body joints로 바로 physical-ai `qpos` 뒤쪽에 들어갈 수 있다. ZMQ input protocol v1의 `joint_pos`는 IsaacLab order라 별도 reorder가 필요하지만, debug output path는 adapter가 단순하다.
- 이번 PASS는 synthetic trace에 대한 adapter/gate PASS다. 실제 controller가 스쿼트를 했다는 증거가 아니므로 M19는 닫히지 않는다.

### 가설은 통과했나?
- [x] PASS — GR00T trace를 web trajectory + visible gate로 판정하는 adapter path가 재현 가능하게 열렸다.
- [ ] FAIL — 해당 없음. 단, M19 완료는 실제 GR00T/SONIC measured trace가 필요하다.

### 정의에 반영
- ROADMAP M19 다음 작업을 "Git LFS fix -> GR00T model download/sim2sim -> real measured trace through exp120 adapter -> exp29/browser replay"로 더 좁힌다.

### 다음 실험 후보
- exp121: WSL에서 Git LFS를 복구하고 GR00T `download_from_hf.py` + sim2sim 최소 실행 preflight를 통과시킨다.
- exp122: `g1_debug` realtime 또는 `StateLogger` CSV를 실제로 캡처해 exp120 adapter에 넣고 visible/contact/slip/return/browser replay를 판정한다.
