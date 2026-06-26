# 0012 - Controllable physics evidence workbench uses MuJoCo runtime readouts

Status: Accepted 2026-06-26

## Context

Robotics Lab v2 now has a React shell, environment presets, physical rough terrain routing, and an asset-backed lab shell. The next gap is not another decorative scene pass. The public demo needs to show that user input changes learned policy commands and that physical interaction claims come from MuJoCo runtime state.

The previous rough terrain contact cue approach was reverted because visual overlays can imply physics evidence that was not read from the simulator.

## Decision

H33 splits the next work into three evidence milestones:

1. M33 exposes user command control in the public UI and QA summary.
2. M34 probes browser-accessible MuJoCo contact/force/sensor readouts before making new contact claims.
3. M35 refreshes public README/live story only after the evidence boundaries are clear.

MuJoCo WASM remains the runtime truth layer. We will not implement a new physics engine for this horizon, and unsupported contact fields must be reported as unavailable rather than simulated with visual-only cues.

## Consequences

Positive:
- A visitor can connect keyboard input to policy behavior without reading source code.
- Contact/force claims become falsifiable through runtime evidence.
- Public copy can distinguish learned policy control, replay, assisted fixture, rough terrain, and unsupported real-robot claims.

Negative:
- M34 may find that some useful MuJoCo fields are not exposed by the current WASM binding.
- Debug readouts may remain QA-only until UI density is handled carefully.

## Follow-up

- M33 should keep policy command semantics stable and only expose state.
- M34 should start as a read-only probe before any public debug panel.
- M35 should update public claims only after M33/M34 evidence exists.
