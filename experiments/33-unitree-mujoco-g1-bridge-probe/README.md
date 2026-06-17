# 33-unitree-mujoco-g1-bridge-probe - Unitree G1 trace to web twin contract

> M24 follow-up. Unitree MuJoCo/SDK-style G1 state traces must be able to enter the existing web twin without rewriting the viewer.

## 1. 가설 (Hypothesis)

If a Unitree G1 backend can export root pose plus 29 joint positions per frame, then the current `physical-ai-web-trajectory-v1` replay contract can ingest it as `qpos[frame][36]` with a thin adapter.

반증 기준:
- Unitree-style trace cannot be converted to MuJoCo floating-base `qpos` ordering.
- Converted frames do not match `nq=36` for the current G1 web scene.
- The adapter cannot make the source type explicit enough to distinguish mock, native sim, and future telemetry traces.

## 2. 방법 (Method)

### 셋업
- Target contract: `experiments/32-digital-twin-architecture-gate/verify/web-trajectory-contract.json`
- Target web scene: `g1/scene_g1_policy.xml`
- Source layout inspector: `inspect_unitree_mujoco_source.py`
- Headless runtime recorder: `record_unitree_mujoco_g1.py`
- Adapter: `bridge_unitree_trace.py`
- SDK capture contract inspector: `inspect_unitree_sdk2_python_capture_contract.py`
- Live capture normalizer: `normalize_live_lowstate_capture.py`
- Capture producer template: `capture_live_lowstate_jsonl.py`
- Local DDS trace publisher: `publish_mock_unitree_dds.py`
- Unitree MuJoCo DDS publisher: `publish_unitree_mujoco_g1_dds.py`
- Local DDS smoke runner: `run_local_dds_capture_smoke.py`
- Local LowCmd command smoke runner: `run_local_lowcmd_contract_smoke.py`
- Unitree MuJoCo LowCmd closed-loop smoke runner: `run_unitree_mujoco_lowcmd_closed_loop_smoke.py`
- LowCmd browser closed-loop smoke runner: `run_lowcmd_browser_closed_loop_smoke.py`
- Unassisted LowCmd gain sweep runner: `run_unassisted_lowcmd_gain_sweep.py`
- Unitree RL Lab policy browser candidate runner: `run_rl_lab_policy_browser_candidate.py`
- Unitree MuJoCo DDS smoke runner: `run_unitree_mujoco_dds_capture_smoke.py`
- DDS to WebSocket bridge: `stream_dds_to_websocket.py`
- Unitree MuJoCo DDS WebSocket smoke runner: `run_unitree_mujoco_dds_websocket_smoke.py`
- Browser DDS stream QA: `experiments/03-digital-twin/web/qa/dds_stream_check.mjs`
- Live DDS preflight: `preflight_live_dds_capture.py`
- Readiness gate: `check_twin_readiness.py`
- Live demo launcher: `run_live_twin_demo.py`
- External DDS browser candidate gate: `run_external_dds_browser_candidate.py`
- Local stream server: `stream_web_telemetry.py`
- Candidate gate runner: `run_twin_candidate_gate.py`
- LowState synthesizer: `synthesize_lowstate_trace.py`
- LowState adapter: `bridge_lowstate_trace.py`
- Contract verifier: `check_web_trajectory_contract.py`
- Round-trip verifier: `compare_web_trajectories.py`
- Controlled sample: `examples/mock_unitree_g1_trace.json`

