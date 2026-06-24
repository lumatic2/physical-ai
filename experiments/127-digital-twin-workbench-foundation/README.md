# 127-digital-twin-workbench-foundation - visitor-facing twin evidence workbench

> M26. Backend/controller evidence from M24/M25 is surfaced inside the public MuJoCo web twin as runtime mode, state contract, evidence lanes, gate, and current limit.

## 1. 가설 (Hypothesis)

If the browser twin is a real workbench rather than a gallery, then a selected experiment should expose what runtime is active, what state contract it uses, what evidence lanes exist, which QA gate applies, and what the current limit is.

반증 기준:
- Workbench summary cannot distinguish replay, telemetry sidecar, reference comparison, policy, or stream mode.
- The visible panel says more than the QA hook can verify.
- Assisted fixture evidence is presented as real robot telemetry or unassisted controller proof.

## 2. 방법 (Method)

### 셋업

- Viewer: `experiments/03-digital-twin/web/src/main.js`
- QA runner: `experiments/03-digital-twin/web/qa/workbench_check.mjs`
- Primary sample: `unitree-g1-elastic-stand`
- Comparison sample: `g1-squat-reference-vs-wbc`

### 시나리오

- S1: selected experiment renders a Twin workbench panel.
- S2: `window.demo.qaWorkbenchSummary()` returns experiment id, runtime, state contract, evidence lanes, gate, status, limit, and pass.
- S3: Playwright writes tracked summary artifacts for telemetry-sidecar and comparison cases.

### 측정 metric

- `stateContract.nq`
- `stateContract.frames`
- `stateContract.telemetry`
- `stateContract.comparison`
- `evidenceLanes`
- `gate`
- `pass`

## 3. 결과 (Results)

| Run | Verdict | Cost | Retries | 비고 |
|-----|---------|------|---------|------|
| unitree-g1-elastic-stand workbench | PASS | local Playwright | 1 | qpos[36], 100 frames, 50Hz, telemetry sidecar, `qaSeek`, assisted limit preserved |
| g1-squat-reference-vs-wbc workbench | PASS | local Playwright | 0 | qpos[36], 300 frames, 50Hz, reference compare, `qaCompare`, learned-policy overclaim avoided |
| unitree-g1-elastic-stand visual replay | PASS | local Playwright | 0 | existing replay QA still samples frames 0/33/65/99 with telemetry readout and consoleErrors=0 |

### 박제 위치

- `verify/unitree-g1-elastic-stand-workbench-summary.json`
- `verify/g1-squat-reference-vs-wbc-workbench-summary.json`

## 4. 통찰 (Insights)

- The viewer now exposes twin evidence as a runtime contract, not just descriptive copy.
- `unitree-g1-elastic-stand` correctly appears as a stable assisted fixture with telemetry sidecar, not real robot telemetry.
- `g1-squat-reference-vs-wbc` correctly appears as a comparison gate, not a learned policy success.
- Future real robot DDS evidence can target the same summary shape once a real publisher exists.

### 가설은 통과했나?

- [x] PASS - Workbench summary distinguishes replay plus telemetry sidecar.
- [x] PASS - Workbench summary distinguishes replay plus reference comparison.
- [x] PASS - Current limits are included in the QA artifact.
- [ ] PENDING - Real robot telemetry is still future evidence, not part of M26.
