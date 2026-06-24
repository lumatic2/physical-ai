# 128-robotics-lab-ui-shell - shadcn UI shell for the MuJoCo twin

> M27. Convert the public Robotics Lab from a vanilla DOM overlay into a Vite/React/Tailwind/shadcn shell while preserving the existing MuJoCo runtime and evidence gates.

## 1. 가설 (Hypothesis)

If the Robotics Lab UI is moved to a shadcn/Tailwind app shell without changing the runtime boundary, then the site can gain a polished, responsive product interface while keeping existing replay/workbench QA valid.

반증 기준:
- Vite/shadcn migration breaks MuJoCo WASM load or COOP/COEP requirements.
- `unitree-g1-elastic-stand` no longer replays qpos[36] with telemetry sidecar.
- Workbench summary no longer distinguishes telemetry replay and reference comparison evidence.
- Mobile UI covers the full canvas or causes text overflow.

## 2. 방법 (Method)

### 셋업

- App shell: Vite + React + Tailwind CSS v4 + shadcn/ui `radix-nova`.
- Runtime: existing `src/main.js` MuJoCo/Three.js code remains the truth layer.
- UI: `src/App.jsx` renders the shadcn workbench overlay and reads `window.demo.qaWorkbenchSummary()`.
- QA: Vite dev server with COOP/COEP headers; Playwright checks existing visual/workbench paths.
- Icon: imagegen-generated Robotics Lab favicon saved under `web/assets/`.

### 시나리오

- S1: Vite build succeeds.
- S2: desktop replay visual QA passes for `unitree-g1-elastic-stand`.
- S3: mobile replay visual QA passes and leaves robot/canvas visible.
- S4: workbench summary passes for telemetry sidecar and reference comparison cases.
- S5: favicon/app icon assets load with expected PNG dimensions.

## 3. 결과 (Results)

| Run | Verdict | Cost | Retries | 비고 |
|-----|---------|------|---------|------|
| vite-build | PASS | local Vite | 0 | Vite build succeeds; chunk warning is expected from MuJoCo/runtime bundle size |
| unitree desktop visual | PASS | local Playwright | 0 | qpos[36], 100 frames, telemetry sidecar, consoleErrors=0 |
| unitree mobile visual | PASS | local Playwright | 2 | panel compressed to compact mobile summary so canvas remains visible |
| unitree workbench | PASS | local Playwright | 0 | telemetry sidecar evidence preserved |
| reference comparison workbench | PASS | local Playwright | 0 | `qaCompare` evidence preserved |
| favicon check | PASS | local fetch + PNG header check | 0 | `/assets/favicon.png` 256px and `/assets/robotics-lab-icon-512.png` 512px |

### 박제 위치

- `verify/ui-shell-smoke.json`
- `verify/unitree-g1-elastic-stand-workbench-summary.json`
- `verify/g1-squat-reference-vs-wbc-workbench-summary.json`
- `verify/favicon-check-summary.json`

## 4. 통찰 (Insights)

- React/shadcn can own the app chrome without replacing the MuJoCo runtime.
- Vite dev server must be used for QA now that the entrypoint is JSX and Tailwind/shadcn imports need transformation.
- The legacy DOM panel remains hidden only to preserve metadata and QA summary during the transition. A later cleanup can move that metadata out of `src/main.js`.
- Mobile needs a compact workbench surface; the full desktop robot picker is too tall for the first viewport.

### 가설은 통과했나?

- [x] PASS - MuJoCo replay/workbench QA survived the shadcn shell.
- [x] PASS - favicon is generated, committed, and verified from the local server.
- [x] PASS - mobile visual QA passes after compacting the overlay.
- [ ] PENDING - M28 environment/physics controls are not part of this milestone.
