# DESIGN - Robotics Lab Environment

## Design Intent

Robotics Lab should read as a working digital twin lab, not a blue tiled viewer. The first viewport must show the robot action, while the environment preset should change the perceived space around it.

The new arm laboratory view should make the physical-AI loop legible without requiring prior robotics knowledge: what the robot sees, what instruction it received, what component produced each decision or action, and what changed in the environment.

## Arm Laboratory View

- Main panel: third-person simulation camera showing the robot arm, target object and destination.
- Camera inset: the exact wrist-camera frame consumed by the policy, with a clear `model input` label.
- Instruction strip: one natural-language task and current episode state.
- Decision/action timeline: source-tagged `sensor`, `vlm`, `vla`, `controller`, `environment` events aligned to playback time.
- Evidence drawer: policy/environment revision, seed, trace schema, PASS/FAIL outcome and raw artifact links.
- Mode badges: `recorded evidence` vs `live/local inference`, `simulation` vs `real telemetry`.

## Environment Milestones

1. Visual Lab Scenes: procedural Three.js objects make each preset visually distinct while keeping MuJoCo physics unchanged.
2. Physical Rough Terrain Scene: rough preset gains collision/contact evidence and explicit QA.
3. Asset-backed Lab Shell: lightweight GLB/glTF or generated assets improve fidelity after performance checks.

## Preset Direction

- `flat-lab`: clean calibration bay with floor seams, safety border, wall panels, calibration posts, and soft neutral lighting.
- `instrumented-lab`: measurement bay with sensor rigs, vertical height frame, monitor panels, contact readout rails, and tighter inspection lighting.
- `rough-terrain`: terrain lane with curb blocks, lane boundaries, hazard edge markings, side barriers, and test-rig lighting.

## Guardrails

- M30 visual objects are Three.js-only and must not be described as collision geometry.
- No decorative gradient blobs or abstract hero graphics.
- Text and UI should stay out of the robot viewport as much as possible; the scene itself carries the sense of place.
- If an environment affects physics, it belongs to M31 and must update QA evidence.
- Do not render free-form chain-of-thought. Use short structured facts such as detected target, selected skill, action chunk and measured result.
- Never show an observer camera as `model input`; camera provenance must remain visible.
- PASS and FAIL episodes use the same layout and evidence density so failure is not visually hidden.
