# 0011 - Robotics Lab v2 uses shadcn UI shell before physics environment upgrades

Status: Accepted 2026-06-24

## Context

The current public twin is a static MuJoCo WASM/Three.js app with vanilla DOM overlays. M26 exposed runtime and evidence contracts, but the UI is still difficult to evolve: component structure, mobile panels, environment controls, QA status, and branding assets are all hand-written in `src/main.js`.

The next product direction includes two different concerns:

- Site UI polish: shadcn/ui, Tailwind CSS, favicon/app icon, responsive panels.
- Digital twin environment upgrade: lab-like background, switchable environment presets, grounding/contact/physics controls.

Combining those in one code pass would make it hard to know whether failures come from UI migration, asset loading, MuJoCo scene changes, or physics behavior.

## Decision

Split Robotics Lab v2 into two product milestones.

1. M27 creates the Vite/React/Tailwind/shadcn app shell and generated favicon while preserving the current MuJoCo runtime and existing visual/workbench QA.
2. M28 adds the laboratory environment and user-facing environment/grounding/physics controls after the shell is stable.

The MuJoCo runtime remains the truth layer. shadcn owns application chrome and controls, not the physics engine.

## Consequences

Positive:
- UI polish and physics behavior become independently testable.
- The React shell can use shadcn components without rewriting MuJoCo loading in the same step.
- Generated favicon work is project-bound and can be verified separately from runtime behavior.

Negative:
- M27 will not by itself improve physics/contact behavior.
- M28 must respect existing scene registry and QA contracts rather than freely replacing the runtime.

## Follow-up

- M27 should run shadcn CLI only after the Vite/React project context is clear.
- M28 should start with presets and summaries before deeper contact/solver changes.
