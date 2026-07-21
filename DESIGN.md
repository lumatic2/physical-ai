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

### Public Evidence Contract

- `assets/arm-lab/registry.json` is a deterministic public derivative of the LAB1 episode and LAB2 causal trace; it never replaces those canonical artifacts.
- PASS and FAIL expose the same cameras, instruction, state/action trace and event lanes.
- Main camera is labelled `model input`; wrist camera is labelled `observer only` because that is the recorded producer contract.
- Every public artifact carries a byte size and SHA-256 digest. Local paths, token-like values, unknown event sources and ambiguous live/real claims fail before build.

## Local Live Laboratory View

- Entry: public recorded evidence and localhost live execution use separate routes or explicit entry modes; a public build never probes localhost.
- Controls: supported task/instruction, canonical/paraphrase form, execution lane, initial state, start/pause/resume/stop and current safety state.
- Execution lanes: `OpenVLA — direct VLA action`, `π₀.₅ — direct VLA action chunk`, `Qwen3-VL — scene/skill + scripted controller` are named in plain language and never collapsed into one generic AI badge.
- Observation panel: the exact model-input camera, structured VLM scene/skill when that lane is active, and an explicit `not available for this lane` state otherwise.
- Action panel: proposed versus executed action, component source, latency, heartbeat, GPU lease and stop reason remain visible without exposing hidden reasoning.
- Recording transition: session completion shows promotion/quarantine status and opens the exact canonical replay only after hash linkage passes.

### Askewly Design Adaptation

- Surface: an application workbench whose first task is inspecting recorded physical-AI evidence, not a decorative dashboard.
- Focal region: synchronized camera evidence. Instruction and current event support it; trace graphs and raw provenance form the verification layer.
- Hierarchy uses the existing project tokens, surface luminance and spacing before borders or shadows. Accent colour remains a small state signal.
- Interaction must include keyboard playback, explicit PASS/FAIL text, responsive DOM order and reduced-motion-safe states.
- Avoid nested card grids, ornamental metrics, colour-only outcomes, emoji icons, left-accent cards and free-form chain-of-thought.

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
