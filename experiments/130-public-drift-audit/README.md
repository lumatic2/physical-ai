# 130-public-drift-audit - public claim drift after M27/M28

> M29. Audit public-facing copy and live QA after Robotics Lab v2 UI shell and environment controls landed locally.

## 1. 가설 (Hypothesis)

If M27/M28 are complete locally but not consistently reflected publicly, then a reviewer will see a mismatch between repo evidence, Askewly pages, vault notes, and the live `robotics.askewly.com` experience.

반증 기준:
- live `robotics.askewly.com` exposes the Vite/React shell plus `qaWorkbenchSummary()` and `qaEnvironmentSummary()`.
- Askewly project/blog copy reflects the current G1 squat state without calling it real robot telemetry.
- vault notes either match the current evidence or are clearly historical.
- README copy does not overclaim assisted fixture, controller-backed sim, or rough terrain environment controls.

## 2. 방법 (Method)

### 셋업

- Local source: `README.md`, `docs/PRD.md`, `docs/ARCHITECTURE.md`, `experiments/03-digital-twin/web/README.md`.
- Public Robotics Lab: `https://robotics.askewly.com/?exp=unitree-g1-elastic-stand`.
- Askewly public pages: `https://askewly.com/projects/physical-ai-arm`, `https://askewly.com/blog/robot-walk-qa-after-demo`.
- Askewly source copy: `C:/Users/yusun/projects/Askwely-company/web/src/lib/projects.ts` and physical-ai blog MDX files.
- Vault check: `ssh m4` after confirming `~/vault/00-System/VAULT_INDEX.md` exists.

### 시나리오

- S1: Search local and Askewly source copy for drift-sensitive claims.
- S2: Fetch public HTML for Robotics Lab, Askewly project page, and blog page.
- S3: Run live visual QA and live workbench/environment QA.
- S4: Probe live page for QA hooks and deployed entrypoint.
- S5: Search vault physical-ai notes/logs for public claim drift.

### 측정 metric

- `surfaceStatus`: `ok`, `stale`, or `drift`.
- `claimBoundary`: assisted fixture, controller-backed simulation, no real robot telemetry, rough-terrain scene reload.
- `qaStatus`: pass, timeout, or missing hook.

## 3. 결과 (Results)

| Surface | Verdict | Evidence | 비고 |
|-----|---------|------|------|
| live Robotics Lab | DRIFT | `verify/public-drift-audit.json` | Deployed page is legacy static `./src/main.js`, has no React root and no workbench/environment hooks. |
| live visual replay | PASS | `node qa/visual_check.mjs --live --exp=unitree-g1-elastic-stand --steps=1 --chunk=1` | qpos[36], telemetry sidecar, consoleErrors=0. |
| live workbench/environment QA | FAIL_STALE_DEPLOY | command timeouts + hook probe | `workbench_check` and `environment_check` timed out because M26/M28 hooks are absent on live. |
| Askewly project page | STALE | `projects.ts` + public HTML | Says G1 squat is still a micro-dip probe; M19 is now visible-squat sim evidence, still not real telemetry. |
| Askewly `robot-walk-qa-after-demo` blog | OK | MDX + public HTML | General QA framing is consistent and does not claim current real-hardware logs. |
| Askewly G1 squat blog | OK | MDX source | Explicitly states the result is measured MuJoCo WBC/browser replay, not real Unitree hardware telemetry. |
| GitHub/root README | MOSTLY_OK_STALE | local grep | No real-robot overclaim found, but top-level copy still reads as gallery more than M27/M28 workbench. |
| vault physical-ai notes | STALE_HISTORICAL | `ssh m4 grep` | Notes are mostly M6/M12 era synthesis plus M28 daily log; no current M27/M28 public-facing synthesis found. |

### 박제 위치

- `verify/public-drift-audit.json`

## 4. 통찰 (Insights)

### 무엇을 알아냈나

- The urgent drift is deployment/state drift, not claim inflation: live Robotics Lab is visually working but not serving the local M27/M28 Vite/React workbench.
- Askewly project copy needs a narrow update: replace "G1 squat is still micro-dip" with "G1 squat has simulated WBC/browser replay evidence, but no real robot telemetry."
- The safety boundary is currently best preserved in the G1 squat blog and local web README.
- Vault needs either a current synthesis note or a clear pointer that older M6/M12 notes are historical.

### 가설은 통과했나?

- [x] PASS - live/public surfaces are not fully aligned with M27/M28.
- [x] PASS - no audited surface claimed assisted fixture as real robot telemetry.
- [x] PASS - the main fix is deploy/copy sync before new rough-terrain work.

### 정의에 반영

- No new ADR. This is a maintenance audit, not a stack decision.

### 다음 실험 후보

- Deploy or verify M27/M28 Robotics Lab live bundle, then rerun live `workbench_check` and `environment_check`.
- Update Askewly project page copy for post-M19 G1 squat status.
- Refresh vault physical-ai synthesis after live deployment is confirmed.