### 시나리오
- S1: mock Unitree trace를 `root_pos`, `root_quat`, `joint_pos` arrays로 작성한다.
- S2: adapter가 이를 `fps`, `nq`, `scene`, `qpos` web trajectory로 변환한다.
- S3: 변환 결과가 contract shape, finite values, root quaternion ordering, frame count를 만족하는지 검증한다.
- S4: headless qpos evidence를 telemetry-shaped LowState trace로 합성한다.
- S5: LowState trace를 다시 web trajectory + telemetry sidecar로 변환하고 원본 qpos와 round-trip 차이를 비교한다.
- S6: live capture shape(JSON/JSONL, nested `pose`/`low_state`)를 normalized LowState trace로 변환한 뒤 같은 bridge를 통과시킨다.
- S7: normalized trajectory + telemetry sidecar를 WebSocket stream으로 흘리고 browser viewer가 qpos를 frame-by-frame 갱신하는지 확인한다.
- S8: 실제 capture 후보는 `run_twin_candidate_gate.py` 한 번으로 normalize, bridge, contract, stability gate를 모두 통과해야 한다.
- S9: `capture_live_lowstate_jsonl.py --fixture`로 hardware capture와 같은 JSONL envelope를 생성하고, 그 파일을 candidate gate에 넣어 producer path를 검증한다.
- S10: 공식 `unitree_sdk2_python` source를 검사해 G1 LowState import path, `rt/lowstate`, 35-slot HG motor state, `rt/sportmodestate` position source가 capture template의 전제와 맞는지 확인한다.
- S11: local CycloneDDS/Unitree SDK2 `ChannelPublisher`가 `rt/lowstate`와 `rt/sportmodestate`를 publish하고, capture script가 `ChannelSubscriber`로 받아 candidate gate까지 통과하는지 확인한다.
- S12: official Unitree G1 MJCF를 headless MuJoCo runtime으로 step하면서 `rt/lowstate`와 `rt/sportmodestate`를 publish하고, capture script가 DDS로 받아 candidate gate까지 통과하는지 확인한다.
- S13: DDS LowState/SportModeState를 파일 capture 없이 browser-compatible WebSocket `physical-ai-stream-frame-v0`로 직접 변환해 stream smoke를 통과하는지 확인한다.
- S14: direct DDS->WebSocket stream을 실제 browser viewer에 연결해 MuJoCo qpos, telemetry panel, stream QA stats가 통과하는지 Playwright로 확인한다.
- S15: readiness gate가 assisted demo-ready 상태와 unassisted/real completion evidence를 분리해 판정하는지 확인한다.
- S16: live demo launcher가 assisted sim publisher + DDS bridge + web viewer URL을 one command로 구성하는지 dry-run으로 확인한다.
- S17: external DDS publisher를 기다리는 browser candidate gate가 real robot/unassisted completion artifact 위치에 summary를 쓸 수 있는지 확인한다.
- S18: simulated external DDS publisher를 별도 프로세스로 띄워 external browser candidate gate의 PASS path를 검증하되, real completion evidence로 승격하지 않는다.
- S19: G1 HG `LowCmd` zero-hold command를 `rt/lowcmd`에 publish하고 local subscriber로 받아 command path contract를 검증한다.
- S20: G1 HG `LowCmd`를 Unitree MuJoCo runtime에 먹이고, 그 runtime이 publish한 `LowState`/`SportModeState` capture를 candidate gate에 통과시킨다.
- S21: G1 HG `LowCmd`가 구동한 Unitree MuJoCo runtime의 DDS state를 WebSocket bridge로 흘려 browser viewer QA까지 통과시킨다.
- S22: 같은 LowCmd browser loop에서 elastic-band support를 끄고 unassisted completion 가능성을 검사한다.
- S23: unassisted LowCmd browser loop의 gain 후보를 sweep해 completion 후보가 있는지 확인한다.
- S24: Unitree RL Lab G1-29DOF velocity ONNX policy를 Python publisher에 흡수해 elastic-band 없이 official Unitree MuJoCo -> DDS -> browser candidate gate를 통과시키는지 확인한다.

### Live capture input contract

실제 DDS/SDK 캡처는 다음 최소 필드를 가져야 web twin 입력으로 인정한다.

- `t` 또는 `tick`: frame time/order
- `root_pos[3]`: floating-base world position
- `root_quat[4]`: floating-base world quaternion, normalized by the ingest script
- `motor_state[29]`: each joint with `q`, optional `dq`, optional `tau_est`

주의: Unitree `LowState` joint telemetry만으로는 floating-base root pose가 부족하다. 실제 디지털 트윈 capture에는 mocap, odometry, simulator state, 또는 별도 pose estimator에서 온 root pose가 함께 들어와야 한다.

`capture_live_lowstate_jsonl.py`는 두 가지 root pose source를 지원한다.

- `--root-pose-source jsonl`: 외부 pose estimator/mocap/sim log가 만든 `root_pos`, `root_quat` JSONL을 LowState와 frame index로 결합한다.
- `--root-pose-source sportmode`: Unitree SDK2-style `rt/sportmodestate.position`과 `rt/lowstate.imu_state.quaternion`을 결합한다. 이 옵션은 Unitree MuJoCo bridge와 맞지만, 실제 로봇에서는 pose 의미와 좌표계를 별도 검증해야 한다.

### 측정 metric
- `frames`
- `nq`
- `duration_s`
- `root_height_drop_m`
- `shape_valid`
- `finite_valid`
- `contract_valid`

## 3. 결과 (Results)

