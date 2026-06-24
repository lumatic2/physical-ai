# 0010 - Digital twin workbench foundation

Status: Accepted 2026-06-24

## Context

M24/M25 closed the simulated controller-backed twin gate: Unitree MuJoCo, DDS-shaped state, LowCmd command path, browser stream, collapse rejection, and an unassisted Unitree RL Lab browser candidate all have evidence.

The public viewer still reads mostly as a robot gallery. A reviewer can see scenes and copy, but the UI does not yet make the twin evidence contract explicit enough: runtime source, qpos shape, telemetry sidecar, stream path, comparison gate, and assisted-vs-unassisted limits are scattered across experiment notes.

## Decision

Add a Digital Twin Workbench layer to the existing MuJoCo/Web viewer before starting another backend rewrite.

The workbench exposes the selected experiment's runtime mode, state contract, evidence lanes, and current limit in the visible panel and through a Playwright-readable QA hook.

## Consequences

Positive:
- The public surface better matches the actual north star: verified twin evidence, not just animation.
- Backend artifacts from M24/M25 become easier to inspect without reading many experiment folders.
- Future real robot telemetry can reuse the same summary contract.

Negative:
- This is not a new controller or real robot milestone by itself.
- `src/main.js` remains a large single-file viewer until a later refactor is justified.

## Follow-up

- Use M26 step 0 to add the workbench panel and QA artifact.
- Later steps may split experiment copy/metadata out of `main.js` only if the workbench grows beyond one cohesive file.
