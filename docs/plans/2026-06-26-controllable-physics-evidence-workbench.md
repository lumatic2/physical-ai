# Controllable Physics Evidence Workbench Plan

planning_gate:
  team_validation_mode: manual-pass
  spec_delta: "ROADMAP, PRD, ARCHITECTURE, and ADR 0012 now define H33 as controllable command evidence + MuJoCo runtime readout + public story refresh."
  perspectives:
    product: "A 5-minute reviewer should see that keyboard input changes the policy command and that physics claims are evidence-backed."
    architecture: "MuJoCo WASM remains the truth layer; UI exposes command/readout state without rewriting physics."
    security: "No secrets, external consoles, telemetry credentials, or hardware network assumptions."
    qa: "Each milestone has a JSON evidence artifact plus local/live smoke where applicable."
    skeptic: "Contact readouts may be unavailable in browser bindings; unsupported fields must be explicit rather than disguised by overlays."
  dod:
    - "M33 command smoke artifact proves visible UI + QA command changes."
    - "M34 contact/force probe artifact records supported and unsupported MuJoCo readout fields."
    - "M35 public story smoke proves README/live copy reflects current evidence boundaries."

## Horizon

H33 moves Robotics Lab v2 from "visually realistic environment" to "controllable evidence workbench." It should not create new physics claims until runtime state supports them.

## Milestone Tree

- [ ] M33 User-controllable Digital Twin
  - [ ] Step 0: expose command state in UI; AC: `npm run build`, `node qa/workbench_check.mjs --exp=g1-walk`, `qaWorkbenchSummary().control.enabled === true`.
  - [ ] Step 1: add `qa/control_smoke.mjs` local/live keyboard command smoke; AC: `experiments/134-user-controllable-digital-twin/verify/control-smoke.json` captures down/release transitions and visible UI.
- [ ] M34 MuJoCo Contact/Force Readout Probe
  - [ ] Step 0: read-only runtime field audit; AC: probe reports `ncon`, contact, force, sensor availability.
  - [ ] Step 1: QA/debug summary integration; AC: supported fields appear in QA-only summary or unsupported fields are documented.
- [ ] M35 Public Evidence Story Refresh
  - [ ] Step 0: README and experiment index claim audit; AC: stale or over-broad claims are listed.
  - [ ] Step 1: public copy/evidence refresh; AC: README/index/live smoke align with M27-M34 boundaries.

## Current Run Scope

Produce roadmap and phase plans only. Stop before implementation of M33.

## Stop Conditions

- Stop if M34 requires a new MuJoCo binding, native build, or physics engine change.
- Stop if public copy would imply real robot telemetry, unassisted squat proof, or hardware control.
- Stop if live verification requires external credentials or console access.