### 데이터
| Run | Verdict | Cost | Retries | 비고 |
|-----|---------|------|---------|------|
| mock-unitree-g1-trace | PASS | local Python | 0 | Unitree-style 4-frame trace를 web `qpos[frame][36]`로 변환 |
| web-contract-check | PASS | local Python | 0 | converted trajectory shape/finite/nq/fps/scene 검증 |
| unitree-source-layout | PASS | temp Git clone | 0 | G1 29DOF source has 1 free joint + 29 hinge joints + 29 motors/sensors in expected order |
| unitree-headless-runtime | PASS_BRIDGE / FAIL_STABILITY | local MuJoCo 3.9.0 + temp Git clone | 0 | Unitree G1 scene loads as nq=36/nu=29 and records web-compatible qpos rollout, but PD hold collapses from 0.793m to 0.411m in 2s |
| unitree-web-replay-qa | PASS | local Playwright | 0 | `?exp=unitree-g1-headless` loads and samples frames 0/33/65/99 with nq=36, console errors=0 |
| unitree-lowstate-synthesis | PASS | local Python | 0 | Headless qpos evidence converted to `unitree-g1-lowstate-trace-v0` with 100 frames and 29 motor states |
| unitree-lowstate-bridge | PASS | local Python | 0 | LowState-like input converted to web trajectory plus `physical-ai-g1-telemetry-sidecar-v0` |
| unitree-lowstate-roundtrip | PASS | local Python | 0 | Original headless qpos vs LowState-bridged qpos: 3,600 values compared, max abs diff 0.0 |
| unitree-web-telemetry-qa | PASS | local Playwright | 0 | Viewer loads the telemetry sidecar and displays frame/tick/height/max-joint-velocity readout for `unitree-g1-headless` |
| unitree-live-normalize | PASS | local Python | 0 | Capture-shaped LowState trace normalized with 100 frames, 29 joints, 50Hz estimate, monotonic time |
| unitree-live-normalized-roundtrip | PASS | local Python | 0 | Normalized capture -> web trajectory matches original headless qpos within 1.2e-15 max abs diff |
| unitree-live-nested-jsonl | PASS | local Python | 1 | Nested JSONL fixture (`pose` + `low_state.motor_state`) normalizes and bridges to web contract; first retry fixed JSONL detection |
| unitree-web-stream-qa | PASS | local Playwright + WebSocket | 1 | Viewer receives streamed qpos/telemetry frames, updates MuJoCo qpos and overlay; first retry fixed stream hello handling |
| unitree-elastic-stand | PASS_ASSISTED | local MuJoCo 3.9.0 + Playwright + WebSocket | 0 | Official Unitree G1 scene with Unitree-style elastic-band support holds height within 0.096mm drop; web replay and stream QA PASS |
| unitree-stream-quality-gate | PASS / FAIL_EXPECTED | local Playwright + WebSocket | 0 | Assisted stand passes 40-frame stream quality gate (`fps>=20`, ordered ticks, height range <=1cm); collapsing trace fails height stability with 0.311m range |
| unitree-candidate-gate | PASS / FAIL_EXPECTED | local Python | 1 | One-command candidate gate passes assisted stand and rejects collapsing PD-hold trace; first retry fixed checker import name |
| unitree-capture-producer-fixture | PASS | local Python | 0 | Capture producer emits JSONL with `pose` + `low_state`; candidate gate passes 100 frames at 50Hz, height range 0.004246m |
| unitree-sdk2-python-capture-contract | PASS | official GitHub checkout | 0 | `unitree_sdk2_python` head `4f12b013...` has G1 HG LowState/LowCmd imports, `rt/lowstate` subscriber, `rt/lowcmd` publisher, 35 motor slots, and SportModeState position[3] |
| unitree-live-dds-preflight | PASS | local Python + pip `cyclonedds` | 1 | Preflight initially failed because `cyclonedds` was missing; after install, SDK channel/IDL imports and Unitree G1 scene checks PASS |
| unitree-local-dds-capture-smoke | PASS | local CycloneDDS + Unitree SDK2 checkout | 1 | Local `ChannelPublisher` -> `ChannelSubscriber` capture -> candidate gate PASS; auto interface works, explicit `lo` failed on Windows |
| unitree-local-lowcmd-contract-smoke | PASS | local CycloneDDS + Unitree SDK2 checkout | 0 | Local `rt/lowcmd` G1 HG LowCmd target-hold publisher/subscriber round-trip PASS with 30 frames, 29 enabled motors, 35 HG slots, nonzero CRC |
| unitree-mujoco-lowcmd-closed-loop-smoke | PASS_ASSISTED | local MuJoCo + CycloneDDS + Unitree SDK2 checkout | 0 | DDS `rt/lowcmd` initial-q hold drives Unitree MuJoCo runtime; runtime receives 124 LowCmd messages and captured LowState/SportModeState passes candidate gate with 100 frames, 48.84fps, height range 0.00414m |
| unitree-lowcmd-browser-closed-loop-smoke | PASS_ASSISTED | local MuJoCo + CycloneDDS + WebSocket + Playwright | 0 | DDS `rt/lowcmd` initial-q hold drives Unitree MuJoCo runtime; browser external DDS candidate receives 88 frames, 51.80fps, ordered ticks, height range 0.00283m |
| unitree-lowcmd-browser-unassisted-smoke | FAIL_EXPECTED | local MuJoCo + CycloneDDS + WebSocket + Playwright | 0 | Same LowCmd browser loop without elastic-band support fails height stability: transport/control topics work, but browser height range is 0.03663m and root height drops about 0.600m |
| unitree-unassisted-lowcmd-gain-sweep | FAIL_EXPECTED | local MuJoCo + CycloneDDS + WebSocket + Playwright | 0 | Three unassisted gain candidates all fail browser height stability; best score was kp=0.5,kd=1.0 with height range 0.06685m and root drop 0.639m |
| unitree-mujoco-dds-elastic-smoke | PASS_ASSISTED | local MuJoCo + CycloneDDS + Unitree SDK2 checkout | 0 | Official G1 MJCF headless runtime publishes DDS; capture/candidate gate PASS with 100 frames, 48.85fps, height range 0.004246m |
| unitree-mujoco-dds-collapse-smoke | FAIL_EXPECTED | local MuJoCo + CycloneDDS + Unitree SDK2 checkout | 0 | Same runtime DDS path rejects unassisted PD hold: height range/root drop 0.4084m |
| unitree-mujoco-dds-websocket-elastic-smoke | PASS_ASSISTED | local MuJoCo + CycloneDDS + WebSocket | 1 | DDS LowState/SportModeState streamed directly as `physical-ai-stream-frame-v0`; 75 frames received, qpos[36] valid, height range 0.004246m |
| unitree-mujoco-dds-websocket-collapse-smoke | FAIL_EXPECTED | local MuJoCo + CycloneDDS + WebSocket | 1 | Same direct DDS->WebSocket path rejects unassisted PD hold; height range 0.4080m and fps below 20 threshold |
| unitree-browser-dds-stream-elastic | PASS_ASSISTED | Playwright + local web + DDS WebSocket | 1 | Browser viewer receives direct DDS stream, applies qpos to MuJoCo, telemetry readout updates; repeated DDS ticks tracked separately from out-of-order |
| unitree-browser-dds-stream-collapse | FAIL_EXPECTED | Playwright + local web + DDS WebSocket | 0 | Browser viewer receives collapse stream but height range gate fails (`0.0189m` over sampled window) |
| unitree-twin-readiness | PARTIAL_ASSISTED -> COMPLETE | local Python | 0 | Initially separated demo-ready assisted evidence from completion; final run reads unassisted Unitree RL Lab policy candidate as completion evidence |
| unitree-live-demo-launcher | PASS_DRY_RUN | local Python | 0 | One command assembles web server, DDS bridge, optional Unitree MJCF publisher, and browser URL |
| unitree-external-dds-candidate-no-source | FAIL_EXPECTED | local Python + Playwright | 0 | External candidate wrapper writes failure summary when no real DDS publisher is present; rerun with real robot DDS on the same domain |
| unitree-external-dds-simulated-source-smoke | PASS | local Python + Playwright + CycloneDDS | 1 | Simulated external Unitree MJCF publisher proves the external browser candidate PASS path without writing real completion directories; retry changed process order so live ticks were not repeated |
| unitree-rl-lab-policy-browser-candidate | PASS | Unitree RL Lab ONNX + MuJoCo + CycloneDDS + Playwright | 1 | Official Unitree RL Lab G1-29DOF velocity policy drives official Unitree MuJoCo without elastic-band; browser external DDS candidate PASS with repeatedTicks=0, measured fps 42.12, heightRange 0.00011m |
| unitree-twin-readiness-final | COMPLETE | local Python | 0 | Readiness gate now has unassisted controller candidate evidence; real robot telemetry remains future work |

