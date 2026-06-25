# Robotics Lab Environment Realism Plan

planning_gate:
  team_validation_mode: manual-pass
  spec_delta: "ROADMAP, PRD, ARCHITECTURE, and DESIGN now split environment realism into visual-only, physical terrain, and asset-backed milestones."
  perspectives:
    product: "Visitors should understand the digital twin environment from the scene itself, not only from labels."
    architecture: "Visual-only Three.js primitives stay separate from MuJoCo collision; M31 owns physics terrain."
    security: "No secret, auth, or external service dependency."
    qa: "Build, workbench QA, environment summaries, rendered Playwright smoke, and visual-only contract checks."
    skeptic: "Procedural visuals can still look synthetic; asset-backed shell remains a later milestone."
  dod:
    - "M30 evidence JSON passes and records distinct object sets for all three presets."
    - "Live/public default still opens G1 walking and scene switches in-app."

## Milestone Tree

- [ ] M30 Visual Lab Scenes
  - [ ] Step 0: procedural visual environment composition for flat/instrumented/rough presets; AC: build + environment smoke + Playwright no-GUI render check.
  - [ ] Step 1: evidence artifact and screenshots for visual-only preset distinction; AC: `experiments/131-visual-lab-scenes/verify/visual-lab-scenes-smoke.json`.
- [ ] M31 Physical Rough Terrain Scene
  - [ ] Step 0: rough scene compatibility audit; AC: identify MJCF variant and policy compatibility.
  - [ ] Step 1: contact-bearing rough preset route; AC: rough policy QA with physical terrain evidence.
- [ ] M32 Asset-backed Lab Shell
  - [ ] Step 0: asset strategy and budget; AC: asset source, size target, lazy-load plan.
  - [ ] Step 1: asset shell integration; AC: build, visual QA, bundle/performance smoke.

## Current Run Scope

Implement M30 Step 0 and Step 1 only. Stop before M31 because it changes the physics/contact claim level.
