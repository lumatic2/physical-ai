# Architecture - Digital Twin Workbench

## 현재 스택

- Public viewer: `experiments/03-digital-twin/web`, MuJoCo WASM, Three.js, lil-gui.
- Runtime registry: `experiments/03-digital-twin/experiments.json` canonical, `web/experiments.json` derived mirror.
- Evidence artifacts: `experiments/*/verify/*.json`, web QA outputs under `experiments/03-digital-twin/web/qa/out/`.
- Backend bridge evidence: Unitree MuJoCo/DDS/LowCmd probes in `experiments/33-unitree-mujoco-g1-bridge-probe`.

## Runtime layers

1. Registry layer: `experiments.json` defines scene, trajectory, optional policy, optional telemetry sidecar, optional comparison trajectory.
2. Physics/viewer layer: `src/main.js` loads MJCF through MuJoCo WASM and renders with Three.js.
3. Control layer:
   - Policy mode runs ONNX closed-loop in browser.
   - Replay mode sets `qpos` from trajectory frames.
   - Stream mode applies WebSocket `physical-ai-stream-frame-v0`.
4. Workbench layer: selected experiment metadata, state contract, evidence lanes, and current limit are exposed in DOM and `window.demo.qaWorkbenchSummary()`.

## Contracts

- Replay trajectory: `fps`, `nq`, `scene`, `qpos[frame][nq]`.
- Telemetry sidecar: frame-aligned telemetry for replay experiments.
- Stream frame: browser-compatible qpos frame plus telemetry payload.
- QA summary: JSON object with experiment id, runtime mode, state contract, evidence lanes, current limit, and `pass`.

## 금지사항

- `web/` JSON mirrors are derived from `experiments/03-digital-twin/`; canonical data edits start at the experiment root unless the file is web-only UI code.
- Assisted fixture evidence must not be described as real robot telemetry or unassisted controller proof.
- Real robot secrets, DDS network settings, or hardware-only assumptions must not be baked into public static assets.