### 박제 위치
- `verify/mock_unitree_g1_web_trajectory.json`
- `verify/bridge-probe-summary.json`
- `verify/web-contract-check.json`
- `verify/unitree-source-layout.json`
- `verify/unitree_headless_g1_web_trajectory.json`
- `verify/unitree-headless-summary.json`
- `verify/unitree-headless-contract-check.json`
- `verify/unitree-web-registered-contract-check.json`
- `verify/unitree-web-replay-qa.json`
- `verify/unitree_headless_lowstate_trace.json`
- `verify/unitree-lowstate-synthesis-summary.json`
- `verify/unitree_lowstate_web_trajectory.json`
- `verify/unitree_lowstate_telemetry_sidecar.json`
- `verify/unitree-lowstate-bridge-summary.json`
- `verify/unitree-lowstate-contract-check.json`
- `verify/unitree-lowstate-roundtrip-compare.json`
- `verify/unitree-web-telemetry-qa.json`
- `verify/unitree-live-normalized-lowstate-trace.json`
- `verify/unitree-live-normalize-summary.json`
- `verify/unitree-live-normalized-web-trajectory.json`
- `verify/unitree-live-normalized-telemetry-sidecar.json`
- `verify/unitree-live-normalized-bridge-summary.json`
- `verify/unitree-live-normalized-contract-check.json`
- `verify/unitree-live-normalized-roundtrip-compare.json`
- `verify/unitree-live-nested-jsonl-fixture.ndjson`
- `verify/unitree-live-nested-jsonl-normalized-trace.json`
- `verify/unitree-live-nested-jsonl-normalize-summary.json`
- `verify/unitree-live-nested-jsonl-web-trajectory.json`
- `verify/unitree-live-nested-jsonl-telemetry-sidecar.json`
- `verify/unitree-live-nested-jsonl-bridge-summary.json`
- `verify/unitree-live-nested-jsonl-contract-check.json`
- `verify/unitree-web-stream-qa.json`
- `verify/unitree_elastic_stand_web_trajectory.json`
- `verify/unitree-elastic-stand-summary.json`
- `verify/unitree-elastic-stand-contract-check.json`
- `verify/unitree_elastic_stand_lowstate_trace.json`
- `verify/unitree-elastic-stand-lowstate-summary.json`
- `verify/unitree_elastic_stand_telemetry_sidecar.json`
- `verify/unitree-elastic-stand-bridge-summary.json`
- `verify/unitree-elastic-stand-roundtrip-compare.json`
- `verify/unitree-elastic-stand-web-replay-qa.json`
- `verify/unitree-elastic-stand-web-stream-qa.json`
- `verify/unitree-elastic-stand-stream-quality-qa.json`
- `verify/unitree-collapse-stream-quality-qa.json`
- `verify/candidate-gate-elastic-stand/candidate_gate_summary.json`
- `verify/candidate-gate-collapse/candidate_gate_summary.json`
- `verify/unitree-elastic-stand-capture-fixture.jsonl`
- `verify/candidate-gate-capture-fixture/candidate_gate_summary.json`
- `verify/unitree-sdk2-python-capture-contract.json`
- `verify/live-dds-capture-preflight.json`
- `verify/local-dds-capture-smoke/local_dds_capture_smoke_summary.json`
- `verify/local-dds-capture-smoke/local_dds_capture.jsonl`
- `verify/local-dds-capture-smoke/candidate_gate/candidate_gate_summary.json`
- `verify/local-lowcmd-contract-smoke.json`
- `verify/unitree-mujoco-lowcmd-closed-loop-smoke/unitree_mujoco_lowcmd_closed_loop_smoke_summary.json`
- `verify/unitree-mujoco-lowcmd-closed-loop-smoke/candidate_gate/candidate_gate_summary.json`
- `verify/lowcmd-browser-closed-loop-smoke/lowcmd_browser_closed_loop_smoke_summary.json`
- `verify/lowcmd-browser-closed-loop-smoke/browser_candidate_gate/candidate_gate_summary.json`
- `verify/lowcmd-browser-unassisted-smoke/lowcmd_browser_closed_loop_smoke_summary.json`
- `verify/lowcmd-browser-unassisted-smoke/browser_candidate_gate/candidate_gate_summary.json`
- `verify/unassisted-lowcmd-gain-sweep/unassisted_lowcmd_gain_sweep_summary.json`
- `verify/unitree-mujoco-dds-elastic-smoke/unitree_mujoco_dds_capture_smoke_summary.json`
- `verify/unitree-mujoco-dds-elastic-smoke/unitree_mujoco_dds_capture.jsonl`
- `verify/unitree-mujoco-dds-elastic-smoke/candidate_gate/candidate_gate_summary.json`
- `verify/unitree-mujoco-dds-collapse-smoke/unitree_mujoco_dds_capture_smoke_summary.json`
- `verify/unitree-mujoco-dds-collapse-smoke/candidate_gate/candidate_gate_summary.json`
- `verify/unitree-mujoco-dds-websocket-elastic-smoke/unitree_mujoco_dds_websocket_smoke_summary.json`
- `verify/unitree-mujoco-dds-websocket-collapse-smoke/unitree_mujoco_dds_websocket_smoke_summary.json`
- `experiments/03-digital-twin/web/qa/out/unitree-g1-elastic-stand_elastic_dds_stream_summary.json`
- `experiments/03-digital-twin/web/qa/out/unitree-g1-elastic-stand_elastic_dds_stream.png`
- `experiments/03-digital-twin/web/qa/out/unitree-g1-elastic-stand_collapse_dds_stream_summary.json`
- `experiments/03-digital-twin/web/qa/out/unitree-g1-elastic-stand_collapse_dds_stream.png`
- `verify/twin-readiness.json`
- `verify/external-dds-no-source-smoke/candidate_gate_summary.json`
- `verify/external-dds-simulated-source-smoke/external_dds_candidate_smoke_summary.json`
- `verify/external-dds-simulated-source-smoke/external_candidate_gate/candidate_gate_summary.json`
- `verify/rl-lab-policy-browser-candidate/rl_lab_policy_browser_candidate_summary.json`
- `verify/unassisted-controller-candidate/candidate_gate_summary.json`
- `verify/unassisted-controller-candidate/browser_candidate_gate/candidate_gate_summary.json`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- 현재 web twin은 backend source를 알 필요 없이 `qpos[frame][nq]`만 맞으면 replay할 수 있다.
- G1 29-DoF trace는 floating-base root pose 7개와 joint position 29개를 합치면 현재 web scene의 `nq=36`에 맞는다.
- Unitree G1 29DOF MJCF의 motor order와 jointpos sensor order는 `g1_joint_index_dds.md`의 29DOF 순서와 일치한다.
- Unitree G1 MJCF 자체는 로컬 MuJoCo에서 `nq=36`, `nu=29`로 load되고, headless rollout을 현재 web trajectory contract로 바로 출력할 수 있다.
- 단, 단순 PD hold headless rollout은 안정 직립이 아니다. root height가 2초 동안 `0.793m -> 0.411m`로 내려가므로, 이 artifact는 bridge evidence이지 controller evidence가 아니다.
- 이 trajectory는 실제 web registry에 `unitree-g1-headless`로 등록되어 local browser replay QA를 통과했다.
- LowState-shaped trace adapter도 통과했다. 다만 이번 LowState는 headless qpos에서 합성한 trace이므로 실제 DDS capture evidence는 아니다.
- 합성 LowState sidecar는 이제 viewer에서도 소비된다. 웹 overlay는 현재 replay frame의 tick, root height, max joint velocity를 표시한다.
- live capture normalizer를 추가하면서 실제 캡처 acceptance gate가 명확해졌다. root pose가 없는 joint-only LowState는 web twin trajectory로 승격하지 않는다.
- JSONL 로그는 첫 글자가 `{`여도 full JSON object가 아닐 수 있다. normalizer는 full JSON parse 실패 시 line-by-line JSONL로 fallback한다.
- viewer는 이제 `?stream=ws://...` query로 local WebSocket state stream을 받을 수 있다. static replay와 별개로 qpos가 stream frame에 의해 갱신되는 path가 생겼다.
- 안정적인 public/backend fixture는 확보했다. Unitree simulator의 humanoid elastic-band support와 같은 방식으로 G1 standing trace를 만들면 root height drop이 `0.000096m`에 그치고, replay/stream이 모두 통과한다.
- 단, 이것은 assisted fixture다. unassisted standing controller 또는 실제 DDS capture 성공으로 표현하면 안 된다.
- stream QA는 이제 단순 수신 여부가 아니라 frame order, measured fps, height range를 본다. 같은 stream plumbing에서도 collapse trace는 `heightRange=0.311m`로 stability gate를 실패한다.
- `run_twin_candidate_gate.py`가 실제 캡처 acceptance path를 명령 하나로 묶는다. 후보 capture는 normalize -> bridge -> web contract -> height stability를 모두 통과해야 twin candidate로 승격된다.
- `capture_live_lowstate_jsonl.py`는 hardware producer의 템플릿이다. 현재 fixture mode는 통과했지만, hardware mode는 Unitree SDK와 별도 root-pose source가 있어야 한다.
- capture template은 공식 `unitree_sdk2_python` 예제 구조와 정렬했다. G1은 `unitree_sdk2py.idl.unitree_hg.msg.dds_.LowState_`와 `rt/lowstate`를 쓰고, HG LowState는 35 motor slots를 제공하므로 29DOF G1은 앞 29개를 사용한다.
- Unitree MuJoCo bridge는 `rt/sportmodestate.position`도 publish하므로 sim-backed live twin 후보에서는 root position을 DDS topic으로 받을 수 있다. 다만 실제 robot digital twin에서는 이 position의 frame/quality를 별도 gate로 검증해야 한다.
- 로컬 DDS loop는 이제 실제로 열린다. `publish_mock_unitree_dds.py`가 SDK2 `ChannelPublisher`로 LowState/SportModeState를 publish하고, `capture_live_lowstate_jsonl.py`가 `ChannelSubscriber`로 받아 JSONL을 만들며, 그 JSONL은 candidate gate를 통과한다.
- Command path도 최소 계약은 열린다. `run_local_lowcmd_contract_smoke.py`는 G1 HG `LowCmd` target-hold를 `rt/lowcmd`에 publish하고 같은 DDS domain의 subscriber가 35-slot message, 29 enabled motor commands, finite gains, nonzero CRC를 확인한다.
- State와 command가 같은 runtime에서 닫힌다. `run_unitree_mujoco_lowcmd_closed_loop_smoke.py`는 `rt/lowcmd` initial-q hold command를 Unitree MuJoCo runtime에 넣고, 그 runtime이 낸 `LowState`/`SportModeState` capture를 candidate gate까지 통과시킨다.
- Browser까지 같은 loop가 이어진다. `run_lowcmd_browser_closed_loop_smoke.py`는 `LowCmd -> Unitree MuJoCo -> LowState/SportModeState -> DDS WebSocket -> browser viewer` 경로를 external DDS candidate mode로 검증한다.
- 같은 loop에서 elastic-band support를 끄면 browser candidate gate가 실패한다. 이는 DDS transport 실패가 아니라 unassisted controller/stability 실패이며, full digital twin completion으로 승격할 수 없다.
- 단순 LowCmd gain sweep도 unassisted completion 후보를 찾지 못했다. 따라서 다음 breakthrough는 gain만 키우는 것이 아니라 stabilizer/controller design 또는 실제 robot telemetry path다.
- Unitree RL Lab에는 G1-29DOF velocity ONNX policy와 deploy YAML이 포함되어 있다. 이를 Python publisher에 흡수하니 단순 LowCmd hold/gain sweep과 달리 elastic-band 없이 official Unitree MuJoCo에서 안정적인 state stream을 만들 수 있었다.
- `run_rl_lab_policy_browser_candidate.py`는 이 policy를 50Hz로 실행하고, `LowState`/`SportModeState` DDS를 browser external candidate gate에 공급한다. canonical run은 domain 95에서 100-frame browser PASS, repeatedTicks 0, measured fps 42.12, heightRange 0.00011m, publisher root height drop 0.00585m를 기록했다.
- Unitree MJCF headless runtime도 DDS loop로 열린다. `publish_unitree_mujoco_g1_dds.py`가 official G1 scene을 step하면서 LowState/SportModeState를 publish하고, capture/candidate gate가 이를 받는다.
- 같은 runtime DDS path에서 elastic-band assisted stand는 PASS하고 unassisted PD hold는 FAIL_EXPECTED다. 따라서 새 gate는 simulator plumbing뿐 아니라 stability gate로도 작동한다.
- 파일 capture 없이도 live stream path가 열린다. `stream_dds_to_websocket.py`는 DDS LowState/SportModeState를 직접 `physical-ai-stream-frame-v0` WebSocket frame으로 변환한다.
- Browser viewer도 direct DDS stream을 실제로 소비한다. `dds_stream_check.mjs`는 local web server, DDS bridge, Unitree MJCF publisher를 띄우고 Playwright로 `window.demo.qaStreamStatus()`와 telemetry readout을 검증한다.
- DDS tick은 bridge sampling보다 느리거나 빠를 수 있어 같은 tick이 반복될 수 있다. viewer는 repeated tick과 out-of-order tick을 분리해 기록한다.
- DDS smoke를 병렬로 돌릴 때 같은 domain/topic을 공유하면 assisted/collapse stream이 섞인다. WebSocket smoke는 domain id를 분리해 순차 실행해야 한다.
- readiness gate는 현재 상태를 `COMPLETE`로 판정한다. state path, command path, collapse rejection, 그리고 unassisted Unitree RL Lab policy browser candidate가 모두 통과했기 때문이다. 단, real robot telemetry는 별도 future evidence다.
- `run_live_twin_demo.py`는 local assisted demo를 여는 운영 entrypoint다. real robot 사용 시에는 `--publisher external`로 같은 DDS domain에 실제 `rt/lowstate`/`rt/sportmodestate`를 공급해야 한다.
- `run_external_dds_browser_candidate.py`는 completion 후보를 만드는 entrypoint다. real robot 또는 unassisted controller가 같은 DDS domain에 publish 중일 때 이 gate가 PASS하면 readiness gate가 full completion evidence로 읽는다.
- Windows에서는 Unitree 예제의 `lo` interface가 CycloneDDS interface와 매칭되지 않았다. interface를 지정하지 않는 auto mode가 local smoke를 통과했다.
- 다음 실제 backend probe는 real robot DDS `LowState`/root pose capture다.
- 이 단계는 real-robot telemetry twin은 아니다. 다만 simulated controller-backed G1 digital twin gate는 닫혔다.

