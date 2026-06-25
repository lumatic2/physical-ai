# DESIGN - Robotics Lab Environment

## Design Intent

Robotics Lab should read as a working digital twin lab, not a blue tiled viewer. The first viewport must show the robot action, while the environment preset should change the perceived space around it.

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
