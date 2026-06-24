# Robotics Lab v2 Plan

## North Star

Make `robotics.askewly.com` feel like a polished, inspectable digital twin workbench: a shadcn/Tailwind UI shell around the current MuJoCo runtime, then a laboratory environment with controllable terrain, grounding, and physics settings.

## Scope Boundary

- This plan covers M27 and M28.
- It does not include real robot DDS capture, Isaac/Gazebo migration, or full neural RL training.
- Stop after M27 if the React/shadcn shell breaks current MuJoCo QA. Do not continue into environment physics changes until the shell passes.

## Step Tree

- [ ] M27 - Robotics Lab shadcn UI Shell
  - [ ] Step 0: Vite/React/Tailwind/shadcn scaffold around existing static assets — verify local server loads `unitree-g1-elastic-stand`.
  - [ ] Step 1: Move robot picker/workbench/status UI into shadcn components — verify desktop/mobile UI smoke and `qaWorkbenchSummary`.
  - [ ] Step 2: Generate and apply favicon/app icon with imagegen — verify favicon loads and asset is saved under `web/assets/`.
  - [ ] Step 3: Responsive polish and visual QA pass — verify desktop + mobile screenshots and no console errors.
- [ ] M28 - Digital Twin Laboratory Environment Controls
  - [ ] Step 0: Define environment preset contract and UI summary — verify preset state appears in QA JSON.
  - [ ] Step 1: Add lab-like visual environment and floor/material presets — verify scenes render with stable camera/framing.
  - [ ] Step 2: Add grounding/contact/physics controls with safe defaults — verify selected values are recorded and existing replay/policy gates do not regress.
  - [ ] Step 3: Tune physics presets and compare stability/collapse evidence — verify environment smoke artifact and update experiment README.

## Planning Gate

```yaml
planning_gate:
  team_validation_mode: manual-pass
  spec_delta: "Update product spec/architecture/ADR/ROADMAP for shadcn UI shell and digital twin lab environment controls."
  perspectives:
    product: "M27 improves reviewability and brand polish; M28 makes the twin feel inspectable rather than static."
    architecture: "React/shadcn shell must wrap the existing MuJoCo runtime instead of rewriting it. Physics changes wait until after shell QA."
    security: "No external secrets required. Imagegen asset must be committed locally and not referenced from a transient generated path."
    qa: "Each milestone has Playwright JSON evidence plus existing visual_check regression gates."
    skeptic: "The biggest risk is mixing UI migration with physics behavior changes; split milestones prevent that."
  dod:
    - "M27 evidence: ui-shell smoke JSON + desktop/mobile visual QA + favicon asset check."
    - "M28 evidence: environment controls smoke JSON + stable replay/policy regression checks."
```