### 가설은 통과했나?
- [x] PASS - mock Unitree-style trace는 current web trajectory contract로 변환된다.
- [x] PASS - 실제 Unitree MuJoCo MJCF는 headless qpos runtime trace로 연결했다.
- [x] PASS - 합성 LowState-shaped trace는 web trajectory + telemetry sidecar로 round-trip 변환된다.
- [x] PASS - telemetry sidecar가 viewer overlay에서 frame-synchronized readout으로 표시된다.
- [x] PASS - capture-shaped JSON/JSONL input을 normalized LowState contract로 받는 ingest gate가 생겼다.
- [x] PASS - local WebSocket telemetry stream이 viewer qpos와 overlay를 갱신한다.
- [x] PASS_ASSISTED - elastic-band supported stable G1 stand fixture가 replay/stream QA를 통과한다.
- [x] PASS - stream quality gate가 stable fixture와 unstable trace를 구분한다.
- [x] PASS - one-command candidate gate가 stable fixture와 unstable trace를 구분한다.
- [x] PASS - capture producer fixture JSONL이 candidate gate를 통과한다.
- [x] PASS - capture producer의 SDK import/topic assumptions가 공식 `unitree_sdk2_python` source와 맞는다.
- [x] PASS - local DDS publisher/subscriber capture smoke가 candidate gate를 통과한다.
- [x] PASS - local LowCmd command publisher/subscriber smoke가 G1 HG command contract를 통과한다.
- [x] PASS_ASSISTED - DDS LowCmd -> Unitree MuJoCo runtime -> DDS LowState capture -> candidate gate closed loop가 통과한다.
- [x] PASS_ASSISTED - DDS LowCmd -> Unitree MuJoCo runtime -> DDS WebSocket -> browser viewer closed loop가 통과한다.
- [x] FAIL_EXPECTED - 같은 browser closed loop에서 elastic-band support를 끄면 height stability gate를 실패한다.
- [x] FAIL_EXPECTED - unassisted LowCmd gain sweep도 browser height stability gate를 통과한 후보가 없다.
- [x] PASS_ASSISTED - official Unitree G1 MJCF headless runtime -> DDS capture -> candidate gate가 assisted stand에서 통과한다.
- [x] FAIL_EXPECTED - 같은 runtime DDS path에서 unassisted PD hold collapse를 gate가 거부한다.
- [x] PASS_ASSISTED - official Unitree G1 MJCF headless runtime -> DDS -> WebSocket stream이 browser-compatible frame smoke를 통과한다.
- [x] FAIL_EXPECTED - 같은 direct DDS->WebSocket path에서 unassisted PD hold collapse를 stream gate가 거부한다.
- [x] PASS_ASSISTED - browser viewer가 direct DDS->WebSocket stream을 받아 qpos/telemetry를 갱신하고 Playwright QA를 통과한다.
- [x] FAIL_EXPECTED - browser viewer QA가 unassisted collapse stream을 height gate로 거부한다.
- [x] COMPLETE - readiness gate가 unassisted Unitree RL Lab policy browser candidate를 full simulated controller-backed twin evidence로 읽는다.
- [x] PASS_DRY_RUN - live demo launcher가 assisted sim publisher + DDS bridge + web URL을 구성한다.
- [x] FAIL_EXPECTED - external DDS browser candidate gate는 외부 publisher가 없으면 실패 summary를 남긴다.
- [x] PASS - simulated external DDS publisher를 별도 프로세스로 띄우면 browser candidate gate가 external mode에서 통과한다.
- [x] PASS - Unitree RL Lab G1-29DOF velocity policy가 official Unitree MuJoCo를 elastic-band 없이 구동하고 browser external DDS candidate gate를 통과한다.
- [ ] PENDING - 실제 robot DDS `LowState`/root pose telemetry trace는 아직 연결하지 않았다.

### 정의에 반영
- M24 다음 구현은 Unitree MuJoCo 설치/실행 자체보다 먼저 "trace export contract" 검증으로 시작한다.

### 다음 실험 후보
- 실제 `unitreerobotics/unitree_mujoco` checkout에서 G1 standing/walk trace를 export한다.
- 실제 DDS `LowCmd`/`LowState` + root pose trace를 `run_twin_candidate_gate.py`에 통과시킨다.
- stable stand/walk controller trace를 capture해 collapse artifact를 대체한다.
